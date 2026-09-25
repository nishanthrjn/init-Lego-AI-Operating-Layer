import { closed, DEFAULT_CONFIG, IMPLEMENTATION, parseConfig, parseFrame, parseResult, result } from "../contract.js";
import type { FrameRequest, HandConfig, HandResult } from "../contract.js";
import type { HandAdapter } from "../frame-pump.js";
export interface WorkerTransport {
  send(message: unknown, transfer?: Transferable[]): void;
  listen(message: (value: unknown) => void, error: () => void): void;
  terminate(): void;
}
export interface Clock {
  set(action: () => void, delay: number): unknown;
  clear(handle: unknown): void;
}
const clock: Clock = {
  set: (action, delay) => setTimeout(action, delay),
  clear: handle => clearTimeout(handle as ReturnType<typeof setTimeout>),
};
function createWorker(): WorkerTransport {
  // Fixed classic worker bundle; MediaPipe 0.10.21 uses importScripts.
  const worker = new Worker("/worker.js");
  return {
    send: (message, transfer = []) => worker.postMessage(message, transfer),
    listen: (message, error) => {
      worker.onmessage = event => message(event.data as unknown);
      worker.onerror = event => { event.preventDefault(); error(); };
      worker.onmessageerror = () => error();
    },
    terminate: () => worker.terminate(),
  };
}
export interface BrowserPreflight {
  readonly supported: boolean;
  readonly implementation: typeof IMPLEMENTATION;
  readonly reason: "OK" | "BROWSER_APIS";
}
export function preflight(): BrowserPreflight {
  const supported = globalThis.isSecureContext === true &&
    typeof Worker !== "undefined" && typeof OffscreenCanvas !== "undefined" &&
    typeof createImageBitmap === "function" && typeof WebAssembly !== "undefined" &&
    typeof crypto !== "undefined" && !!crypto.subtle &&
    typeof navigator !== "undefined" && !!navigator.mediaDevices?.getUserMedia;
  return Object.freeze({ supported, implementation: IMPLEMENTATION, reason: supported ? "OK" : "BROWSER_APIS" });
}
export class WorkerHandAdapter implements HandAdapter<ImageBitmap> {
  private worker: WorkerTransport | undefined;
  private ready = false;
  private lifecycle = 0;
  private config = DEFAULT_CONFIG;
  private pending: { id: number; done: (result: HandResult) => void; timer: unknown } | undefined;
  private closing: Promise<void> | undefined;
  constructor(private readonly makeWorker: () => WorkerTransport = createWorker,
              private readonly timer: Clock = clock) {}
  async initialize(config: HandConfig): Promise<HandResult> {
    const shutdown = this.stop();
    const generation = ++this.lifecycle;
    await shutdown;
    if (generation !== this.lifecycle) return result(0, "CANCELLED", "STOPPED");
    try { this.config = parseConfig(config); }
    catch { return result(0, "INVALID_INPUT", "CONFIGURATION"); }
    try { this.worker = this.makeWorker(); }
    catch { return result(0, "UNSUPPORTED", "BROWSER_APIS"); }
    const worker = this.worker;
    worker.listen(value => {
      if (this.worker !== worker) return;
      try {
        const output = parseResult(value, this.config.maxHands);
        if (!this.pending || output.frameId !== this.pending.id ||
            output.attribution.implementation !== IMPLEMENTATION) throw new Error("OUTPUT");
        this.ready = output.status === "SUCCESS";
        this.complete(output);
        if (output.status !== "SUCCESS") void this.stop();
      } catch {
        this.complete(result(this.pending?.id ?? 0, "EXECUTION_FAILURE", "OUTPUT"));
        void this.stop();
      }
    }, () => {
      this.complete(result(this.pending?.id ?? 0, "EXECUTION_FAILURE", "WORKER"));
      void this.stop();
    });
    return this.send(0, { kind: "init", config: this.config }, [], this.config.initializationDeadlineMs);
  }
  process(request: FrameRequest, frame: ImageBitmap): Promise<HandResult> {
    if (!this.ready || !this.worker || this.pending) {
      frame.close();
      return Promise.resolve(result(request.frameId, "INVALID_INPUT", "MESSAGE"));
    }
    try {
      parseFrame(request, this.config);
      if (frame.width !== request.width || frame.height !== request.height) throw new Error("FRAME");
    } catch {
      frame.close();
      return Promise.resolve(result(0, "INVALID_INPUT", "FRAME"));
    }
    return this.send(request.frameId, { kind: "frame", request, bitmap: frame }, [frame], this.config.frameDeadlineMs);
  }
  private send(id: number, message: unknown, transfer: Transferable[], delay: number): Promise<HandResult> {
    return new Promise(resolve => {
      const handle = this.timer.set(() => {
        this.complete(result(id, "DEADLINE", id === 0 ? "INITIALIZATION" : "FRAME"));
        void this.stop();
      }, delay);
      this.pending = { id, done: resolve, timer: handle };
      try { this.worker?.send(message, transfer); }
      catch {
        this.complete(result(id, "EXECUTION_FAILURE", "WORKER"));
        void this.stop();
      }
    });
  }
  private complete(output: HandResult): void {
    const pending = this.pending;
    this.pending = undefined;
    if (pending) { this.timer.clear(pending.timer); pending.done(output); }
  }
  stop(): Promise<void> {
    this.lifecycle++;
    if (this.closing) return this.closing;
    this.ready = false;
    const worker = this.worker;
    this.worker = undefined; // reject old generation results immediately
    this.complete(result(this.pending?.id ?? 0, "CANCELLED", "STOPPED"));
    if (!worker) return Promise.resolve();
    const shutdown = new Promise<void>(resolve => {
      let finished = false;
      const finish = () => {
        if (finished) return;
        finished = true;
        this.timer.clear(handle);
        worker.terminate();
        resolve();
      };
      const handle = this.timer.set(finish, 150);
      worker.listen(value => {
        try {
          const r = closed(value, ["kind"]);
          if (r.kind === "closed") finish();
        } catch { /* late result discarded; bounded forced termination follows */ }
      }, finish);
      try { worker.send({ kind: "stop" }); } catch { finish(); }
    });
    this.closing = shutdown.finally(() => { this.closing = undefined; });
    return this.closing;
  }
}

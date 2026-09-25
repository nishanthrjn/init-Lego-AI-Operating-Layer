import { HandLandmarker } from "@mediapipe/tasks-vision";
import { closed, parseConfig, parseFrame, result } from "../contract.js";
import type { HandConfig } from "../contract.js";
import { loadApprovedAssets } from "./assets.js";
import { Inference } from "./inference.js";

const scope = globalThis as unknown as {
  onmessage: ((event: MessageEvent<unknown>) => void) | null;
  postMessage(data: unknown): void;
  close(): void;
  location: Location;
};
let task: HandLandmarker | undefined;
let inference: Inference<ImageBitmap> | undefined;
let config: HandConfig | undefined;
let state: "new" | "initializing" | "ready" | "closed" = "new";
// Do not expose upstream SDK dumps in local diagnostics.
console.log = console.info = console.warn = console.error = () => {};
function finish(): void {
  state = "closed";
  try { task?.close(); } catch { /* worker termination is the remaining cleanup boundary */ }
  task = undefined;
  inference = undefined;
  scope.postMessage({ kind: "closed" });
  scope.close();
}
async function initialize(value: unknown): Promise<void> {
  if (state !== "new") { scope.postMessage(result(0, "INVALID_INPUT", "MESSAGE")); return; }
  state = "initializing";
  const start = performance.now();
  try { config = parseConfig(value); }
  catch { scope.postMessage(result(0, "INVALID_INPUT", "CONFIGURATION")); return; }
  if (typeof OffscreenCanvas === "undefined" || typeof WebAssembly === "undefined" ||
      typeof ImageBitmap === "undefined" || !crypto?.subtle) {
    scope.postMessage(result(0, "UNSUPPORTED", "BROWSER_APIS")); return;
  }
  try {
    const probe = new OffscreenCanvas(2, 2).getContext("webgl2");
    if (!probe) { scope.postMessage(result(0, "UNSUPPORTED", "LOCAL_RUNTIME")); return; }
    probe.getExtension("WEBGL_lose_context")?.loseContext();
  } catch { scope.postMessage(result(0, "UNSUPPORTED", "LOCAL_RUNTIME")); return; }
  let buffers: readonly ArrayBuffer[];
  try { buffers = await loadApprovedAssets(scope.location.origin); }
  catch { scope.postMessage(result(0, "INITIALIZATION_FAILURE", "ASSET")); return; }
  // stop can be received while asset loading awaits.
  if ((state as string) === "closed") return;
  const [loaderBytes, wasmBytes, modelBytes] = buffers;
  if (!loaderBytes || !wasmBytes || !modelBytes) return;
  const loader = URL.createObjectURL(new Blob([loaderBytes], { type: "text/javascript" }));
  const wasm = URL.createObjectURL(new Blob([wasmBytes], { type: "application/wasm" }));
  try {
    task = await HandLandmarker.createFromOptions(
      { wasmLoaderPath: loader, wasmBinaryPath: wasm },
      { baseOptions: { modelAssetBuffer: new Uint8Array(modelBytes), delegate: "CPU" },
        runningMode: "VIDEO", numHands: 1 },
    );
    if ((state as string) === "closed") { task.close(); task = undefined; return; }
    // Initialize the graph before any camera acquisition; lazy initialization is
    // included in the initialization deadline and network-observation window.
    const canvas = new OffscreenCanvas(2, 2);
    canvas.getContext("2d")?.fillRect(0, 0, 2, 2);
    task.detectForVideo(canvas, 0);
    const initializedTask = task;
    inference = new Inference(config, (frame, timestamp) => initializedTask.detectForVideo(frame, timestamp));
    state = "ready";
    scope.postMessage(result(0, "SUCCESS", "OK", [], performance.now() - start));
  } catch { scope.postMessage(result(0, "INITIALIZATION_FAILURE", "LOCAL_RUNTIME")); }
  finally { URL.revokeObjectURL(loader); URL.revokeObjectURL(wasm); }
}
scope.onmessage = event => {
  const value = event.data;
  let bitmap: ImageBitmap | undefined;
  try {
    if (value === null || typeof value !== "object") throw new Error("MESSAGE");
    const candidate = (value as { bitmap?: unknown }).bitmap;
    if (typeof ImageBitmap !== "undefined" && candidate instanceof ImageBitmap) bitmap = candidate;
    const tag = (value as { kind?: unknown }).kind;
    if (tag === "init") {
      const message = closed(value, ["kind", "config"]);
      void initialize(message.config);
    } else if (tag === "stop") {
      closed(value, ["kind"]); finish();
    } else if (tag === "frame") {
      const message = closed(value, ["kind", "request", "bitmap"]);
      if (!(message.bitmap instanceof ImageBitmap)) throw new Error("FRAME");
      bitmap = message.bitmap;
      if (state !== "ready" || !inference || !config) throw new Error("STATE");
      const request = parseFrame(message.request, config);
      scope.postMessage(inference.run(request, bitmap));
    } else throw new Error("MESSAGE");
  } catch {
    bitmap?.close();
    scope.postMessage(result(0, "INVALID_INPUT", "MESSAGE"));
  }
};

import type { FrameRequest, HandConfig, HandResult } from "./contract.js";
import { parseFrame, parseResult } from "./contract.js";
// Browser-private acquisition shape; never part of canonical LegoAI contracts.
export interface LocalFrame { readonly width: number; readonly height: number; close(): void }
export interface HandAdapter<F extends LocalFrame> {
  initialize(config: HandConfig): Promise<HandResult>;
  process(request: FrameRequest, frame: F): Promise<HandResult>;
  stop(): Promise<void>;
}
export class FramePump<F extends LocalFrame> {
  private active = false;
  private generation = 0;
  private busy = false;
  private sequence = 0;
  submitted = 0;
  processed = 0;
  dropped = 0;
  constructor(
    private readonly adapter: HandAdapter<F>,
    private readonly config: HandConfig,
    private readonly capture: () => Promise<F>,
    private readonly accept: (result: HandResult) => void,
  ) {}
  start(): void { this.active = true; this.generation++; }
  stop(): void { this.active = false; this.generation++; }
  async tick(timestampMs: number): Promise<void> {
    if (!this.active) return;
    if (this.busy) { this.dropped = Math.min(this.dropped + 1, 1_000_000_000); return; }
    this.busy = true; // covers asynchronous capture as well as inference
    const generation = this.generation;
    let frame: F | undefined;
    try {
      frame = await this.capture();
      if (!this.active || generation !== this.generation) return;
      this.sequence++;
      const request = parseFrame({ schemaVersion: 1, frameId: this.sequence, timestampMs,
        width: frame.width, height: frame.height }, this.config);
      this.submitted = Math.min(this.submitted + 1, 1_000_000_000);
      const output = parseResult(await this.adapter.process(request, frame), this.config.maxHands);
      if (output.frameId !== request.frameId) throw new Error("FRAME_ID");
      if (this.active && generation === this.generation) {
        this.processed = Math.min(this.processed + 1, 1_000_000_000);
        this.accept(output);
      }
    } finally {
      try { frame?.close(); } // safe also for transferred ImageBitmap
      finally { this.busy = false; }
    }
  }
}
export interface OwnedStream { getTracks(): readonly { stop(): void }[] }
export class CameraLease<S extends OwnedStream> {
  private generation = 0;
  private stream: S | undefined;
  async acquire(open: () => Promise<S>): Promise<S | null> {
    this.stop();
    const generation = this.generation;
    const stream = await open();
    if (generation !== this.generation) {
      stream.getTracks().forEach(track => track.stop());
      return null;
    }
    this.stream = stream;
    return stream;
  }
  stop(): void {
    this.generation++;
    this.stream?.getTracks().forEach(track => track.stop());
    this.stream = undefined;
  }
}

import type { Hand, HandConfig, FrameRequest, HandResult } from "../contract.js";
import { parseFrame, result } from "../contract.js";
import type { LocalFrame } from "../frame-pump.js";
export interface RawDetection {
  landmarks: { x: number; y: number; z: number }[][];
  handedness: { categoryName: string; score: number }[][];
}
// Injectable local task call. It has no fetch, URL, telemetry or fallback path.
export class Inference<F extends LocalFrame> {
  private lastTimestamp = -1;
  constructor(
    private readonly config: HandConfig,
    private readonly detect: (frame: F, timestamp: number) => RawDetection,
    private readonly now: () => number = () => performance.now(),
  ) {}
  run(request: FrameRequest, frame: F): HandResult {
    const start = this.now();
    try {
      try { parseFrame(request, this.config); }
      catch { return result(0, "INVALID_INPUT", "FRAME"); }
      if (request.width !== frame.width || request.height !== frame.height ||
          request.timestampMs <= this.lastTimestamp) return result(request.frameId, "INVALID_INPUT", "FRAME");
      this.lastTimestamp = request.timestampMs;
      const raw = this.detect(frame, request.timestampMs);
      const elapsed = Math.max(0, this.now() - start);
      if (elapsed > this.config.frameDeadlineMs) return result(request.frameId, "DEADLINE", "FRAME");
      try {
        if (raw.landmarks.length > 1 || raw.handedness.length !== raw.landmarks.length) throw new Error("OUTPUT");
        const hands: Hand[] = raw.landmarks.map((points, index) => {
          const category = raw.handedness[index]?.[0];
          if (!category || (category.categoryName !== "Left" && category.categoryName !== "Right")) throw new Error("OUTPUT");
          return { landmarks: points.map(p => ({ x: p.x, y: p.y, z: p.z })),
            handedness: { label: category.categoryName, score: category.score } };
        });
        return result(request.frameId, "SUCCESS", "OK", hands, elapsed);
      } catch { return result(request.frameId, "EXECUTION_FAILURE", "OUTPUT"); }
    } catch { return result(request.frameId, "EXECUTION_FAILURE", "INFERENCE"); }
    finally { frame.close(); }
  }
}

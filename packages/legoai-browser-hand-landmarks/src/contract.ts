// Closed task values only. No browser handles, SDK objects or canonical authority.
export const IMPLEMENTATION = "mediapipe-0.10.21" as const;
export const ASSET = "hand-landmarker-float16-v1" as const;
export const DIGEST = "fbc2a30080c3c557093b5ddfc334698132eb341044ccee322ccf8bcf3607cde1";
export type Status = "SUCCESS" | "UNSUPPORTED" | "INVALID_INPUT" |
  "INITIALIZATION_FAILURE" | "EXECUTION_FAILURE" | "DEADLINE" | "CANCELLED";
const reasons = {
  SUCCESS: ["OK"],
  UNSUPPORTED: ["BROWSER_APIS", "LOCAL_RUNTIME"],
  INVALID_INPUT: ["CONFIGURATION", "FRAME", "MESSAGE"],
  INITIALIZATION_FAILURE: ["ASSET", "LOCAL_RUNTIME"],
  EXECUTION_FAILURE: ["INFERENCE", "OUTPUT", "WORKER", "CAMERA_DENIED", "CAMERA_UNAVAILABLE"],
  DEADLINE: ["INITIALIZATION", "FRAME", "SESSION"],
  CANCELLED: ["STOPPED"],
} as const;
export type Reason = typeof reasons[Status][number];
export interface HandConfig {
  readonly schemaVersion: 1;
  readonly revision: "hand-local-v1";
  readonly implementation: typeof IMPLEMENTATION;
  readonly approvedAsset: typeof ASSET;
  readonly runningMode: "VIDEO";
  readonly maxHands: 1;
  readonly localOnly: true;
  readonly maxWidth: number;
  readonly maxHeight: number;
  readonly frameDeadlineMs: number;
  readonly initializationDeadlineMs: number;
  readonly sessionLimitMs: number;
}
export const DEFAULT_CONFIG: HandConfig = Object.freeze({
  schemaVersion: 1, revision: "hand-local-v1", implementation: IMPLEMENTATION,
  approvedAsset: ASSET, runningMode: "VIDEO", maxHands: 1, localOnly: true,
  maxWidth: 640, maxHeight: 480, frameDeadlineMs: 2000,
  initializationDeadlineMs: 30000, sessionLimitMs: 60000,
});
export interface FrameRequest {
  readonly schemaVersion: 1;
  readonly frameId: number;
  readonly timestampMs: number;
  readonly width: number;
  readonly height: number;
}
export interface Landmark { readonly x: number; readonly y: number; readonly z: number }
export interface Hand {
  readonly landmarks: readonly Landmark[];
  readonly handedness?: Readonly<{ label: "Left" | "Right"; score: number }>;
}
export interface HandResult {
  readonly schemaVersion: 1;
  readonly frameId: number;
  readonly configurationRevision: "hand-local-v1";
  readonly status: Status;
  readonly reason: Reason;
  readonly attribution: Readonly<{
    implementation: typeof IMPLEMENTATION | "fake";
    asset: typeof ASSET | "fixture";
    digest: string;
    backend: "CPU/WASM" | "fixture";
  }>;
  readonly durationMs: number;
  readonly hands: readonly Hand[];
}
export function closed(value: unknown, keys: readonly string[]): Record<string, unknown> {
  if (value === null || typeof value !== "object" || Array.isArray(value)) throw new Error("SHAPE");
  const prototype = Object.getPrototypeOf(value);
  if (prototype !== Object.prototype && prototype !== null) throw new Error("PLAIN_VALUE");
  const record = value as Record<string, unknown>;
  const actual = Object.keys(record);
  if (actual.length !== keys.length || actual.some(k => !keys.includes(k))) throw new Error("FIELDS");
  for (const key of actual) {
    const descriptor = Object.getOwnPropertyDescriptor(record, key);
    if (!descriptor || !("value" in descriptor)) throw new Error("DATA_ONLY");
  }
  return record;
}
export function finite(value: unknown, min = -Number.MAX_VALUE, max = Number.MAX_VALUE): number {
  if (typeof value !== "number" || !Number.isFinite(value) || value < min || value > max) throw new Error("NUMBER");
  return value;
}
export function integer(value: unknown, min: number, max: number): number {
  const n = finite(value, min, max);
  if (!Number.isSafeInteger(n)) throw new Error("INTEGER");
  return n;
}
export function parseConfig(value: unknown): HandConfig {
  const r = closed(value, Object.keys(DEFAULT_CONFIG));
  for (const key of ["schemaVersion", "revision", "implementation", "approvedAsset", "runningMode", "maxHands", "localOnly"] as const) {
    if (r[key] !== DEFAULT_CONFIG[key]) throw new Error("CONFIGURATION");
  }
  for (const key of ["maxWidth", "maxHeight", "frameDeadlineMs", "initializationDeadlineMs", "sessionLimitMs"] as const) {
    if (r[key] !== DEFAULT_CONFIG[key]) throw new Error("CONFIGURATION_REVISION");
  }
  return Object.freeze({
    ...DEFAULT_CONFIG,
    maxWidth: integer(r.maxWidth, 2, 640), maxHeight: integer(r.maxHeight, 2, 480),
    frameDeadlineMs: integer(r.frameDeadlineMs, 100, 5000),
    initializationDeadlineMs: integer(r.initializationDeadlineMs, 1000, 60000),
    sessionLimitMs: integer(r.sessionLimitMs, 1000, 60000),
  });
}
export function parseFrame(value: unknown, config: HandConfig): FrameRequest {
  const r = closed(value, ["schemaVersion", "frameId", "timestampMs", "width", "height"]);
  if (r.schemaVersion !== 1) throw new Error("VERSION");
  return Object.freeze({
    schemaVersion: 1, frameId: integer(r.frameId, 1, 1_000_000_000),
    timestampMs: finite(r.timestampMs, 0, Number.MAX_SAFE_INTEGER),
    width: integer(r.width, 1, config.maxWidth), height: integer(r.height, 1, config.maxHeight),
  });
}
export function parseResult(value: unknown): HandResult {
  const r = closed(value, ["schemaVersion", "frameId", "configurationRevision", "status", "reason", "attribution", "durationMs", "hands"]);
  if (r.schemaVersion !== 1 || r.configurationRevision !== "hand-local-v1") throw new Error("VERSION");
  if (typeof r.status !== "string" || !Object.hasOwn(reasons, r.status)) throw new Error("STATUS");
  const status = r.status as Status;
  if (!(reasons[status] as readonly unknown[]).includes(r.reason)) throw new Error("REASON");
  const a = closed(r.attribution, ["implementation", "asset", "digest", "backend"]);
  const real = a.implementation === IMPLEMENTATION && a.asset === ASSET && a.digest === DIGEST && a.backend === "CPU/WASM";
  const fake = a.implementation === "fake" && a.asset === "fixture" && a.digest === "fixture" && a.backend === "fixture";
  if (!real && !fake) throw new Error("ATTRIBUTION");
  if (!Array.isArray(r.hands) || r.hands.length > 1 || (status !== "SUCCESS" && r.hands.length !== 0)) throw new Error("HANDS");
  const hands = r.hands.map((value: unknown): Hand => {
    const hasHandedness = value !== null && typeof value === "object" && Object.hasOwn(value, "handedness");
    const hand = closed(value, hasHandedness ? ["landmarks", "handedness"] : ["landmarks"]);
    if (!Array.isArray(hand.landmarks) || hand.landmarks.length !== 21) throw new Error("LANDMARKS");
    const landmarks = Object.freeze(hand.landmarks.map((point: unknown) => {
      const p = closed(point, ["x", "y", "z"]);
      return Object.freeze({ x: finite(p.x), y: finite(p.y), z: finite(p.z) });
    }));
    if (!hasHandedness) return Object.freeze({ landmarks });
    const h = closed(hand.handedness, ["label", "score"]);
    if (h.label !== "Left" && h.label !== "Right") throw new Error("HANDEDNESS");
    return Object.freeze({ landmarks, handedness: Object.freeze({ label: h.label, score: finite(h.score, 0, 1) }) });
  });
  return Object.freeze({
    schemaVersion: 1, frameId: integer(r.frameId, 0, 1_000_000_000),
    configurationRevision: "hand-local-v1", status, reason: r.reason as Reason,
    attribution: Object.freeze(real
      ? { implementation: IMPLEMENTATION, asset: ASSET, digest: DIGEST, backend: "CPU/WASM" as const }
      : { implementation: "fake" as const, asset: "fixture" as const, digest: "fixture", backend: "fixture" as const }),
    durationMs: finite(r.durationMs, 0, 3_600_000), hands: Object.freeze(hands),
  });
}
export function result(frameId: number, status: Status, reason: Reason, hands: readonly Hand[] = [], durationMs = 0): HandResult {
  return parseResult({ schemaVersion: 1, frameId, configurationRevision: "hand-local-v1", status, reason,
    attribution: { implementation: IMPLEMENTATION, asset: ASSET, digest: DIGEST, backend: "CPU/WASM" },
    hands, durationMs });
}

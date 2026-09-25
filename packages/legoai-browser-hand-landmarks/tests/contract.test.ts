import test from "node:test";
import assert from "node:assert/strict";
import { DEFAULT_CONFIG, parseConfig, parseFrame, parseResult, result } from "../src/contract.js";
import type { HandResult } from "../src/contract.js";
import { preflight } from "../src/adapter/client.js";
import { FramePump } from "../src/frame-pump.js";
import type { HandAdapter, LocalFrame } from "../src/frame-pump.js";
const hand = { landmarks: Array.from({ length: 21 }, () => ({ x: .5, y: .5, z: 0 })),
  handedness: { label: "Left" as const, score: .8 } };
test("closed configuration is copied and frozen", () => {
  const input = { ...DEFAULT_CONFIG };
  const config = parseConfig(input);
  input.maxWidth = 320;
  assert.equal(config.maxWidth, 640);
  assert.ok(Object.isFrozen(config));
});
for (const change of [{ schemaVersion: 2 }, { module: "arbitrary" }, { localOnly: false },
  { maxHands: 3 }, { maxHands: 4 }, { maxHands: 0 }, { maxHands: -1 },
  { maxHands: 1.5 }, { maxHands: "2" }, { maxHands: null }, { maxHands: NaN }, { approvedAsset: "https://example.invalid/model" }, { maxWidth: 9999 }]) {
  test("reject invalid configuration " + JSON.stringify(change), () => {
    assert.throws(() => parseConfig({ ...DEFAULT_CONFIG, ...change }));
  });
}
test("frame bounds checked before allocation", () => {
  const frame = { schemaVersion: 1, frameId: 1, timestampMs: 1, width: 640, height: 480 };
  assert.equal(parseFrame(frame, DEFAULT_CONFIG).width, 640);
  assert.throws(() => parseFrame({ ...frame, width: 641 }, DEFAULT_CONFIG));
  assert.throws(() => parseFrame({ ...frame, timestampMs: NaN }, DEFAULT_CONFIG));
});
test("zero hands is success; 21 plain landmarks are immutable", () => {
  assert.deepEqual(result(1, "SUCCESS", "OK").hands, []);
  const output = result(1, "SUCCESS", "OK", [hand]);
  assert.equal(output.hands[0]?.landmarks.length, 21);
  assert.ok(Object.isFrozen(output.hands[0]?.landmarks[0]));
});
for (const count of [0, 20, 22]) test("reject landmark count " + count, () => {
  assert.throws(() => result(1, "SUCCESS", "OK", [{ landmarks: Array.from({ length: count }, () => ({ x: 0, y: 0, z: 0 })) }]));
});
for (const coordinate of ["x", "y", "z"]) for (const number of [NaN, Infinity, -Infinity]) {
  test("reject nonfinite " + coordinate + String(number), () => {
    const landmarks = hand.landmarks.map(p => ({ ...p, [coordinate]: number }));
    assert.throws(() => result(1, "SUCCESS", "OK", [{ landmarks }]));
  });
}
test("too many hands, wrong score, mismatched status and unknown fields fail", () => {
  assert.throws(() => result(1, "SUCCESS", "OK", [hand, hand, hand]));
  assert.throws(() => result(1, "SUCCESS", "OK", [{ ...hand, handedness: { label: "Left", score: 1.1 } }]));
  assert.throws(() => result(1, "SUCCESS", "OK", [{ ...hand, handedness: { label: "Left", score: NaN } }]));
  const valid = result(1, "SUCCESS", "OK", [hand]);
  for (const change of [{ schemaVersion: 2 }, { status: "UNKNOWN" }, { status: "CANCELLED" },
    { extra: "not allowed" }, { attribution: { implementation: "untrusted" } }]) {
    assert.throws(() => parseResult({ ...valid, ...change }));
  }
});
test("the same consumer accepts a fake adapter with plain values", async () => {
  const outputs: HandResult[] = [];
  const fake: HandAdapter<LocalFrame> = {
    initialize: async () => result(0, "SUCCESS", "OK"),
    process: async request => parseResult({ ...result(request.frameId, "SUCCESS", "OK"),
      attribution: { implementation: "fake", asset: "fixture", digest: "fixture", backend: "fixture" } }),
    stop: async () => {},
  };
  const pump = new FramePump(fake, DEFAULT_CONFIG, async () => ({ width: 10, height: 10, close() {} }), o => outputs.push(o));
  pump.start();
  await pump.tick(1);
  assert.equal(outputs[0]?.attribution.implementation, "fake");
  assert.equal(outputs[0]?.status, "SUCCESS");
});

test("headless unsupported preflight does not request camera", () => {
  assert.equal(preflight().supported, false);
  assert.equal(preflight().reason, "BROWSER_APIS");
});

test("configuration is inert plain data, never class instances or getters", () => {
  class ExecutableConfiguration {}
  assert.throws(() => parseConfig(Object.assign(new ExecutableConfiguration(), DEFAULT_CONFIG)));
  let evaluated=false;
  const value={...DEFAULT_CONFIG};
  Object.defineProperty(value,"implementation",{enumerable:true,get(){evaluated=true;return "mediapipe-0.10.21";}});
  assert.throws(() => parseConfig(value));
  assert.equal(evaluated,false);
});

for (const maxHands of [1, 2] as const) test("accept bounded maxHands " + maxHands, () => {
  const config = parseConfig({ ...DEFAULT_CONFIG, maxHands });
  assert.equal(config.maxHands, maxHands);
  assert.ok(Object.isFrozen(config));
  assert.equal(DEFAULT_CONFIG.maxHands, 1);
});
test("two hands are copied, deeply immutable and bounded by selected configuration", () => {
  const input = { ...result(1, "SUCCESS", "OK"), hands: [hand, hand] };
  const output = parseResult(input, 2);
  assert.equal(output.hands.length, 2);
  for (const detected of output.hands) {
    assert.equal(detected.landmarks.length, 21);
    assert.notEqual(detected.landmarks, hand.landmarks);
    assert.ok(Object.isFrozen(detected));
    assert.ok(Object.isFrozen(detected.landmarks));
    assert.ok(Object.isFrozen(detected.landmarks[0]));
  }
  assert.ok(Object.isFrozen(output.hands));
  assert.throws(() => parseResult(input, 1));
});
for (const second of [
  { landmarks: hand.landmarks.slice(1) },
  { landmarks: hand.landmarks.map(p => ({ ...p, x: NaN })) },
  { ...hand, extra: true },
  { ...hand, handedness: { label: "Left", score: 2 } },
]) test("malformed second hand rejects entire result " + JSON.stringify(second), () => {
  assert.throws(() => parseResult({ ...result(1, "SUCCESS", "OK"), hands: [hand, second] }));
});

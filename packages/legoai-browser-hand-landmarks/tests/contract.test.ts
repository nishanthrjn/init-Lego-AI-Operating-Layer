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
  { maxHands: 2 }, { approvedAsset: "https://example.invalid/model" }, { maxWidth: 9999 }]) {
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
  assert.throws(() => result(1, "SUCCESS", "OK", [hand, hand]));
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

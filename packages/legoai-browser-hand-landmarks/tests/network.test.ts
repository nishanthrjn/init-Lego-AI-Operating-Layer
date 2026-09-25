import test from "node:test";
import assert from "node:assert/strict";
import { Inference } from "../src/adapter/inference.js";
import { DEFAULT_CONFIG, parseConfig } from "../src/contract.js";
test("tested inference flow has no fetch or fallback request, including errors", () => {
  const previous=globalThis.fetch;
  let calls=0;
  globalThis.fetch=async()=>{calls++;throw new Error("NETWORK_FORBIDDEN");};
  try {
    let closes=0;
    const frame={width:10,height:10,close(){closes++;}};
    const request={schemaVersion:1 as const,frameId:1,timestampMs:1,width:10,height:10};
    const inference=new Inference(DEFAULT_CONFIG,()=>({landmarks:[],handedness:[]}),()=>1);
    assert.equal(inference.run(request,frame).status,"SUCCESS");
    const failing=new Inference(DEFAULT_CONFIG,()=>{throw new Error("SDK diagnostic");},()=>1);
    assert.equal(failing.run(request,frame).status,"EXECUTION_FAILURE");
    assert.equal(calls,0); assert.equal(closes,2);
  } finally {globalThis.fetch=previous;}
});
test("unsupported input never reaches inference; duration deadline is truthful", () => {
  let calls=0;
  const frame={width:641,height:10,close(){}};
  const task=new Inference(DEFAULT_CONFIG,()=>{calls++;return {landmarks:[],handedness:[]};});
  const request={schemaVersion:1 as const,frameId:1,timestampMs:1,width:10,height:10};
  assert.equal(task.run(request,frame).status,"INVALID_INPUT");assert.equal(calls,0);
  let time=0;
  const slow=new Inference(DEFAULT_CONFIG,()=>({landmarks:[],handedness:[]}),()=>{time+=3000;return time;});
  assert.equal(slow.run(request,{width:10,height:10,close(){}}).status,"DEADLINE");
});

for (const maxHands of [1, 2] as const) for (const count of [0, 1, 2, 3]) {
  test(`inference respects selected bound ${maxHands} with ${count} hands`, () => {
    const previous = globalThis.fetch;
    globalThis.fetch = async () => { throw new Error("NETWORK_FORBIDDEN"); };
    let closed = 0;
    try {
      const task = new Inference(parseConfig({ ...DEFAULT_CONFIG, maxHands }), () => ({
        landmarks: Array.from({ length: count }, () => Array.from({ length: 21 }, () => ({ x: .5, y: .5, z: 0 }))),
        handedness: Array.from({ length: count }, () => [{ categoryName: "Left", score: .8 }]),
      }), () => 1);
      const output = task.run({ schemaVersion: 1, frameId: 1, timestampMs: 1, width: 10, height: 10 },
        { width: 10, height: 10, close() { closed++; } });
      assert.equal(output.status, count <= maxHands ? "SUCCESS" : "EXECUTION_FAILURE");
      assert.equal(output.hands.length, count <= maxHands ? count : 0);
      assert.equal(closed, 1);
    } finally { globalThis.fetch = previous; }
  });
}

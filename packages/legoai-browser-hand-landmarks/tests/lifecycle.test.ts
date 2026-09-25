import test from "node:test";
import assert from "node:assert/strict";
import { CameraLease, FramePump } from "../src/frame-pump.js";
import type { LocalFrame, HandAdapter } from "../src/frame-pump.js";
import { DEFAULT_CONFIG, parseConfig, result } from "../src/contract.js";
import type { HandResult } from "../src/contract.js";
import { WorkerHandAdapter } from "../src/adapter/client.js";
import type { Clock, WorkerTransport } from "../src/adapter/client.js";
function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>(done => { resolve = done; });
  return { promise, resolve };
}
class ManualClock implements Clock {
  actions = new Map<number, () => void>();
  next = 0;
  set(action: () => void): number { const id = ++this.next; this.actions.set(id, action); return id; }
  clear(handle: unknown): void { this.actions.delete(handle as number); }
  fire(): void { const actions = [...this.actions.values()]; this.actions.clear(); actions.forEach(a => a()); }
}
class FakeWorker implements WorkerTransport {
  message: (value: unknown) => void = () => {};
  error: () => void = () => {};
  terminated = 0;
  sent: unknown[] = [];
  autoClose = true;
  listen(message: (value: unknown) => void, error: () => void): void { this.message = message; this.error = error; }
  send(message: unknown): void {
    this.sent.push(message);
    if (this.autoClose && (message as {kind: string}).kind === "stop") this.message({kind: "closed"});
  }
  terminate(): void { this.terminated++; }
}
const request = { schemaVersion: 1 as const, frameId: 1, timestampMs: 1, width: 10, height: 10 };
function frame(): ImageBitmap { return { width: 10, height: 10, close() {} } as ImageBitmap; }
test("capture and inference share one slot; busy frames dropped without queue", async () => {
  const capture = deferred<LocalFrame>();
  const inference = deferred<HandResult>();
  let captures = 0, calls = 0, closes = 0;
  const outputs: HandResult[] = [];
  const adapter: HandAdapter<LocalFrame> = {
    initialize: async () => result(0, "SUCCESS", "OK"), stop: async () => {},
    process: async () => { calls++; return inference.promise; },
  };
  const pump = new FramePump(adapter, DEFAULT_CONFIG, () => { captures++; return capture.promise; }, o => outputs.push(o));
  pump.start();
  const first = pump.tick(1);
  for (let i = 0; i < 100; i++) await pump.tick(i + 2);
  assert.equal(captures, 1); assert.equal(calls, 0); assert.equal(pump.dropped, 100);
  capture.resolve({width:10,height:10,close(){closes++;}});
  await Promise.resolve();
  await pump.tick(102);
  assert.equal(calls, 1);
  pump.stop();
  inference.resolve(result(1, "SUCCESS", "OK"));
  await first;
  assert.equal(outputs.length, 0); assert.equal(closes, 1);
});
test("stop during acquisition closes late frame", async () => {
  const capture = deferred<LocalFrame>();
  let closes = 0, calls = 0;
  const adapter: HandAdapter<LocalFrame> = {
    initialize: async () => result(0, "SUCCESS", "OK"), stop: async () => {},
    process: async () => { calls++; return result(1, "SUCCESS", "OK"); },
  };
  const pump = new FramePump(adapter, DEFAULT_CONFIG, () => capture.promise, () => assert.fail());
  pump.start(); const pending = pump.tick(1); pump.stop();
  capture.resolve({width:10,height:10,close(){closes++;}});
  await pending;
  assert.equal(calls,0); assert.equal(closes,1);
});
test("camera ownership closes late permission results and repeated sessions", async () => {
  let stops = 0;
  const stream = {getTracks: () => [{stop: () => {stops++;}}]};
  const lease = new CameraLease<typeof stream>();
  const opening = deferred<typeof stream>();
  const pending = lease.acquire(() => opening.promise);
  lease.stop(); opening.resolve(stream);
  assert.equal(await pending, null);
  for (let i=0;i<5;i++) { await lease.acquire(async () => stream); lease.stop(); }
  assert.equal(stops,6);
});
test("deadline rejects acceptance and force terminates nonresponsive worker", async () => {
  const worker = new FakeWorker(); worker.autoClose = false;
  const clock = new ManualClock();
  const client = new WorkerHandAdapter(() => worker, clock);
  const initialization = client.initialize(DEFAULT_CONFIG);
  await Promise.resolve();
  worker.message(result(0,"SUCCESS","OK"));
  await initialization;
  const pending = client.process(request,frame());
  const oldListener = worker.message;
  clock.fire();
  assert.equal((await pending).status,"DEADLINE");
  oldListener(result(1,"SUCCESS","OK")); // discarded
  const stopped = client.stop();
  clock.fire();
  await stopped;
  assert.equal(worker.terminated,1); assert.equal(clock.actions.size,0);
});
test("cancellation and repeated start stop leave no pending worker timers", async () => {
  const workers: FakeWorker[] = [];
  const clock = new ManualClock();
  const client = new WorkerHandAdapter(() => { const w=new FakeWorker(); workers.push(w); return w; },clock);
  for (let i=0;i<4;i++) {
    const initializing = client.initialize(DEFAULT_CONFIG);
    await Promise.resolve();
    const worker = workers[i]; assert.ok(worker);
    worker.message(result(0,"SUCCESS","OK")); await initializing;
    const pending = client.process(request,frame());
    await client.stop();
    assert.equal((await pending).status,"CANCELLED");
    assert.equal(worker.terminated,1); assert.equal(clock.actions.size,0);
  }
});
test("stop before asynchronous initialization resumes does not create worker", async () => {
  let creations=0;
  const client = new WorkerHandAdapter(() => {creations++;return new FakeWorker();});
  const initialized=client.initialize(DEFAULT_CONFIG);
  await client.stop();
  assert.equal((await initialized).status,"CANCELLED"); assert.equal(creations,0);
});
test("malformed worker response fails safely without leaking response", async () => {
  const worker=new FakeWorker(); const client=new WorkerHandAdapter(()=>worker,new ManualClock());
  const initialized=client.initialize(DEFAULT_CONFIG);
  await Promise.resolve();
  worker.message({ rawSecret:"not accepted" });
  assert.equal((await initialized).reason,"OUTPUT");
  await client.stop();
});

for (const failure of ["capture", "inference", "close"] as const) {
  test("in-flight slot is released after " + failure + " failure", async () => {
    let captures = 0, calls = 0, closes = 0;
    const adapter: HandAdapter<LocalFrame> = {
      initialize: async () => result(0, "SUCCESS", "OK"), stop: async () => {},
      process: async request => {
        calls++;
        if (failure === "inference" && calls === 1) throw new Error("INFERENCE");
        return result(request.frameId, "SUCCESS", "OK");
      },
    };
    const outputs: HandResult[] = [];
    const pump = new FramePump(adapter, DEFAULT_CONFIG, async () => {
      captures++;
      if (failure === "capture" && captures === 1) throw new Error("CAPTURE");
      return { width: 10, height: 10, close() {
        closes++;
        if (failure === "close" && closes === 1) throw new Error("CLOSE");
      } };
    }, output => outputs.push(output));
    pump.start();
    await assert.rejects(pump.tick(1));
    await pump.tick(2);
    assert.equal(captures, 2);
    assert.equal(pump.dropped, 0);
    assert.equal(pump.submitted, failure === "capture" ? 1 : 2);
    assert.equal(outputs.at(-1)?.status, "SUCCESS");
    pump.stop();
  });
}

for (const maxHands of [1, 2] as const) {
  test("worker responses enforce requested maxHands " + maxHands, async () => {
    const worker = new FakeWorker();
    const client = new WorkerHandAdapter(() => worker, new ManualClock());
    const initializing = client.initialize(parseConfig({ ...DEFAULT_CONFIG, maxHands }));
    await Promise.resolve();
    assert.equal((worker.sent[0] as { config: { maxHands: number } }).config.maxHands, maxHands);
    worker.message(result(0, "SUCCESS", "OK"));
    await initializing;
    const pending = client.process(request, frame());
    const hand = { landmarks: Array.from({ length: 21 }, () => ({ x: .5, y: .5, z: 0 })) };
    worker.message(result(1, "SUCCESS", "OK", [hand, hand]));
    const output = await pending;
    assert.equal(output.status, maxHands === 2 ? "SUCCESS" : "EXECUTION_FAILURE");
    assert.equal(output.hands.length, maxHands === 2 ? 2 : 0);
    await client.stop();
  });
}

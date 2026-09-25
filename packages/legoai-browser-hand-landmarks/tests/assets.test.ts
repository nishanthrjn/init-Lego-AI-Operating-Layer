import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { ASSETS } from "../src/adapter/approved.js";
import { verifyAsset, loadApprovedAssets } from "../src/adapter/assets.js";
test("shipped bytes match every fixed descriptor; altered bytes fail", async () => {
  for (const descriptor of ASSETS) {
    const bytes=await readFile("assets/"+descriptor.path.split("/").at(-1));
    const copy=new Uint8Array(bytes).buffer;
    await verifyAsset(copy,descriptor);
    const mutated = new Uint8Array(copy);
    mutated[0] = (mutated[0] ?? 0) ^ 1;
    await assert.rejects(verifyAsset(copy,descriptor));
    await assert.rejects(verifyAsset(new ArrayBuffer(1),descriptor));
  }
});
test("oversized stream and unsupported origin rejected", async () => {
  let reads=0;
  const fetcher: typeof fetch=async()=>{
    reads++;
    return new Response(new Uint8Array(ASSETS[0].bytes+1));
  };
  await assert.rejects(loadApprovedAssets("https://local.invalid",fetcher));
  assert.equal(reads,1);
  await assert.rejects(loadApprovedAssets("file://",fetcher));
});

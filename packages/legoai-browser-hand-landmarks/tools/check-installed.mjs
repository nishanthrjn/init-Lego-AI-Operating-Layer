import assert from "node:assert/strict";
import { readFile, access } from "node:fs/promises";
import { createHash } from "node:crypto";
import { fileURLToPath } from "node:url";
process.chdir(fileURLToPath(new URL("../",import.meta.url)));
const pkg=JSON.parse(await readFile("package.json","utf8"));
const lock=JSON.parse(await readFile("package-lock.json","utf8"));
assert.equal(lock.lockfileVersion,3);
assert.deepEqual(lock.packages[""].dependencies,pkg.dependencies);
assert.deepEqual(lock.packages[""].devDependencies,pkg.devDependencies);
for(const [name,version] of Object.entries({...pkg.dependencies,...pkg.devDependencies})) {
  const installed=JSON.parse(await readFile("node_modules/"+name+"/package.json","utf8"));
  assert.equal(installed.version,version,"Installed version differs from exact pin: "+name);
}
await access("node_modules/esbuild/bin/esbuild");
const manifest=JSON.parse(await readFile("assets/manifest.json","utf8"));
for(const descriptor of manifest.files) {
  const bytes=await readFile("assets/"+descriptor.path.split("/").at(-1));
  assert.equal(bytes.byteLength,descriptor.bytes);
  assert.equal(createHash("sha256").update(bytes).digest("hex"),descriptor.sha256);
}
console.log("Exact direct dependencies and approved shipped asset digests verified; npm ls checks the dependency tree.");

for(const [name,digest] of Object.entries(manifest.sdkFiles)) {
  const bytes=await readFile("node_modules/@mediapipe/tasks-vision/"+name);
  assert.equal(createHash("sha256").update(bytes).digest("hex"),digest,"SDK file integrity: "+name);
}
const approved=await readFile("src/adapter/approved.ts","utf8");
const serialized=approved.split("export const ASSETS = ")[1].split(" as const;")[0];
assert.deepEqual(JSON.parse(serialized),manifest.files,"Runtime asset descriptors differ from manifest");

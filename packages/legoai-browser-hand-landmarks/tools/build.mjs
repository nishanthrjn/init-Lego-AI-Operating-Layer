import { build } from "esbuild";
import { mkdir, cp, copyFile, readFile, writeFile } from "node:fs/promises";
import { createHash } from "node:crypto";
import { fileURLToPath } from "node:url";
import path from "node:path";
import { spawnSync } from "node:child_process";
const root = fileURLToPath(new URL("../", import.meta.url));
const example = path.resolve(root, "../../examples/browser-hand-landmarks");
process.chdir(root);
await mkdir("dist", { recursive: true });
await mkdir(path.join(example, "dist"), { recursive: true });
const types = spawnSync(process.execPath, ["node_modules/typescript/bin/tsc", "-p", "tsconfig.types.json"], {stdio:"inherit", shell:false});
if (types.status !== 0) process.exit(types.status ?? 1);
await build({entryPoints:["src/index.ts"], outfile:"dist/index.js", bundle:true, format:"esm", platform:"browser", target:"es2022", sourcemap:false});
await build({entryPoints:["src/adapter/worker.ts"], outfile:"dist/worker.js", bundle:true, format:"iife", platform:"browser", target:"es2022", sourcemap:false, legalComments:"eof"});
await build({entryPoints:[path.join(example,"main.ts")], outfile:path.join(example,"dist/main.js"), bundle:true, format:"esm", platform:"browser", target:"es2022", sourcemap:false});
await copyFile("dist/worker.js",path.join(example,"dist/worker.js"));
await cp("assets",path.join(example,"dist/assets"),{recursive:true});
for(const name of ["index.html","style.css"]) await copyFile(path.join(example,name),path.join(example,"dist",name));
const manifest = {};
for(const name of ["main.js","worker.js","index.html","style.css"]) {
  const bytes=await readFile(path.join(example,"dist",name));
  manifest[name]={sha256:createHash("sha256").update(bytes).digest("hex"),bytes:bytes.byteLength};
}
await writeFile(path.join(example,"dist/build-integrity.json"),JSON.stringify(manifest,null,2)+"\n");
console.log("Browser package and static example built. Runtime qualification remains pending.");

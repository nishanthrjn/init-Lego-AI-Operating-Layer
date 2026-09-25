import assert from "node:assert/strict";
import { readFile, readdir } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import path from "node:path";
import ts from "typescript";
const root=fileURLToPath(new URL("../",import.meta.url));
const repo=path.resolve(root,"../..");
const architecture=process.argv.includes("--architecture");
async function sources(directory) {
  const output=[];
  for(const item of await readdir(directory,{withFileTypes:true})) {
    const name=path.join(directory,item.name);
    if(item.isDirectory()) output.push(...await sources(name));
    else if(name.endsWith(".ts")) output.push(name);
  }
  return output;
}
const files=[...await sources(path.join(root,"src")),...await sources(path.join(root,"tests")),
  path.join(repo,"examples/browser-hand-landmarks/main.ts")];
for(const file of files) {
  const source=await readFile(file,"utf8");
  const tree=ts.createSourceFile(file,source,ts.ScriptTarget.Latest,true);
  assert.equal(tree.parseDiagnostics.length,0,"Syntax diagnostics: "+file);
  if(!architecture || file.includes(path.sep+"tests"+path.sep)) continue;
  const worker=file.endsWith(path.join("adapter","worker.ts"));
  const assets=file.endsWith(path.join("adapter","assets.ts"));
  function visit(node) {
    if(ts.isImportDeclaration(node)) {
      const module=node.moduleSpecifier.text;
      if(module.includes("@mediapipe/")) assert.ok(worker,"SDK import outside worker");
      if(file.endsWith("contract.ts")) assert.fail("Task values must not import implementation/browser packages");
    }
    if(ts.isCallExpression(node) && node.expression.kind===ts.SyntaxKind.ImportKeyword) assert.fail("No dynamic imports");
    if(ts.isIdentifier(node)) {
      assert.ok(!["eval","XMLHttpRequest","WebSocket","sendBeacon","innerHTML"].includes(node.text),"Forbidden code path "+node.text+" in "+file);
      if(node.text==="fetch") assert.ok(assets,"Network API outside initialization assets");
    }
    ts.forEachChild(node,visit);
  }
  visit(tree);
}
if(architecture) {
  const pkg=JSON.parse(await readFile(path.join(root,"package.json"),"utf8"));
  assert.deepEqual(Object.keys(pkg.dependencies),["@mediapipe/tasks-vision"]);
  assert.deepEqual(Object.keys(pkg.devDependencies).sort(),["@types/node","esbuild","typescript"]);
  for(const version of Object.values({...pkg.dependencies,...pkg.devDependencies})) assert.match(version,/^\d+\.\d+\.\d+$/);
  const core=await readFile(path.join(repo,"pyproject.toml"),"utf8");
  assert.ok(!/mediapipe|onnxruntime|legoai-browser/.test(core),"Browser dependency leaked into Python metadata");
  console.log("Architecture: isolated adapter imports, closed dependency pins, no application egress APIs.");
} else console.log("TypeScript source syntax inspected; no auto-fixes.");

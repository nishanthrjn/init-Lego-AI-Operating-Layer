// Static GET/HEAD hosting only. No uploads, API, telemetry or development websocket.
import http from "node:http";
import { readFile, stat } from "node:fs/promises";
import { createReadStream } from "node:fs";
import { fileURLToPath } from "node:url";
import path from "node:path";
const root=fileURLToPath(new URL("../../../examples/browser-hand-landmarks/dist/",import.meta.url));
try {await stat(path.join(root,"main.js"));} catch {
  console.error("Build missing. Run python validate_browser_hand_landmark.py from the repository root first.");
  process.exit(1);
}
const manifest=JSON.parse(await readFile(path.join(root,"assets/manifest.json"),"utf8"));
const allowed=new Set(["/index.html","/main.js","/worker.js","/style.css","/build-integrity.json",
  "/assets/manifest.json","/assets/LICENSE","/assets/THIRD-PARTY-NOTICES.md", ...manifest.files.map(x=>x.path)]);
const mime={".html":"text/html; charset=utf-8",".js":"text/javascript; charset=utf-8",".css":"text/css; charset=utf-8",
  ".json":"application/json",".wasm":"application/wasm",".task":"application/octet-stream"};
const csp="default-src 'none'; script-src 'self' blob: 'wasm-unsafe-eval'; worker-src 'self' blob:; connect-src 'self' blob:; style-src 'self'; img-src 'self' blob:; media-src 'self' blob:; object-src 'none'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'";
const server=http.createServer(async(req,res)=>{
  if(!["GET","HEAD"].includes(req.method??"")) {res.writeHead(405);res.end();return;}
  if(!["127.0.0.1:5174","localhost:5174"].includes(req.headers.host??"")) {
    res.writeHead(400);res.end();return;
  }
  let pathname;
  try { pathname=new URL(req.url??"/","http://127.0.0.1:5174").pathname; }
  catch { res.writeHead(400);res.end();return; }
  const resource=pathname==="/" ? "/index.html" : pathname;
  if(!allowed.has(resource)) {res.writeHead(404);res.end();return;}
  const file=path.join(root,resource.slice(1));
  try {
    const metadata=await stat(file);
    res.writeHead(200,{
      "Content-Type":mime[path.extname(file)]??"text/plain; charset=utf-8",
      "Content-Length":metadata.size,"Cache-Control":"no-store",
      "Content-Security-Policy":csp,"X-Content-Type-Options":"nosniff",
      "Referrer-Policy":"no-referrer","Permissions-Policy":"camera=(self), microphone=()",
    });
    if(req.method==="HEAD") res.end(); else createReadStream(file).on("error",()=>res.destroy()).pipe(res);
  } catch {res.writeHead(404);res.end();}
});
server.on("error",()=>{console.error("Static host could not bind 127.0.0.1:5174.");process.exitCode=1;});
server.listen(5174,"127.0.0.1",()=>console.log("Open http://127.0.0.1:5174 — camera validation is manual."));

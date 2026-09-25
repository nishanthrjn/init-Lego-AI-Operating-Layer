# Browser Hand-Landmark Local Inference Vertical Slice

IMPLEMENTATION COMPLETE — LOCAL VALIDATION PENDING.
No automated qualification, production build or real camera experiment has been
run internally. This milestone does not alter M8.3's pending validation status.
The preceding [impact assessment](BROWSER-EDGE-AI-CAPABILITY-IMPACT-ASSESSMENT.md)
remains authoritative.

## Scope and ownership

One optional browser package, packages/legoai-browser-hand-landmarks, and one
plain HTML/TypeScript consumer, examples/browser-hand-landmarks. Python Core,
ModelPort, Catalog, governance and canonical execution contracts are unchanged.
The local hand task is not a canonical CV ontology or a second LegoAI runtime.
There is no Agent, LLM, gesture, DOM control, ONNX, server API, cloud fallback,
remote telemetry or account system.

The consumer imports plain HandResult values and the package facade. Only
src/adapter/worker.ts imports MediaPipe. HTMLVideoElement/MediaStream belong to
example acquisition; ImageBitmap transfer and MediaPipe sessions stay in the
browser-private adapter boundary. No SDK object crosses the result contract.

## Pinned tuple and assumptions

- @mediapipe/tasks-vision 0.10.21; exact npm lockfile.
- Hand Landmarker float16/1 from the versioned official Google model URL.
- Model SHA-256:
  fbc2a30080c3c557093b5ddfc334698132eb341044ccee322ccf8bcf3607cde1.
- Apache-2.0 notices, file hashes, byte counts and sources are under package assets/.
- Qualification target: desktop Chromium Chrome/Edge 140+ on Windows with a camera,
  secure localhost context, workers, ImageBitmap, OffscreenCanvas, WebAssembly,
  Web Crypto and worker WebGL2. This is an assumption to verify, not a tested
  browser-version matrix. Record the exact browser/version in the smoke evidence.
- CPU delegate and non-SIMD WASM are explicit; no WebGPU abstraction or backend
  optimizer. MediaPipe still needs browser graphics support for image processing.
- Package source inspection confirmed an importScripts loader path. esbuild emits
  one classic IIFE worker, not an ES-module worker. Actual compatibility remains
  subject to the manual smoke test.

The upstream guide describes synchronous detection and recommends workers.
[MediaPipe browser guide](https://developers.google.com/edge/mediapipe/solutions/vision/hand_landmarker/web_js).
Build tools are pinned TypeScript 5.9.3, esbuild 0.25.12 and @types/node 24.10.0;
Node 24 is the supported tooling line. No framework, Vite, test framework or
monorepo orchestrator was added. Tests use node:test.

## Contract and limits

Schema version 1 has closed configuration, frame metadata and result shapes.
hand-local-v1 denotes one exact fixed configuration; changing its meaning requires
a new revision and deliberate implementation update. It is not a server-issued
ConfigurationRevisionRef, admission or permission.

Configuration permits exactly the built-in implementation/asset, VIDEO mode,
one hand, localOnly=true, dimensions at most 640 by 480, a 30-second initialization
acceptance deadline, 2-second frame deadline and 60-second camera session limit.
No arbitrary module, class, model URL, endpoint or metadata is accepted.
Runtime validators copy and freeze nested accepted values.

SUCCESS permits zero or one hand; a detected hand has exactly 21 finite x/y/z
points in MediaPipe's documented landmark order (wrist, thumb, index, middle,
ring, little finger). x/y use image-relative coordinates. z is relative depth
with wrist origin, not calibrated distance. Values are not silently clamped.
Handedness label is Left/Right with a finite score in [0,1]. The preview and
overlay are unmirrored. Handedness is retained as the model's estimate, without correcting for selfie/mirroring assumptions; it must
not be used as verified identity or anatomical truth without consumer evaluation.

Other statuses are UNSUPPORTED, INVALID_INPUT, INITIALIZATION_FAILURE,
EXECUTION_FAILURE, DEADLINE and CANCELLED with closed safe reason codes.
Camera permission denial is a browser/user decision, never LegoAI authorization
denial. SDK output is converted and validated before exposure; world coordinates,
tracking identity and raw SDK metadata are discarded.

## Worker, camera and backpressure

The UI requests camera permission only after explicit Start and successful
initialization. A warm-up graph invocation is part of initialization and uses
a synthetic local 2x2 canvas, not camera data.

FramePump reserves a slot before asynchronous capture and holds it through
inference. While busy, incoming frame opportunities are dropped; no pending
frame queue exists. At most one ImageBitmap capture/inference is in flight.
Frames close on completion, error, stale-generation discard or transfer cleanup.
Processed/dropped counters saturate at a fixed ceiling.

Stop immediately stops all owned tracks, cancels animation/session scheduling,
clears the overlay, and invalidates result acceptance. The client requests task
close, waits at most 150 ms for acknowledgment, then terminates the worker.
Restart uses a fresh worker/task. A pending browser permission prompt cannot be
programmatically dismissed: restart is disabled until it settles; late streams
are stopped. Page hide/visibility loss also stops the session.

Deadline/cancellation means acceptance ended and cleanup was requested. It does
not prove hard GPU/native interruption or zero consumed resources. Browser timers
may be delayed or throttled. Worker termination is a containment action, not
evidence of device-level cancellation. Bounds are not hard GPU/memory quotas.

## Asset integrity and local-only scope

The task, WASM and loader JS are shipped/self-hosted; no runtime CDN is used.
Only fixed descriptor locations under /assets are fetched, during initialization,
without credentials and with redirects rejected. Stream reads reject oversized
responses; exact length and SHA-256 are checked before model/loader use.
Verified executable/WASM bytes are supplied through temporary blob URLs, then
revoked. Initialization failure has no remote fallback.

The installed-tree check compares exact dependency pins, shipped hashes and SDK
source hashes. npm ci uses the committed lockfile. Generated JS bundle digests
are recorded at build time; the browser does not self-attest its initial JS
bundle or deployment integrity. Pinned source plus build hashes are not a claim
of reproducible binaries or supply-chain attestation.

The static host serves an allowlist with GET/HEAD only, restrictive CSP, no
analytics and no development websocket. Inference/conversion source has no fetch
or upload path. The negative-network test runs the real conversion/processing
code with a fake detector and forbidden fetch; it does not execute MediaPipe.
Manual Network inspection must verify the real path performs no requests during
camera processing. Static initialization fetches, including blob resources, are
expected before camera permission.

Frames and derived landmarks remain local. Only bounded safe statuses,
attribution, durations and counters appear as diagnostics; landmarks are drawn
locally, never logged. These records are not canonical Evidence. The guarantee
covers shipped code under its trusted browser/dependency assumptions, not a
compromised browser, malicious extension, hostile OS or arbitrary modified code.

## One validation launcher

From the repository root:

    python .\validate_browser_hand_landmark.py

It uses only the standard library (Python 3.11+), shell=False, fixed commands,
streamed stdout/stderr and failure exit codes. On Windows it invokes npm-cli.js
through node.exe, not a shell command string. It never installs, edits source,
auto-fixes, commits or changes Git state.

If dependencies are absent, it fails with this explicit one-time setup command:

    npm.cmd --prefix packages/legoai-browser-hand-landmarks ci --ignore-scripts

Then rerun the launcher. This resolves the request's no-automatic-install rule:
phase 2 checks installed lockfile consistency and asset integrity rather than
silently running npm ci. Neither installation nor validation was performed
internally; only lockfile generation and static source inspection were done.

Phases cover environment; dependency integrity; strict typecheck; static checks;
compiled node:test contract/asset tests; worker/backpressure/camera ownership tests;
negative-network tests; package/static-example builds; dependency architecture;
affected Python packaging/import inspection; and git diff --check. No Python
production code changed, so the launcher does not run unrelated Python tests.
The added boundaries are checked without modifying Core metadata.

Passing automated checks prints AUTOMATED LOCAL VALIDATION PASSED and
MANUAL BROWSER VALIDATION STILL REQUIRED. Failed phases stop immediately;
later required phases are not reported passed.

## Manual smoke test after automated validation

1. Start the built example with one command:

       npm.cmd --prefix packages/legoai-browser-hand-landmarks run dev

2. Open http://127.0.0.1:5174 in the target browser.
3. Open DevTools Network, clear its log, click Start Camera and grant permission.
   Initialization first retrieves fixed local assets. Put one hand in view and
   confirm the 21-point overlay updates without gesture/cursor effects.
4. Verify no camera/image uploads, inference API calls or telemetry requests.
   After initialization, processing should add no requests. Do not paste raw
   media, landmarks or an unredacted HAR back into the conversation.
5. Remove the hand: zero hands is SUCCESS. Click Stop: camera indicator turns
   off, overlay clears and inference stops. Start again; no duplicate stream,
   worker or animation activity should remain.
6. Deny camera permission on a fresh permission prompt: expect a safe denial
   message and no crash. Restore permission through browser settings afterward.
7. Switch DevTools to offline only after initialization: the current initialized
   session should continue within its 60-second bound. Stop/restart or reload
   while offline is not guaranteed: assets are fetched no-store and no persistent
   cache/service worker is implemented. Restore network before another start.
8. On a browser lacking required APIs, expect UNSUPPORTED. A present API whose
   initialization fails produces a safe initialization failure. Do not fake
   successful support or invoke another provider.

Paste back: the full launcher output including the final summary (or first
failure and exit code); exact Node/browser versions; whether overlay, no-hand,
denial, Stop/restart and offline-after-initialization behaved as above; whether
Network showed only initialization assets and no later egress; and any safe
status/reason or sanitized console error. State which manual checks were not
performed. No qualification until automated and real-browser evidence is supplied.

## Static review and deferred work

Source review covers closed shapes, unknown revisions, dimension checks, asset
allowlisting, absence of upload/analytics, worker cleanup, late-result discard,
permission races and package import direction. Syntax inspection is not validation.
Full tests/builds, SDK execution and webcam behavior remain user-run.

Do not add gestures/AirTouch, Face/Pose, ONNX/WebGPU, generic inference/model
contracts, browser governance/Plugin marketplaces, remote telemetry, servers,
accounts, caches/sync, training, conversion or deployment in this milestone.
No production or M8.3 qualification claim follows from implementation.

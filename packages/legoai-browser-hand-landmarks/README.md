# Browser hand landmarks

Implementation complete; local automated and camera validation pending.
No Python Core dependency or contract changes. M8.3 status is unchanged.

This isolated TypeScript package owns one versioned hand task, a classic
MediaPipe worker, asset verification, and bounded browser-private lifecycle code.
The plain HTML consumer lives in examples/browser-hand-landmarks.

See [implementation and validation instructions](../../planning/BROWSER-HAND-LANDMARK-VERTICAL-SLICE.md).
From the repository root run:

    python .\validate_browser_hand_landmark.py

The launcher never installs dependencies. If it reports missing dependencies,
explicitly run its printed setup command, then rerun validation:

    npm.cmd --prefix packages/legoai-browser-hand-landmarks ci --ignore-scripts

After automated validation, start the built example:

    npm.cmd --prefix packages/legoai-browser-hand-landmarks run dev

Open http://127.0.0.1:5174. No camera tests have been run internally.

The standalone package build emits dist/index.js, dist/worker.js and declarations.
Its WorkerHandAdapter expects the fixed worker route /worker.js and approved
/assets routes; the included static example supplies them. This is not arbitrary
deployment discovery, a public Plugin registry, or a general inference Port.

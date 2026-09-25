# Browser hand landmarks

The one-hand slice is locally qualified per user-reported automated and manual
validation. The bounded two-hand extension requires fresh local validation.
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

## Bounded hand count

`HandConfig.maxHands` accepts only numeric literals 1 or 2, with default 1.
Use `parseConfig({ ...DEFAULT_CONFIG, maxHands: 2 })` for a frozen two-hand
configuration. Other fixed fields and resource limits remain unchanged.
`configurationRevision` identifies the local contract profile; maxHands is an
explicit session parameter, not inferred from the result revision alone.
The worker receives this validated configuration and passes maxHands as MediaPipe
numHands. Inference, worker response acceptance and the frame pump enforce the
selected maximum. Standalone parseResult accepts at most two hands, or takes an
explicit maximum of 1 or 2. Each hand has exactly 21 finite landmarks.
Array order is observational only, not persistent physical hand identity.

In the example, stop and choose **Maximum hands: 2**, then Start Camera. The
renderer uses the same color for every hand; it does not assign tracking IDs.

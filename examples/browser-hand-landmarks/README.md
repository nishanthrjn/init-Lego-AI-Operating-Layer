# Local hand-landmark example

Plain HTML/TypeScript consumer; no frontend framework or backend API.
See [validation and manual smoke procedure](../../planning/BROWSER-HAND-LANDMARK-VERTICAL-SLICE.md).

From the repository root, after installing dependencies explicitly if prompted:

    python .\validate_browser_hand_landmark.py
    npm.cmd --prefix packages/legoai-browser-hand-landmarks run dev

Open http://127.0.0.1:5174. Click Start Camera, grant permission and show one hand.
Stop must turn off the camera indicator. Real camera validation remains pending.

## Camera-path diagnostic follow-up

Status: static review complete; automated revalidation and real browser validation
required. The prior 36 passing tests do not qualify these changes.

Confirmed code defect: the camera acquisition catch also handled playback errors,
mislabeling playback denial as camera permission denial. Readiness is now bounded
by a 10-second wait, observes loadedmetadata/loadeddata/canplay/playing/resize,
and requires play success, current frame data and nonzero dimensions. Stop cancels
the wait and removes its listeners. The reported frozen preview's root cause is
not established without the new local diagnostics. Touch recognition is a manual
test expectation error: gestures and DOM control remain out of scope.

Static camera-path audit:

- The acquired stream is assigned to video.srcObject; muted inline playback is
  requested. Playback failure has its own safe code.
- Each free capture creates a fresh ImageBitmap. Transfer is to one classic
  worker; the worker closes the received bitmap. The pump releases its slot on
  success, rejection, cancellation and even a failing frame close. No queue added.
- VIDEO inference uses increasing requestAnimationFrame timestamps, with duplicate
  video times skipped; inference validates finite, strictly increasing timestamps.
- The installed 0.10.21 SDK has an importScripts worker loading path and an
  OffscreenCanvas path. The worker probes WebGL2 and warms up the graph before
  reporting ready. This is source evidence, not proof of target-browser support.
- Fixed /assets URLs match the static host allowlist and build copies. Verified
  loader/WASM bytes use blob URLs; the model is passed as bytes. CSP permits these
  local resources. No static path mismatch was found; check actual Network results.
- Overlay backing width/height use intrinsic video dimensions, including changes;
  CSS scales video and canvas together. Neither is mirrored.
- Safe diagnostics show readiness, dimensions, submitted/completed/dropped counts,
  and distinct stage errors. No frames, landmarks or raw exception objects are logged.

Rebuild through the authoritative launcher, then serve:

```powershell
python .\validate_browser_hand_landmark.py
npm.cmd --prefix packages/legoai-browser-hand-landmarks run dev
```

Open http://127.0.0.1:5174 and reload after rebuilding (the server serves dist).
Press Start Camera and grant access. Confirm live video and camera/worker/MediaPipe
ready values. Move one hand: completed counts must increase and 21 points follow
it. Remove the hand: expect successful zero-hand status. Stop: camera indicator
off. Start again: tracking resumes. Inspect DevTools Network for local assets
and no image/frame/landmark uploads or inference endpoint. Keep the page visible;
hiding it deliberately stops the session, as does its 60-second limit.

Report browser name/version, safe panel values and counts/error code, whether the
preview moves, and whether the overlay moves. Do not send images, frames or
biometric landmark data. If only VIDEO_WAITING_FOR_FRAME appears, the preview is
not producing new usable frames; if submitted advances but completed does not,
report the eventual worker/frame deadline or error code.

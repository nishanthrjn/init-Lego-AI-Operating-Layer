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

### Initialization failure follow-up

Static review found a code defect in error propagation: blob URL creation was
outside the initialization catch, and the async message-handler call had no
rejection handler. Such failures bypassed a structured initialization response
and waited for the client's 30-second deadline. Missing asset buffers also
returned silently. These paths now return an explicit initialization failure;
partially created blob URLs are revoked. No inference moved to the UI thread.

The reported loading symptom is not yet attributed to this defect: browser/version,
safe panel values and network/console errors were supplied only as placeholders.
Worker compatibility is therefore unconfirmed, not a demonstrated blocker.
The example uses the fixed static host (not Vite), with /worker.js and /assets/*
matching the build output and allowlist. The pinned SDK maps the WASM filename to
its verified blob URL and receives model bytes directly. Frame submission starts
only after worker initialization and camera readiness; VIDEO timestamps increase.
A camera permission request can remain pending until the browser/user settles it.
Report the actual safe status to distinguish that from worker initialization.

Only static inspection was performed for this follow-up. Rerun the authoritative
validation command above, restart the static host and reload before manual checks.

### Raw camera/source isolation

Manual evidence: 287 submissions and 286 completed results before the session
limit establish an active inference loop. False readiness after cleanup describes
the stopped state, not startup failure. The black preview's root cause remains
unclassified until source isolation is performed.

Static review found no application spinner or opaque overlay: video is displayed,
the overlay is transparent and cleared with clearRect, and capture uses a fresh
createImageBitmap(video), not the overlay or a placeholder. Explicit stacking and
transparency now document that layout. Mirroring remains unchanged.

After rebuilding through the validation launcher and reloading the example:

1. Press **Preview camera only**, grant access and verify a live image. This mode
   creates no worker, loads no model, captures no inference bitmap and hides the
   overlay. Worker readiness false and zero submissions are expected.
2. Stop, select a physical camera from **Local camera**, and retry raw preview if
   necessary. Devices are listed after permission; selection and identifiers stay
   in page memory only. No persistence, logging or transmission is added.
3. Stop and press **Start Camera** using the same selected device. Verify live video
   and increasing submitted/completed counts. The brightness bucket samples the
   exact bitmap transferred to the worker, on a disposable 16x12 local canvas.
   Only NEAR_BLACK/NORMAL/BRIGHT/UNAVAILABLE is displayed; no pixels are retained or
   exposed. A bucket cannot prove meaningful content or hand visibility.
4. Show one hand and verify 21 moving landmarks. Remove it and expect successful
   zero-hand status. Stop and confirm camera indicator off; restart and repeat.
5. Inspect Network for no frame/landmark uploads. Report browser/version, raw versus
   normal visibility, safe counters and visual-signal bucket; no camera images.

A black raw preview narrows investigation to camera selection/device/browser
playback; live raw video but black normal mode points to integration/rendering.
Neither diagnosis is established by a successful inference response alone.
The 60-second limit remains; a separate last-session summary preserves counters
before cleanup while current counters/readiness describe the stopped session.

Only static inspection performed for these changes; local validation pending.

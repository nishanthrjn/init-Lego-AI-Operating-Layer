# Pinned third-party assets

MediaPipe Tasks Vision 0.10.21: Apache-2.0, Google/MediaPipe authors.
WASM loader/binary are unmodified files from the exact npm distribution.
Package source: https://registry.npmjs.org/@mediapipe/tasks-vision/-/tasks-vision-0.10.21.tgz
License copy: LICENSE, obtained from the upstream v0.10.21 tag.
https://github.com/google-ai-edge/mediapipe/blob/v0.10.21/LICENSE

Hand Landmarker bundle: hand_landmarker/hand_landmarker/float16/1,
Google MediaPipe palm detection and hand landmark models, Apache-2.0.
The upstream Hand Tracking model card identifies Apache License Version 2.0:
https://storage.googleapis.com/mediapipe-assets/Model%20Card%20Hand%20Tracking%20(Lite_Full)%20with%20Fairness%20Oct%202021.pdf
Versioned asset source:
https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task

manifest.json records actual SHA-256 hashes and byte counts of retained files.
The npm lockfile additionally records distribution integrity; sdkFiles records
the imported JS and declaration source hashes. Generated main/worker bundles
are hashed into build-integrity.json during the user build, not represented as
a precomputed reproducible-build or browser attestation claim.
Original upstream copyright/license headers in the loader are retained.
No private imagery or inference fixture image is distributed.

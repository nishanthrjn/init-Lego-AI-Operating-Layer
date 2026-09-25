/* Fixed build inputs, never selected from arbitrary URLs. */
export const ASSETS = [
  {
    "id": "vision_wasm_nosimd_internal.js",
    "path": "/assets/vision_wasm_nosimd_internal.js",
    "sha256": "927def7b465c51b86e4b3060f93646aca4e27121f4b8fc0483786e407ea9cf1f",
    "bytes": 204137,
    "format": "javascript",
    "source": "https://registry.npmjs.org/@mediapipe/tasks-vision/-/tasks-vision-0.10.21.tgz"
  },
  {
    "id": "vision_wasm_nosimd_internal.wasm",
    "path": "/assets/vision_wasm_nosimd_internal.wasm",
    "sha256": "3821ea9b1f7fb8c549ef2a064ef5c85750bf375c545a49fd6eea0df44a95f1f4",
    "bytes": 9448638,
    "format": "wasm",
    "source": "https://registry.npmjs.org/@mediapipe/tasks-vision/-/tasks-vision-0.10.21.tgz"
  },
  {
    "id": "hand-landmarker-float16-v1",
    "path": "/assets/hand_landmarker.task",
    "sha256": "fbc2a30080c3c557093b5ddfc334698132eb341044ccee322ccf8bcf3607cde1",
    "bytes": 7819105,
    "format": "mediapipe-task",
    "source": "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task"
  }
] as const;

# Local hand-landmark example

Plain HTML/TypeScript consumer; no frontend framework or backend API.
See [validation and manual smoke procedure](../../planning/BROWSER-HAND-LANDMARK-VERTICAL-SLICE.md).

From the repository root, after installing dependencies explicitly if prompted:

    python .\validate_browser_hand_landmark.py
    npm.cmd --prefix packages/legoai-browser-hand-landmarks run dev

Open http://127.0.0.1:5174. Click Start Camera, grant permission and show one hand.
Stop must turn off the camera indicator. Real camera validation remains pending.

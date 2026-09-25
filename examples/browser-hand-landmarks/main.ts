import {
  CameraLease, DEFAULT_CONFIG, FramePump, WorkerHandAdapter, preflight,
} from "../../packages/legoai-browser-hand-landmarks/src/index.js";
import type { HandResult } from "../../packages/legoai-browser-hand-landmarks/src/index.js";

function element<T extends HTMLElement>(id: string, kind: { new(): T }): T {
  const found = document.getElementById(id);
  if (!(found instanceof kind)) throw new Error("Missing example element");
  return found;
}
const video = element("video", HTMLVideoElement);
const overlay = element("overlay", HTMLCanvasElement);
const startButton = element("start", HTMLButtonElement);
const stopButton = element("stop", HTMLButtonElement);
const status = element("status", HTMLParagraphElement);
const diagnostics = element("diagnostics", HTMLPreElement);
const camera = new CameraLease<MediaStream>();
let adapter: WorkerHandAdapter | undefined;
let pump: FramePump<ImageBitmap> | undefined;
let animation: number | undefined;
let sessionTimer: ReturnType<typeof setTimeout> | undefined;
let generation = 0;
let opening = false;
let permissionPending = false;
let closing: Promise<void> | undefined;
let playback: AbortController | undefined;
let cameraReady = false;
let workerReady = false;
let safeCode = "STOPPED";
let submitted = 0, completed = 0, dropped = 0;
let dimensions = "0 x 0";
function showDiagnostics(): void {
  if (pump) { submitted = pump.submitted; completed = pump.processed; dropped = pump.dropped; }
  diagnostics.textContent = [
    "Safe status: " + safeCode,
    "Camera stream acquired: " + cameraReady,
    "Video dimensions (last observed): " + dimensions,
    "Video readyState: " + video.readyState + "; paused: " + video.paused,
    "Worker ready: " + workerReady,
    "MediaPipe initialized: " + workerReady,
    "Submitted frames: " + submitted,
    "Completed inference results: " + completed,
    "Dropped frames: " + dropped,
  ].join("\n"); // fixed codes and counters only; no media or SDK objects
}
// Observe readiness events as well as play(): a stream assignment is not a frame.
function playReady(signal: AbortSignal): Promise<void> {
  return new Promise((resolve, reject) => {
    let played = false;
    const events = ["loadedmetadata", "loadeddata", "canplay", "playing", "resize"];
    const cleanup = () => {
      clearTimeout(timer);
      events.forEach(name => video.removeEventListener(name, check));
      video.removeEventListener("error", fail);
      signal.removeEventListener("abort", fail);
    };
    const fail = () => { cleanup(); reject(new Error("VIDEO_PLAYBACK_FAILED")); };
    const check = () => {
      if (played && !video.paused && video.readyState >= 2 && video.videoWidth > 0 && video.videoHeight > 0) {
        cleanup(); resolve();
      }
    };
    const timer = setTimeout(fail, 10_000);
    events.forEach(name => video.addEventListener(name, check));
    video.addEventListener("error", fail);
    signal.addEventListener("abort", fail, { once: true });
    if (signal.aborted) { fail(); return; }
    try { void video.play().then(() => { played = true; check(); }, fail); }
    catch { fail(); }
  });
}
function clearOverlay(): void {
  overlay.getContext("2d")?.clearRect(0, 0, overlay.width, overlay.height);
}
async function stop(message = "Stopped. Camera tracks closed."): Promise<void> {
  generation++;
  opening = false;
  if (animation !== undefined) cancelAnimationFrame(animation);
  animation = undefined;
  if (sessionTimer !== undefined) clearTimeout(sessionTimer);
  sessionTimer = undefined;
  showDiagnostics(); // preserve final counts before releasing the pump
  playback?.abort();
  playback = undefined;
  pump?.stop();
  pump = undefined;
  camera.stop();
  video.pause();
  video.srcObject = null;
  cameraReady = false;
  workerReady = false;
  clearOverlay();
  status.textContent = message;
  showDiagnostics();
  startButton.disabled = true;
  stopButton.disabled = true;
  const current = adapter;
  adapter = undefined;
  const shutdown = current?.stop() ?? closing ?? Promise.resolve();
  closing = shutdown;
  await shutdown;
  if (closing === shutdown) { closing = undefined; startButton.disabled = permissionPending; }
}
function accept(output: HandResult): void {
  safeCode = output.status === "SUCCESS" ? "RUNNING" : output.status + ":" + output.reason;
  if (output.status === "INITIALIZATION_FAILURE") {
    safeCode = output.reason === "ASSET" ? "ASSET_LOAD_FAILED" : "MEDIAPIPE_INITIALIZATION_FAILED";
  } else if (output.reason === "WORKER") safeCode = "WORKER_TERMINATED";
  else if (output.reason === "INFERENCE") safeCode = "INFERENCE_FAILED";
  showDiagnostics();
  if (output.status !== "SUCCESS") { void stop(safeCode); return; }
  clearOverlay();
  const context = overlay.getContext("2d");
  if (!context) { safeCode = "OVERLAY_UNAVAILABLE"; void stop(safeCode); return; }
  context.fillStyle = "#34d399";
  for (const hand of output.hands) for (const point of hand.landmarks) {
    context.beginPath();
    context.arc(point.x * overlay.width, point.y * overlay.height, 4, 0, 2 * Math.PI);
    context.fill();
  }
  status.textContent = output.hands.length === 0 ? "Running — no hand detected (success)." : "Running — 21 landmarks, local only.";
}
async function start(): Promise<void> {
  if (opening || permissionPending || adapter || closing) return;
  opening = true;
  const session = ++generation;
  startButton.disabled = true;
  stopButton.disabled = false;
  cameraReady = workerReady = false;
  submitted = completed = dropped = 0;
  dimensions = "0 x 0";
  safeCode = "WORKER_INITIALIZING";
  showDiagnostics();
  if (!preflight().supported) { safeCode = "UNSUPPORTED_BROWSER_APIS"; await stop(safeCode); return; }
  const current = new WorkerHandAdapter();
  adapter = current;
  status.textContent = "Initializing verified local assets…";
  let initialized: HandResult;
  try { initialized = await current.initialize(DEFAULT_CONFIG); }
  catch {
    if (session === generation) { safeCode = "WORKER_INITIALIZATION_FAILED"; await stop(safeCode); }
    return;
  }
  if (session !== generation) return;
  if (initialized.status !== "SUCCESS") { accept(initialized); return; }
  workerReady = true;
  safeCode = "CAMERA_PERMISSION_PENDING";
  showDiagnostics();
  status.textContent = "Allow camera access to continue.";
  let stage: "camera" | "playback" | "capture" = "camera";
  try {
    permissionPending = true;
    const stream = await camera.acquire(() => navigator.mediaDevices.getUserMedia({
      audio: false, video: { width: { ideal: 640, max: 640 }, height: { ideal: 480, max: 480 } },
    })).finally(() => {
      permissionPending = false;
      if (!adapter && !closing) startButton.disabled = false;
    });
    if (!stream || session !== generation) return;
    sessionTimer = setTimeout(() => { safeCode = "SESSION_DEADLINE"; void stop("Session limit reached (60 seconds). Press Start Camera to restart."); }, DEFAULT_CONFIG.sessionLimitMs);
    stream.getVideoTracks().forEach(track => track.addEventListener("ended", () => {
      if (session === generation) { safeCode = "CAMERA_STREAM_FAILED"; void stop(safeCode); }
    }, { once: true }));
    video.srcObject = stream;
    cameraReady = true;
    stage = "playback";
    safeCode = "VIDEO_STARTING";
    showDiagnostics();
    playback = new AbortController();
    await playReady(playback.signal);
    playback = undefined;
    if (session !== generation) return;
    if (video.videoWidth < 1 || video.videoWidth > 640 || video.videoHeight < 1 || video.videoHeight > 480) {
      safeCode = "INVALID_FRAME_DIMENSIONS"; await stop(safeCode); return;
    }
    stage = "capture";
    dimensions = video.videoWidth + " x " + video.videoHeight;
    overlay.width = video.videoWidth;
    overlay.height = video.videoHeight;
    pump = new FramePump(current, DEFAULT_CONFIG, async () => {
      if (video.videoWidth < 1 || video.videoWidth > 640 || video.videoHeight < 1 || video.videoHeight > 480) {
        if (session === generation) safeCode = "INVALID_FRAME_DIMENSIONS";
        throw new Error("FRAME");
      }
      try { return await createImageBitmap(video); }
      catch { if (session === generation) safeCode = "FRAME_CAPTURE_FAILED"; throw new Error("FRAME_CAPTURE_FAILED"); }
    }, accept);
    pump.start();
    opening = false;
    let lastVideoTime = -1;
    let lastFrameAt = performance.now();
    const tick = (timestamp: number): void => {
      if (session !== generation || !pump) return;
      animation = requestAnimationFrame(tick);
      showDiagnostics();
      if (video.readyState < 2 || video.paused || video.currentTime === lastVideoTime) {
        if (timestamp - lastFrameAt > 2_000) {
          safeCode = "VIDEO_WAITING_FOR_FRAME";
          status.textContent = "Waiting for a new camera frame.";
          showDiagnostics();
        }
        return;
      }
      lastFrameAt = timestamp;
      // Overlay backing pixels follow the same intrinsic frame dimensions.
      if (overlay.width !== video.videoWidth || overlay.height !== video.videoHeight) {
        overlay.width = video.videoWidth; overlay.height = video.videoHeight;
        dimensions = video.videoWidth + " x " + video.videoHeight;
      }
      lastVideoTime = video.currentTime;
      void pump.tick(timestamp).catch(() => { if (session === generation) { if (safeCode !== "FRAME_CAPTURE_FAILED" && safeCode !== "INVALID_FRAME_DIMENSIONS") safeCode = "FRAME_PROCESSING_FAILED"; void stop(safeCode); } });
    };
    animation = requestAnimationFrame(tick);
    safeCode = "RUNNING";
    showDiagnostics();
    status.textContent = "Running locally.";
  } catch (error: unknown) {
    if (session !== generation) return;
    const denied = error instanceof DOMException && error.name === "NotAllowedError";
    safeCode = stage === "playback" ? "VIDEO_PLAYBACK_FAILED" :
      stage === "camera" ? (denied ? "CAMERA_PERMISSION_DENIED" : "CAMERA_STREAM_FAILED") : "FRAME_CAPTURE_FAILED";
    await stop(safeCode);
  }
}
startButton.addEventListener("click", () => { void start(); });
stopButton.addEventListener("click", () => { safeCode = "STOPPED"; void stop(); });
window.addEventListener("pagehide", () => { safeCode = "STOPPED"; void stop(); });
document.addEventListener("visibilitychange", () => {
  if (document.hidden) { safeCode = "PAGE_HIDDEN"; void stop("Stopped while page is hidden. Press Start Camera to restart."); }
});

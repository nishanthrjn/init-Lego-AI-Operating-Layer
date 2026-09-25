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
  pump?.stop();
  pump = undefined;
  camera.stop();
  video.pause();
  video.srcObject = null;
  clearOverlay();
  status.textContent = message;
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
  diagnostics.textContent = [
    "Status: " + output.status + " / " + output.reason,
    "Implementation: " + output.attribution.implementation,
    "Asset: " + output.attribution.asset,
    "SHA-256: " + output.attribution.digest,
    "Backend: " + output.attribution.backend,
    "Duration ms: " + output.durationMs.toFixed(1),
    "Frames processed: " + (pump?.processed ?? 0),
    "Frames dropped: " + (pump?.dropped ?? 0),
  ].join("\n"); // no landmarks, frames, SDK values or arbitrary errors
  if (output.status !== "SUCCESS") { void stop(output.status + ": " + output.reason); return; }
  clearOverlay();
  const context = overlay.getContext("2d");
  if (!context) return;
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
  diagnostics.textContent = "";
  if (!preflight().supported) { await stop("UNSUPPORTED: required browser APIs unavailable."); return; }
  const current = new WorkerHandAdapter();
  adapter = current;
  status.textContent = "Initializing verified local assets…";
  const initialized = await current.initialize(DEFAULT_CONFIG);
  if (session !== generation) return;
  if (initialized.status !== "SUCCESS") { accept(initialized); return; }
  diagnostics.textContent = "Initialization ms: " + initialized.durationMs.toFixed(1);
  status.textContent = "Allow camera access to continue.";
  try {
    permissionPending = true;
    const stream = await camera.acquire(() => navigator.mediaDevices.getUserMedia({
      audio: false, video: { width: { ideal: 640, max: 640 }, height: { ideal: 480, max: 480 } },
    })).finally(() => {
      permissionPending = false;
      if (!adapter && !closing) startButton.disabled = false;
    });
    if (!stream || session !== generation) return;
    sessionTimer = setTimeout(() => { void stop("DEADLINE: session limit reached."); }, DEFAULT_CONFIG.sessionLimitMs);
    stream.getVideoTracks().forEach(track => track.addEventListener("ended", () => {
      if (session === generation) void stop("Camera unavailable. Session stopped.");
    }, { once: true }));
    video.srcObject = stream;
    await video.play();
    if (session !== generation) return;
    if (video.videoWidth < 1 || video.videoWidth > 640 || video.videoHeight < 1 || video.videoHeight > 480) {
      await stop("INVALID_INPUT: camera dimensions exceed 640×480."); return;
    }
    overlay.width = video.videoWidth;
    overlay.height = video.videoHeight;
    pump = new FramePump(current, DEFAULT_CONFIG, () => {
      if (video.videoWidth < 1 || video.videoWidth > 640 || video.videoHeight < 1 || video.videoHeight > 480) {
        return Promise.reject(new Error("FRAME"));
      }
      return createImageBitmap(video);
    }, accept);
    pump.start();
    opening = false;
    let lastVideoTime = -1;
    const tick = (timestamp: number): void => {
      if (session !== generation || !pump) return;
      animation = requestAnimationFrame(tick);
      if (video.currentTime === lastVideoTime) return;
      lastVideoTime = video.currentTime;
      void pump.tick(timestamp).catch(() => { if (session === generation) void stop("EXECUTION_FAILURE: frame processing."); });
    };
    animation = requestAnimationFrame(tick);
    status.textContent = "Running locally.";
  } catch (error: unknown) {
    if (session !== generation) return;
    const denied = error instanceof DOMException && error.name === "NotAllowedError";
    await stop(denied ? "Camera permission denied. Nothing was uploaded." : "Camera unavailable. Check permissions and device.");
  }
}
startButton.addEventListener("click", () => { void start(); });
stopButton.addEventListener("click", () => { void stop(); });
window.addEventListener("pagehide", () => { void stop(); });
document.addEventListener("visibilitychange", () => {
  if (document.hidden) void stop("Stopped while page is hidden.");
});

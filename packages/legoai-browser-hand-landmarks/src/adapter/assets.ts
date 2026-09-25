import { ASSETS } from "./approved.js";
// Only this initialization module fetches. No input supplies a location.
export async function verifyAsset(bytes: ArrayBuffer, descriptor: typeof ASSETS[number]): Promise<void> {
  if (bytes.byteLength !== descriptor.bytes) throw new Error("ASSET_SIZE");
  const digest = await crypto.subtle.digest("SHA-256", bytes);
  const hex = Array.from(new Uint8Array(digest), b => b.toString(16).padStart(2, "0")).join("");
  if (hex !== descriptor.sha256) throw new Error("ASSET_DIGEST");
}
export async function loadApprovedAssets(origin: string, fetcher: typeof fetch = fetch): Promise<readonly ArrayBuffer[]> {
  const loaded: ArrayBuffer[] = [];
  for (const descriptor of ASSETS) {
    const url = new URL(descriptor.path, origin);
    if (url.origin !== origin || !["http:", "https:"].includes(url.protocol)) throw new Error("ASSET_ORIGIN");
    const response = await fetcher(url, { credentials: "omit", redirect: "error", cache: "no-store" });
    if (!response.ok || !response.body) throw new Error("ASSET_FETCH");
    const length = response.headers.get("content-length");
    if (length !== null && Number(length) !== descriptor.bytes) throw new Error("ASSET_SIZE");
    const reader = response.body.getReader();
    const bytes = new ArrayBuffer(descriptor.bytes); // bounded by build-owned manifest
    const output = new Uint8Array(bytes);
    let used = 0;
    try {
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        if (used + value.byteLength > output.byteLength) throw new Error("ASSET_SIZE");
        output.set(value, used);
        used += value.byteLength;
      }
      if (used !== output.byteLength) throw new Error("ASSET_SIZE");
    } finally {
      await reader.cancel();
      reader.releaseLock();
    }
    await verifyAsset(bytes, descriptor);
    loaded.push(bytes);
  }
  return Object.freeze(loaded);
}

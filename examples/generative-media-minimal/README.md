# Minimal generative-media consumer

`app.py` depends only on `TextToImagePort` and a configuration file. It never
branches on provider, endpoint, API family, credentials or hardware. To switch
providers, change `--config`; the source stays identical.

```powershell
# Local OSS ComfyUI (auto-detects the legacy API family)
uv run --locked python examples/generative-media-minimal/app.py --config examples/generative-media-minimal/configs/comfy-local.toml --prompt "a red ceramic mug on a wooden table" --seed 42 --output .\comfyui-proof\minimal-local.png

# Comfy Cloud (Comfy API v2). Consumes credits. The key comes from the environment only.
$env:COMFY_API_KEY = "<your key>"   # never written to any file
uv run --locked python examples/generative-media-minimal/app.py --config examples/generative-media-minimal/configs/comfy-cloud.toml --prompt "a red ceramic mug on a wooden table" --seed 42 --output .\comfyui-proof\minimal-cloud.png
```

`configs/comfy-v2-selfhosted.toml` targets a self-hosted ComfyUI behind
`comfy-api-proxy` (v2 beta) on `127.0.0.1:8189`.

Before any generation, check reachability read-only:

```powershell
uv run --locked python examples/comfyui-text-to-image/probe_provider.py --config examples/generative-media-minimal/configs/comfy-local.toml
```

The destination must not exist. Nothing is retried automatically.

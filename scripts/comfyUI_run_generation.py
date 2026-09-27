import subprocess
import os

# Define your generation variables
workflow_path = r".\comfyui-proof\workflow.json"
checkpoint = "v1-5-pruned-emaonly.safetensors"
sha256 = "APPROVED_SHA256"
prompt = "a cute white bunny sleeping inside a teacup, flowers around it, pastel colors, cozy, whimsical, soft lighting, highly detailed, 8k, cinematic lighting, photorealistic, trending on artstation"
seed = "42"
output_path = r".\comfyui-proof\mug.png"

# Build the command as a list of strings
command = [
    "uv", "run", "examples/comfyui-text-to-image/generate.py",
    "--workflow", workflow_path,
    "--sha256", sha256,
    "--checkpoint", checkpoint,
    "--prompt", prompt,
    "--seed", seed,
    "--output", output_path
]

print(f"Generating image with seed {seed}...")

# Execute the command
try:
    result = subprocess.run(command, check=True, text=True, capture_output=True)
    print("Generation successful!")
    print(result.stdout)
except subprocess.CalledProcessError as e:
    print("Error during generation:")
    print(e.stderr)
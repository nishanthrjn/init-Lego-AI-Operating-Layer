"""Static experimental packaging only; never submission qualification."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import sys
import zipfile

STATE = "EXPERIMENTAL_UNQUALIFIED"
MEMBERS = ("agent.yaml", "eval_config.yaml", "configs/sampling.yaml", "prompts/system.md")
HERE = Path(__file__).resolve().parent


def digest(blob):
    return hashlib.sha256(blob).hexdigest()


def static_files(candidate):
    if candidate not in {"p1b", "p1c", "p2"}:
        raise ValueError("unsupported experiment")
    area = HERE.parent / "candidates"
    pins = json.loads((HERE / "experimental-pins.json").read_bytes())
    data = {}
    for name in ("p1", "p1b", "p1c", "p2"):
        directory = area / name
        files = {p.relative_to(directory).as_posix(): p.read_bytes() for p in directory.rglob("*") if p.is_file()}
        if set(files) != set(MEMBERS) or any(digest(files[k]) != pins[name][k] for k in MEMBERS):
            raise ValueError("static candidate bytes changed: " + name)
        data[name] = files
    if {k for k in MEMBERS if data["p1"][k] != data["p1b"][k]} != {"prompts/system.md"}:
        raise ValueError("P1b scope mismatch")
    if {k for k in MEMBERS if data["p1b"][k] != data["p1c"][k]} != {"configs/sampling.yaml"}:
        raise ValueError("P1c scope mismatch")
    if {k for k in MEMBERS if data["p1b"][k] != data["p2"][k]} != {"agent.yaml", "prompts/system.md"}:
        raise ValueError("P2 scope mismatch")
    added = b"  - search_similar_code\n  - get_code_neighbors\n  - get_code_subgraph\n"
    if data["p2"]["agent.yaml"].replace(added, b"") != data["p1b"]["agent.yaml"]:
        raise ValueError("P2 may only add the three graph tools")
    return data[candidate]


def verify(config):
    if config.get("experimental_authorized") is not True or config.get("subset") != "dev-16v":
        raise ValueError("explicit dev-16v experimental approval required")
    manifest_bytes = Path(config["manifest"]).read_bytes()
    if digest(manifest_bytes) != config["manifest_sha256"]:
        raise ValueError("experimental manifest hash mismatch")
    manifest = json.loads(manifest_bytes)
    blob = Path(config["package"]).read_bytes()
    if (manifest["state"] != STATE or manifest["candidate"] != config["candidate"]
            or digest(blob) != manifest["zip_sha256"] or digest(blob) != config["zip_sha256"]
            or len(blob) != manifest["zip_size"]):
        raise ValueError("experimental package identity mismatch")
    pins = json.loads((HERE / "experimental-pins.json").read_bytes())
    expected = pins.get(config["candidate"])
    if config["candidate"] not in {"p1b", "p1c", "p2"}:
        raise ValueError("unsupported experiment")
    with zipfile.ZipFile(io.BytesIO(blob)) as archive:
        if sorted(archive.namelist()) != sorted(MEMBERS):
            raise ValueError("experimental archive members mismatch")
        if any(digest(archive.read(name)) != expected[name] for name in MEMBERS):
            raise ValueError("experimental archive bytes mismatch")
    return manifest


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("candidate", choices=("p1b", "p1c", "p2"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    if output.is_relative_to(HERE.parents[2]) or any((p / ".git").exists() for p in output.parents):
        raise ValueError("experimental packages must remain outside repository")
    data = static_files(args.candidate)
    sys.path.insert(0, str(HERE.parent))
    from portable_m2 import zip_bytes, inspect_zip
    blob = zip_bytes(data)
    inspect_zip(blob, data)
    output.mkdir(parents=True, exist_ok=False)
    (output / "submission.zip.bin").write_bytes(blob)
    manifest = {"state": STATE, "candidate": args.candidate, "zip_sha256": digest(blob),
                "zip_size": len(blob), "files": {k: digest(v) for k, v in data.items()},
                "submission_authorized": False}
    raw = (json.dumps(manifest, sort_keys=True, indent=2) + "\n").encode()
    (output / "manifest.json").write_bytes(raw)
    print(json.dumps({**manifest, "manifest_sha256": digest(raw)}))


if __name__ == "__main__":
    main()

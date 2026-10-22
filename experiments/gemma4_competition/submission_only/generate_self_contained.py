"""Offline generator; no compilation, model execution or Kaggle operations."""
import argparse
import ast
import base64
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def load_pins(candidate):
    notebook = json.loads((HERE / "first_submission.ipynb").read_bytes())
    source = "".join(next(c for c in notebook["cells"] if c["id"] == "copy-helper")["source"])
    values = {}
    def literal(node):
        if isinstance(node, ast.Name):
            return values[node.id]
        if isinstance(node, ast.Dict):
            return {literal(k): literal(v) for k, v in zip(node.keys, node.values)}
        return ast.literal_eval(node)
    for node in ast.parse(source).body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            values[node.targets[0].id] = literal(node.value)
    pins = dict(values["CANDIDATE_PINS"][candidate])
    # M2 is the original closed baseline: its legacy pins predate the flags.
    if candidate == "m2":
        pins.setdefault("reconciled", True)
        pins.setdefault("m2_result_understood", True)
    return pins


def build_notebook(candidate, pins, raw_manifest, payload):
    if pins.get("reconciled") is not True or pins.get("m2_result_understood") is not True:
        raise ValueError("Reconciled candidate and understood M2 result required")
    for key in ("manifest_sha256", "zip_sha256", "receipt_sha256"):
        value = pins.get(key)
        if not isinstance(value, str) or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
            raise ValueError("Missing candidate hash pin: " + key)
    if type(pins.get("zip_size")) is not int or pins["zip_size"] <= 0 or not pins.get("authorization"):
        raise ValueError("Missing size or authorization pin")
    if hashlib.sha256(raw_manifest).hexdigest() != pins["manifest_sha256"]:
        raise ValueError("Manifest SHA256 mismatch")
    manifest = json.loads(raw_manifest)
    if (manifest.get("state") != "PORTABLE_COMPILE_AND_PACKAGE_PASS"
            or manifest.get("local_receipt_sha256") != pins["receipt_sha256"]
            or manifest.get("zip_sha256") != pins["zip_sha256"]
            or manifest.get("zip_size") != pins["zip_size"]):
        raise ValueError("Manifest identity mismatch")
    if len(payload) != pins["zip_size"] or hashlib.sha256(payload).hexdigest() != pins["zip_sha256"]:
        raise ValueError("Package SHA256/size mismatch")
    helper = (HERE / "embedded_payload.py").read_text(encoding="utf-8")
    invocation = ("PINS = " + repr(pins) + "\nPAYLOAD_BASE64 = " + repr(base64.b64encode(payload).decode("ascii"))
                  + '\nAUTHORIZATION = ""  # Set to the exact phrase in PINS before saving the version.\n'
                  + 'report = materialize(PAYLOAD_BASE64, PINS, AUTHORIZATION, Path("/kaggle/working/submission.zip"))\n')
    def code(identity, source):
        return {"cell_type": "code", "id": identity, "metadata": {}, "source": source.splitlines(keepends=True),
                "execution_count": None, "outputs": []}
    return {"nbformat": 4, "nbformat_minor": 5,
            "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"}},
            "cells": [{"cell_type": "markdown", "id": "scope", "metadata": {}, "source": [
                "# Self-contained " + candidate.upper() + " package preparation\n",
                "Set Accelerator None; Internet Off. No input datasets required. Only submission.zip is written.\n",
                "Set AUTHORIZATION in the final cell and save that version for reruns. Package preparation does not authorize submission.\n",
                "Expected authorization: `" + pins["authorization"] + "`.\n"]},
                code("payload-helper", helper), code("materialize", invocation)]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", required=True)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--package", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    pins = load_pins(args.candidate)
    notebook = build_notebook(args.candidate, pins, args.manifest.read_bytes(), args.package.read_bytes())
    with args.output.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(notebook, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"notebook": str(args.output), "candidate": args.candidate, **pins}, sort_keys=True))


if __name__ == "__main__":
    main()

"""Standard-library source embedded verbatim into generated submission notebooks."""
import base64
import hashlib
import json
from pathlib import Path


def materialize(payload_base64, pins, authorization, output):
    if authorization != pins["authorization"]:
        raise ValueError("Exact maintainer authorization required")
    payload = base64.b64decode(payload_base64, validate=True)
    def matches(data):
        return len(data) == pins["zip_size"] and hashlib.sha256(data).hexdigest() == pins["zip_sha256"]
    if not matches(payload):
        raise ValueError("Embedded package SHA256/size mismatch")
    # Verify payload before reading or replacing output. Never follow a symlink.
    if output.is_symlink():
        raise ValueError("Output must not be a symlink")
    replaced_hash = None
    state = "CREATED"
    if output.exists():
        previous = output.read_bytes()
        if matches(previous):
            state = "ALREADY_PRESENT_IDENTICAL"
        else:
            replaced_hash = hashlib.sha256(previous).hexdigest()
            # Only the designated output is written; no temporary or sidecar files.
            with output.open("wb") as stream:
                stream.write(payload)
            state = "REPLACED_DIFFERENT"
    else:
        with output.open("xb") as stream:
            stream.write(payload)
    if not matches(output.read_bytes()):
        raise ValueError("Output SHA256/size mismatch; do not submit")
    report = {"state": state, "output": str(output), "replaced_sha256": replaced_hash,
              "zip_sha256": pins["zip_sha256"], "zip_size": pins["zip_size"],
              "manifest_sha256": pins["manifest_sha256"], "receipt_sha256": pins["receipt_sha256"]}
    print(json.dumps(report, indent=2, sort_keys=True))
    return report

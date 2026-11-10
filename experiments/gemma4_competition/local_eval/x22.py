"""Read the confirmed external ZIP unchanged; private evaluation only."""
import hashlib
import io
from pathlib import Path
import zipfile

SOURCE_SHA256 = "80f4b123502f36dfd62745ca6aee9a9cd26f681338e52f75c8b3c302d6100767"
SOURCE_SIZE = 3031
REUSE_SCOPE = "PRIVATE_LOCAL_EVALUATION_ONLY"


def verify_source_zip(blob, pins):
    if len(blob) != SOURCE_SIZE or hashlib.sha256(blob).hexdigest() != SOURCE_SHA256:
        raise ValueError("X22 source ZIP identity mismatch; repacking is forbidden")
    with zipfile.ZipFile(io.BytesIO(blob)) as archive:
        if sorted(archive.namelist()) != sorted(pins):
            raise ValueError("X22 requires exactly the four pinned members")
        for name, expected in pins.items():
            if hashlib.sha256(archive.read(name)).hexdigest() != expected:
                raise ValueError("X22 source member mismatch: " + name)
    return blob


def read_source_archive(path, pins):
    with zipfile.ZipFile(Path(path)) as outer:
        entries = [e for e in outer.infolist() if not e.is_dir()]
        if len(entries) != 1 or entries[0].filename != "submission.zip":
            raise ValueError("X22 outer archive must contain only submission.zip")
        if entries[0].file_size != SOURCE_SIZE:
            raise ValueError("X22 nested ZIP size mismatch")
        blob = outer.read(entries[0])
    return verify_source_zip(blob, pins)

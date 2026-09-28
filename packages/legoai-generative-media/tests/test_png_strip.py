"""Structural PNG stripping (ADR-020 §3): critical chunks only, pixels untouched."""

import hashlib
import zlib

import pytest
from media_support import chunks_of, make_png

from legoai_generative_media.png import strip_png, validate_png
from legoai_generative_media.values import ImageInput

SECRET = b"Alice Example 51.5007N -0.1246W serial-XYZ"
ANCILLARY = {
    b"tEXt": b"Author\0" + SECRET,
    b"zTXt": b"Comment\0\0" + zlib.compress(SECRET),
    b"iTXt": b"Description\0\0\0en\0\0" + SECRET,
    b"eXIf": b"MM\0*" + SECRET,
    b"tIME": b"\x07\xea\x09\x1c\x0c\x00\x00",
    b"iCCP": b"Profile " + SECRET[:10] + b"\0\0" + zlib.compress(SECRET),
    b"sRGB": b"\0",
    b"gAMA": b"\0\0\xb1\x8f",
    b"cHRM": b"\0" * 32,
    b"pHYs": b"\0\0\x0b\x13\0\0\x0b\x13\x01",
    b"prVt": SECRET,  # private ancillary chunk
}


@pytest.mark.parametrize("kind", sorted(ANCILLARY))
def test_each_ancillary_chunk_removed(kind: bytes) -> None:
    data = make_png(before=((kind, ANCILLARY[kind]),))
    stripped, _, _ = strip_png(data)
    assert kind not in [k for k, _ in chunks_of(stripped)]
    assert SECRET not in stripped and SECRET[:10] not in stripped


def test_only_critical_structure_kept_byte_for_byte() -> None:
    before = tuple(ANCILLARY.items())
    after = ((b"tEXt", b"Late\0" + SECRET),)
    data = make_png(120, 80, color=6, before=before, after=after, idat_parts=3)
    stripped, width, height = strip_png(data)
    kinds = [k for k, _ in chunks_of(stripped)]
    assert kinds == [b"IHDR", b"IDAT", b"IDAT", b"IDAT", b"IEND"]
    original = [c for k, c in chunks_of(data) if k in (b"IHDR", b"IDAT", b"IEND")]
    assert [c for _, c in chunks_of(stripped)] == original  # Exact bytes, same order.
    assert stripped[:8] == data[:8]
    assert (width, height) == (120, 80)


def test_optional_truecolour_palette_dropped() -> None:
    stripped, _, _ = strip_png(make_png(before=((b"PLTE", b"\x10\x20\x30" * 4),)))
    assert b"PLTE" not in [k for k, _ in chunks_of(stripped)]


def test_stripped_output_reparses_and_is_idempotent() -> None:
    data = make_png(200, 300, before=tuple(ANCILLARY.items()))
    stripped, width, height = strip_png(data)
    assert strip_png(stripped) == (stripped, width, height)
    # Independent check with the existing output validator.
    validate_png(stripped, width, height)


def test_image_input_holds_only_stripped_bytes() -> None:
    data = make_png(before=((b"tEXt", b"Author\0" + SECRET),))
    image = ImageInput(data)
    assert image.content == strip_png(data)[0]
    assert SECRET not in image.content
    assert image.sha256 == hashlib.sha256(image.content).hexdigest()
    assert image.sha256 != hashlib.sha256(data).hexdigest()
    assert "Alice" not in repr(image)


def test_metadata_in_any_position_removed() -> None:
    data = make_png(
        before=((b"tEXt", b"a\0" + SECRET),),
        after=((b"zTXt", b"b\0\0" + zlib.compress(SECRET)),),
    )
    assert SECRET not in strip_png(data)[0]

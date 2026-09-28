"""ImageInput contract (ADR-020): bounded, exact, PNG-only, never echoed."""

import dataclasses
import struct

import pytest
from media_support import chunk, make_png

from legoai_generative_media.png import MAX_INPUT_BYTES, strip_png
from legoai_generative_media.values import ImageInput

SECRET = b"Alice Example, 51.5007N -0.1246W, Pixel 9"


@pytest.mark.parametrize("color", [2, 6])
def test_valid_truecolour_inputs(color: int) -> None:
    image = ImageInput(make_png(96, 128, color=color))
    assert (image.width, image.height) == (96, 128)
    assert image.byte_length == len(image.content)


def test_contract_has_no_locator_or_provider_fields() -> None:
    assert [f.name for f in dataclasses.fields(ImageInput)] == [
        "content",
        "width",
        "height",
    ]


def test_repr_and_errors_never_expose_bytes() -> None:
    data = make_png(before=((b"tEXt", b"Author\0" + SECRET),))
    image = ImageInput(data)
    text = repr(image) + str({image}) + repr([image])
    assert "Alice" not in text and "\\x89PNG" not in text and "IDAT" not in text
    broken = data[:-5]
    with pytest.raises(ValueError) as caught:
        ImageInput(broken)
    assert "Alice" not in str(caught.value) and "PNG" in str(caught.value)


def test_equality_and_hash_use_stripped_content() -> None:
    plain = ImageInput(make_png())
    tagged = ImageInput(make_png(before=((b"tEXt", b"k\0" + SECRET),)))
    assert plain == tagged and hash(plain) == hash(tagged)
    assert plain.sha256 == tagged.sha256


@pytest.mark.parametrize(
    "value", [bytearray(make_png()), memoryview(make_png()), "png"]
)
def test_only_owned_immutable_bytes(value: object) -> None:
    with pytest.raises(TypeError):
        ImageInput(value)  # type: ignore[arg-type]


def ihdr(width: int = 64, height: int = 64, depth: int = 8, color: int = 2) -> bytes:
    return chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, depth, color, 0, 0, 0))


def corrupt_crc(data: bytes) -> bytes:
    # Flip one byte inside the first IDAT payload; its CRC no longer matches.
    index = data.index(b"IDAT") + 6
    return data[:index] + bytes([data[index] ^ 0xFF]) + data[index + 1 :]


INVALID = {
    "wrong signature": b"\x89PNX\r\n\x1a\n" + make_png()[8:],
    "truncated": make_png()[:40],
    "empty": b"",
    "bad IHDR length": b"\x89PNG\r\n\x1a\n"
    + chunk(b"IHDR", b"\0" * 12)
    + make_png()[33:],
    "IHDR not first": b"\x89PNG\r\n\x1a\n" + chunk(b"tEXt", b"a\0b") + make_png()[8:],
    "invalid CRC": corrupt_crc(make_png()),
    "unknown critical chunk": make_png(before=((b"CrIt", b"x"),)),
    "invalid chunk type": make_png(before=((b"ab1d", b"x"),)),
    "trailing bytes": make_png(trailing=b"\0"),
    "bytes after IEND": make_png(trailing=chunk(b"tEXt", b"a\0b")),
    "interlaced": make_png(interlace=1),
    "16-bit": make_png(depth=16),
    "invalid colour type": make_png(color=5),
    "palette colour type": make_png(color=3),
    "greyscale": make_png(color=0),
    "PLTE after IDAT": make_png(after=((b"PLTE", b"\0" * 3),)),
    "PLTE bad length": make_png(before=((b"PLTE", b"\0" * 4),)),
    "duplicate PLTE": make_png(before=((b"PLTE", b"\0" * 3), (b"PLTE", b"\0" * 3))),
    "duplicate IHDR": make_png(before=((b"IHDR", ihdr()[8:-4]),)),
    "too wide": make_png(2049, 64),
    "too small": make_png(63, 64),
    "non-consecutive IDAT": make_png(after=((b"tEXt", b"a\0b"), (b"IDAT", b"x"))),
    "missing IEND": make_png()[:-12],
    "no IDAT": b"\x89PNG\r\n\x1a\n" + ihdr() + chunk(b"IEND", b""),
    "non-empty IEND": make_png()[:-12] + chunk(b"IEND", b"x"),
    "transparency": make_png(before=((b"tRNS", b"\0\0\0\0\0\0"),)),
}


@pytest.mark.parametrize("case", sorted(INVALID))
def test_invalid_inputs_rejected(case: str) -> None:
    with pytest.raises(ValueError):
        ImageInput(INVALID[case])


def test_oversized_bytes_rejected_before_parsing() -> None:
    data = make_png() + b"\0" * (MAX_INPUT_BYTES + 1 - len(make_png()))
    assert len(data) == MAX_INPUT_BYTES + 1
    with pytest.raises(ValueError, match="oversized"):
        strip_png(data)


def test_bounds_are_inclusive() -> None:
    for width, height in ((64, 64), (2048, 64), (64, 2048)):
        assert ImageInput(make_png(width, height)).width == width

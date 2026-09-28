"""Bounded PNG structure/CRC validation; no pixel decoding or allocation."""

import struct
import zlib

MAX_IMAGE_BYTES = 16 * 1024 * 1024


def validate_png(data: bytes, width: int, height: int) -> None:
    if not 1 <= width <= 1024 or not 1 <= height <= 1024:
        raise ValueError("dimensions out of bounds")
    if len(data) > MAX_IMAGE_BYTES or data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("invalid PNG")
    offset, count = 8, 0
    seen_header = seen_data = ended_data = False
    while offset + 12 <= len(data):
        size = struct.unpack_from(">I", data, offset)[0]
        kind = data[offset + 4 : offset + 8]
        end = offset + 12 + size
        count += 1
        if end > len(data) or count > 4096:
            raise ValueError("invalid PNG chunk")
        payload = data[offset + 8 : offset + 8 + size]
        crc = struct.unpack_from(">I", data, end - 4)[0]
        if zlib.crc32(kind + payload) & 0xFFFFFFFF != crc:
            raise ValueError("invalid PNG CRC")
        if not seen_header:
            if kind != b"IHDR" or size != 13:
                raise ValueError("missing PNG header")
            w, h, depth, color, compression, filtering, interlace = struct.unpack(
                ">IIBBBBB", payload
            )
            if (w, h) != (width, height) or depth != 8 or color not in (2, 6):
                raise ValueError("unexpected PNG profile")
            if (compression, filtering, interlace) != (0, 0, 0):
                raise ValueError("unsupported PNG profile")
            seen_header = True
        elif kind == b"IHDR":
            raise ValueError("duplicate PNG header")
        elif kind == b"IDAT":
            if ended_data or size == 0:
                raise ValueError("invalid PNG data sequence")
            seen_data = True
        elif kind == b"IEND":
            if size != 0 or not seen_data or end != len(data):
                raise ValueError("invalid PNG end")
            return
        else:
            if seen_data:
                ended_data = True
            if kind not in (b"tEXt", b"iTXt", b"zTXt", b"sRGB", b"gAMA", b"pHYs"):
                raise ValueError("unsupported PNG chunk")
        offset = end
    raise ValueError("incomplete PNG")


# Privacy-sensitive input PNGs (ADR-020 §3): v1 limits, no pixel decoding.
MAX_INPUT_BYTES = 16 * 1024 * 1024
MIN_INPUT_SIDE = 64
MAX_INPUT_SIDE = 2048
_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def strip_png(data: bytes) -> tuple[bytes, int, int]:
    """Validate an input PNG exactly and rebuild it from critical chunks only.

    Keeps the signature, IHDR, the consecutive IDAT sequence and IEND,
    byte-for-byte. Every ancillary chunk is dropped. PLTE is dropped too,
    because it is only a suggestion for the accepted truecolour types.
    Anything that cannot be parsed exactly, or whose removal would change
    pixel interpretation (tRNS), is rejected; nothing is ever forwarded
    unstripped. Returns (stripped, width, height).
    """
    if type(data) is not bytes:
        raise TypeError("PNG bytes required")
    if len(data) > MAX_INPUT_BYTES:
        raise ValueError("input PNG oversized")
    if data[:8] != _SIGNATURE:
        raise ValueError("PNG signature required")
    kept = [_SIGNATURE]
    offset, count, width, height = 8, 0, 0, 0
    state = "start"  # start -> header -> data -> after_data
    palette_seen = False
    while True:
        if offset + 12 > len(data):
            raise ValueError("truncated PNG")
        size = struct.unpack_from(">I", data, offset)[0]
        kind = data[offset + 4 : offset + 8]
        end = offset + 12 + size
        count += 1
        if size > 0x7FFFFFFF or end > len(data) or count > 4096:
            raise ValueError("invalid PNG chunk")
        if not all(65 <= b <= 90 or 97 <= b <= 122 for b in kind):
            raise ValueError("invalid PNG chunk type")
        payload = data[offset + 8 : offset + 8 + size]
        if (
            zlib.crc32(kind + payload) & 0xFFFFFFFF
            != struct.unpack_from(">I", data, end - 4)[0]
        ):
            raise ValueError("invalid PNG CRC")
        chunk = data[offset:end]
        critical = not kind[0] & 0x20
        if state == "start":
            if kind != b"IHDR" or size != 13:
                raise ValueError("IHDR must come first")
            width, height, depth, color, compression, filtering, interlace = (
                struct.unpack(">IIBBBBB", payload)
            )
            if not (
                MIN_INPUT_SIDE <= width <= MAX_INPUT_SIDE
                and MIN_INPUT_SIDE <= height <= MAX_INPUT_SIDE
            ):
                raise ValueError("input dimensions out of bounds")
            if depth != 8 or color not in (2, 6):
                raise ValueError("unsupported PNG profile")
            if (compression, filtering, interlace) != (0, 0, 0):
                raise ValueError("unsupported PNG profile")
            kept.append(chunk)
            state = "header"
        elif kind == b"IHDR":
            raise ValueError("duplicate IHDR")
        elif kind == b"PLTE":
            if state != "header" or palette_seen or not 0 < size <= 768 or size % 3:
                raise ValueError("invalid PLTE")
            palette_seen = True  # Optional for truecolour; dropped.
        elif kind == b"IDAT":
            if state == "after_data":
                raise ValueError("non-consecutive IDAT")
            kept.append(chunk)
            state = "data"
        elif kind == b"IEND":
            if state == "header" or size != 0:
                raise ValueError("invalid IEND")
            if end != len(data):
                raise ValueError("bytes after IEND")
            kept.append(chunk)
            return b"".join(kept), width, height
        elif critical:
            raise ValueError("unknown critical chunk")
        else:
            if kind == b"tRNS":
                # Dropping transparency would change how pixels are read.
                raise ValueError("transparency chunk not supported")
            if state == "data":
                state = "after_data"
        offset = end

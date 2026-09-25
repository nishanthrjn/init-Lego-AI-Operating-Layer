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

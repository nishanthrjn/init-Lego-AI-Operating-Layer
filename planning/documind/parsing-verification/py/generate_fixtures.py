"""Design-verification fixture generator for DocumentParsingCapability (Batch 2).

Not production code. Not a test suite. Generates tiny, synthetic, non-private
fixtures used only to characterize pypdf and the DocuMind C# parsers before
the capability's contract is finalized. Run with the isolated verification
venv in this directory (`.venv`), never the legoai-document project venv.
"""

from __future__ import annotations

from pathlib import Path

from pypdf import PdfWriter
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"
FIXTURES.mkdir(exist_ok=True)


def _text_page_pdf(path: Path, pages: list[list[str]]) -> None:
    """Write a PDF where each element of `pages` is a list of text lines for
    that page. An empty list produces a page with no text objects at all
    (a true blank page, not merely whitespace)."""
    c = canvas.Canvas(str(path), pagesize=letter)
    for lines in pages:
        y = 750
        for line in lines:
            c.drawString(72, y, line)
            y -= 18
        c.showPage()
    c.save()


def _image_only_pdf(path: Path) -> None:
    """A syntactically valid PDF whose only content is a rasterized image
    (no text objects at all) -- simulates a scanned/photographed page."""
    from reportlab.lib.utils import ImageReader
    from PIL import Image

    img_path = FIXTURES / "_scratch_raster.png"
    Image.new("RGB", (200, 100), color=(128, 128, 128)).save(img_path)

    c = canvas.Canvas(str(path), pagesize=letter)
    c.drawImage(ImageReader(str(img_path)), 72, 600, width=200, height=100)
    c.showPage()
    c.save()
    img_path.unlink()


def main() -> None:
    # 1-7: plain-text-family fixtures (no PDF library needed)
    (FIXTURES / "01_empty_utf8.txt").write_bytes(b"")
    (FIXTURES / "02_ascii.txt").write_bytes(b"Hello world")
    (FIXTURES / "03_unicode_utf8.txt").write_text(
        "café 日本語 \U0001f600", encoding="utf-8"
    )
    (FIXTURES / "04_multiline.txt").write_bytes(b"line1\nline2\nline3")
    (FIXTURES / "05_leading_trailing_ws.txt").write_bytes(b"  \n  hello  \n  ")
    (FIXTURES / "06_markdown_opaque.md").write_bytes(
        b"# Heading\n\n*emphasis* and a [link](http://example.invalid)\n"
    )
    (FIXTURES / "07_html_opaque.html").write_bytes(
        b"<html><body><p>Hello <b>world</b></p></body></html>"
    )
    (FIXTURES / "15_invalid_utf8.txt").write_bytes(b"\xff\xfe\x00\x80not valid utf-8")

    # 8-11: PDF fixtures via reportlab (text) + pypdf (encryption)
    _text_page_pdf(FIXTURES / "08_one_page_text.pdf", [["Hello world from page one."]])
    _text_page_pdf(
        FIXTURES / "09_multi_page_text.pdf",
        [
            ["Page one line A", "Page one line B"],
            ["Page two line A", "Page two line B"],
            ["Page three only line"],
        ],
    )
    _text_page_pdf(
        FIXTURES / "10_blank_page_middle.pdf",
        [
            ["First page has text."],
            [],  # true blank page: no text objects at all
            ["Third page has text."],
        ],
    )
    _text_page_pdf(
        FIXTURES / "11_unicode_pdf.pdf",
        [["Unicode: café naïve über"]],
    )

    # 12: image-only PDF (no text layer)
    _image_only_pdf(FIXTURES / "12_image_only.pdf")

    # 13: malformed / truncated PDF
    valid = (FIXTURES / "08_one_page_text.pdf").read_bytes()
    (FIXTURES / "13_malformed_truncated.pdf").write_bytes(valid[: len(valid) // 3])
    (FIXTURES / "13b_malformed_garbage.pdf").write_bytes(
        b"%PDF-1.4\nthis is not a real pdf body at all\n%%EOF"
    )

    # 14: encrypted PDF
    writer = PdfWriter()
    writer.append(FIXTURES / "08_one_page_text.pdf")
    writer.encrypt(user_password="secret123", owner_password="owner456")
    with open(FIXTURES / "14_encrypted.pdf", "wb") as f:
        writer.write(f)

    print(f"Fixtures written to {FIXTURES}")
    for p in sorted(FIXTURES.iterdir()):
        print(" ", p.name, p.stat().st_size, "bytes")


if __name__ == "__main__":
    main()

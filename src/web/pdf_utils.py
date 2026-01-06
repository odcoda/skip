#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "pymupdf>=1.24",
# ]
# ///
"""
PDF Utility Functions

Provides PDF-to-image conversion for preview and testing.
Uses PyMuPDF (fitz) for PDF rendering, with fallback to pdf2image.

Usage:
    uv run src/web/pdf_utils.py <pdf_path> [output_dir]
"""

import os
from pathlib import Path
from typing import List, Optional


def get_pdf_page_count(pdf_path: str) -> int:
    """Get the number of pages in a PDF."""
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(pdf_path)
        count = len(doc)
        doc.close()
        return count
    except ImportError:
        try:
            from pdf2image import pdfinfo_from_path
            info = pdfinfo_from_path(pdf_path)
            return info.get("Pages", 0)
        except ImportError:
            # Fallback: try to use pdfinfo command
            import subprocess
            try:
                result = subprocess.run(
                    ["pdfinfo", pdf_path],
                    capture_output=True,
                    text=True
                )
                for line in result.stdout.split('\n'):
                    if line.startswith('Pages:'):
                        return int(line.split(':')[1].strip())
            except:
                pass
    return 0


def convert_pdf_to_images(
    pdf_path: str,
    output_dir: str,
    dpi: int = 150,
    pages: Optional[List[int]] = None,
    format: str = "png"
) -> List[Path]:
    """
    Convert PDF pages to images.

    Args:
        pdf_path: Path to the PDF file
        output_dir: Directory to save images
        dpi: Resolution for rendering (default 150)
        pages: List of page numbers to convert (0-indexed), or None for all
        format: Output format (png, jpg)

    Returns:
        List of paths to generated images
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    generated = []

    # Try PyMuPDF first (faster, no external dependencies)
    try:
        import fitz  # PyMuPDF

        doc = fitz.open(pdf_path)
        total_pages = len(doc)

        if pages is None:
            pages = list(range(total_pages))

        # Scale factor for DPI (fitz uses 72 dpi base)
        zoom = dpi / 72
        mat = fitz.Matrix(zoom, zoom)

        for page_num in pages:
            if 0 <= page_num < total_pages:
                page = doc.load_page(page_num)
                pix = page.get_pixmap(matrix=mat)

                output_path = output_dir / f"page_{page_num:03d}.{format}"
                pix.save(str(output_path))
                generated.append(output_path)

        doc.close()
        return generated

    except ImportError:
        pass

    # Fallback to pdf2image
    try:
        from pdf2image import convert_from_path

        if pages is None:
            images = convert_from_path(pdf_path, dpi=dpi)
            for i, image in enumerate(images):
                output_path = output_dir / f"page_{i:03d}.{format}"
                image.save(str(output_path), format.upper())
                generated.append(output_path)
        else:
            for page_num in pages:
                # pdf2image uses 1-indexed pages
                images = convert_from_path(
                    pdf_path,
                    dpi=dpi,
                    first_page=page_num + 1,
                    last_page=page_num + 1
                )
                if images:
                    output_path = output_dir / f"page_{page_num:03d}.{format}"
                    images[0].save(str(output_path), format.upper())
                    generated.append(output_path)

        return generated

    except ImportError:
        pass

    # Last resort: use ImageMagick convert command
    try:
        import subprocess

        if pages is None:
            # Get page count first
            page_count = get_pdf_page_count(pdf_path)
            pages = list(range(page_count))

        for page_num in pages:
            output_path = output_dir / f"page_{page_num:03d}.{format}"
            result = subprocess.run([
                "convert",
                "-density", str(dpi),
                f"{pdf_path}[{page_num}]",
                str(output_path)
            ], capture_output=True)

            if result.returncode == 0 and output_path.exists():
                generated.append(output_path)

        return generated

    except Exception as e:
        raise RuntimeError(
            f"Could not convert PDF to images. "
            f"Please install PyMuPDF (pip install pymupdf) or "
            f"pdf2image (pip install pdf2image). Error: {e}"
        )


def extract_pdf_text(pdf_path: str, page: Optional[int] = None) -> str:
    """
    Extract text from PDF for searching/debugging.

    Args:
        pdf_path: Path to PDF
        page: Specific page number (0-indexed), or None for all

    Returns:
        Extracted text content
    """
    try:
        import fitz

        doc = fitz.open(pdf_path)
        text_parts = []

        if page is not None:
            if 0 <= page < len(doc):
                text_parts.append(doc.load_page(page).get_text())
        else:
            for p in doc:
                text_parts.append(p.get_text())

        doc.close()
        return "\n\n---\n\n".join(text_parts)

    except ImportError:
        return "PyMuPDF not installed - cannot extract text"


def get_pdf_metadata(pdf_path: str) -> dict:
    """Get PDF metadata."""
    try:
        import fitz

        doc = fitz.open(pdf_path)
        metadata = doc.metadata
        metadata["page_count"] = len(doc)

        # Get page dimensions
        if len(doc) > 0:
            page = doc.load_page(0)
            rect = page.rect
            metadata["width"] = rect.width
            metadata["height"] = rect.height

        doc.close()
        return metadata

    except ImportError:
        return {"error": "PyMuPDF not installed"}


if __name__ == "__main__":
    # Test script
    import sys

    if len(sys.argv) < 2:
        print("Usage: python pdf_utils.py <pdf_path> [output_dir]")
        sys.exit(1)

    pdf_path = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "preview"

    print(f"PDF: {pdf_path}")
    print(f"Output: {output_dir}")

    # Get info
    page_count = get_pdf_page_count(pdf_path)
    print(f"Pages: {page_count}")

    # Convert first 3 pages
    pages_to_convert = list(range(min(3, page_count)))
    print(f"Converting pages: {pages_to_convert}")

    images = convert_pdf_to_images(pdf_path, output_dir, pages=pages_to_convert)
    print(f"Generated: {images}")

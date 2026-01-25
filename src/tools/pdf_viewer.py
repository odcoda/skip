#!/usr/bin/env python3
"""
PDF Viewer Tool

Converts PDF pages to images for visual inspection and layout debugging.
Uses PyMuPDF (fitz) which doesn't require external dependencies.
"""

import sys
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import fitz  # PyMuPDF
from PIL import Image
import io


def pdf_to_images(pdf_path: str, output_dir: str = None, dpi: int = 150,
                  pages: list = None) -> list:
    """
    Convert PDF pages to PNG images.

    Args:
        pdf_path: Path to the PDF file
        output_dir: Directory to save images (default: same as PDF)
        dpi: Resolution in DPI (default: 150)
        pages: List of page numbers to convert (0-indexed), None for all

    Returns:
        List of paths to generated images
    """
    pdf_path = Path(pdf_path)
    if output_dir is None:
        output_dir = pdf_path.parent / "preview"
    else:
        output_dir = Path(output_dir)

    output_dir.mkdir(parents=True, exist_ok=True)

    doc = fitz.open(str(pdf_path))
    output_paths = []

    # Calculate zoom factor for desired DPI (72 is PDF default)
    zoom = dpi / 72
    mat = fitz.Matrix(zoom, zoom)

    page_range = pages if pages else range(len(doc))

    for page_num in page_range:
        if page_num >= len(doc):
            print(f"Warning: Page {page_num} doesn't exist, skipping")
            continue

        page = doc[page_num]
        pix = page.get_pixmap(matrix=mat)

        # Convert to PIL Image
        img_data = pix.tobytes("png")

        # Save as PNG
        output_path = output_dir / f"{pdf_path.stem}_page_{page_num + 1:03d}.png"
        with open(output_path, 'wb') as f:
            f.write(img_data)

        output_paths.append(str(output_path))
        print(f"Saved page {page_num + 1} to {output_path}")

    doc.close()
    return output_paths


def get_pdf_text(pdf_path: str, page_num: int = None) -> str:
    """
    Extract text from a PDF for content verification.

    Args:
        pdf_path: Path to the PDF file
        page_num: Specific page (0-indexed), None for all pages

    Returns:
        Extracted text
    """
    doc = fitz.open(str(pdf_path))

    if page_num is not None:
        if page_num >= len(doc):
            return f"Error: Page {page_num} doesn't exist"
        text = doc[page_num].get_text()
    else:
        text = "\n\n--- Page Break ---\n\n".join(
            page.get_text() for page in doc
        )

    doc.close()
    return text


def get_pdf_info(pdf_path: str) -> dict:
    """
    Get PDF metadata and page info.
    """
    doc = fitz.open(str(pdf_path))

    info = {
        'path': str(pdf_path),
        'page_count': len(doc),
        'metadata': doc.metadata,
        'pages': []
    }

    for i, page in enumerate(doc):
        rect = page.rect
        info['pages'].append({
            'number': i + 1,
            'width': rect.width,
            'height': rect.height,
            'text_length': len(page.get_text())
        })

    doc.close()
    return info


def main():
    import argparse

    parser = argparse.ArgumentParser(description='PDF viewing and conversion tool')
    parser.add_argument('pdf_path', help='Path to PDF file')
    parser.add_argument('-o', '--output', help='Output directory for images')
    parser.add_argument('-d', '--dpi', type=int, default=150, help='DPI for images')
    parser.add_argument('-p', '--pages', type=int, nargs='+', help='Specific pages (1-indexed)')
    parser.add_argument('--info', action='store_true', help='Show PDF info only')
    parser.add_argument('--text', action='store_true', help='Extract text only')
    parser.add_argument('--text-page', type=int, help='Extract text from specific page (1-indexed)')

    args = parser.parse_args()

    if args.info:
        info = get_pdf_info(args.pdf_path)
        print(f"PDF: {info['path']}")
        print(f"Pages: {info['page_count']}")
        for page in info['pages']:
            print(f"  Page {page['number']}: {page['width']:.0f}x{page['height']:.0f} pts, "
                  f"{page['text_length']} chars")
    elif args.text:
        page_num = (args.text_page - 1) if args.text_page else None
        print(get_pdf_text(args.pdf_path, page_num))
    else:
        # Convert pages to 0-indexed if provided
        pages = [p - 1 for p in args.pages] if args.pages else None
        pdf_to_images(args.pdf_path, args.output, args.dpi, pages)


if __name__ == "__main__":
    main()

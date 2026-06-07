#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "flask>=3.0",
#     "pymupdf>=1.24",
#     "requests>=2.31",
#     "beautifulsoup4>=4.12",
# ]
# ///
"""
SCP Foundation Book Generator - Web Frontend

A Flask application providing a web interface for downloading, converting,
and rendering SCP Foundation articles into LaTeX books.

Usage:
    uv run src/web/app.py
"""

import os
import sys
import json
import glob
import re
from pathlib import Path
from datetime import datetime
from flask import Flask, render_template, jsonify, request, send_file, abort

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from scp_downloader import SCPDownloader
from parsers.enhanced_wikidot_parser import EnhancedWikidotParser
from parsers.markdown_renderer import MarkdownRenderer
from latex_pipeline.enhanced_converter import EnhancedLaTeXConverter
from pipeline.builder import SCPBookBuilder, PipelineConfig
from latex_pipeline.compile_latex import compile_latex_to_pdf
from web.pdf_utils import convert_pdf_to_images, get_pdf_page_count

app = Flask(__name__)

# Configure paths relative to project root
PROJECT_ROOT = Path(__file__).parent.parent.parent
OUTPUT_DIR = PROJECT_ROOT / "output"
DOWNLOADS_DIR = OUTPUT_DIR / "downloads"
RAW_DOWNLOADS_DIR = OUTPUT_DIR / "raw_downloads"
INTERMEDIATE_DIR = OUTPUT_DIR / "intermediate"
LATEX_DIR = OUTPUT_DIR / "latex"
PDF_DIR = OUTPUT_DIR / "pdf"
PREVIEW_DIR = OUTPUT_DIR / "preview"

# Ensure directories exist
for dir_path in [DOWNLOADS_DIR, RAW_DOWNLOADS_DIR, OUTPUT_DIR, INTERMEDIATE_DIR,
                 LATEX_DIR, PDF_DIR, PREVIEW_DIR]:
    dir_path.mkdir(parents=True, exist_ok=True)


def get_page_slug(filename):
    """Extract the stable page slug from an output filename."""
    return Path(filename).stem


def get_display_name(slug):
    """Return a human-friendly page label for a downloaded slug."""
    match = re.fullmatch(r'scp-(\d+)', slug.lower())
    if match:
        return f"SCP-{match.group(1)}"
    return slug


def get_scp_number(slug):
    """Extract an SCP number from a page slug, if present."""
    match = re.fullmatch(r'scp-(\d+)', slug.lower())
    return match.group(1) if match else None


def normalize_page_input(value):
    """Normalize user input into a downloader page slug or URL."""
    page = str(value).strip()
    if page.lower().startswith("scp-"):
        return page.lower()
    if page.isdigit():
        return f"scp-{page}"
    return page


def slug_to_latex_filename(slug):
    """Map a page slug to the filename used by the web LaTeX preview."""
    scp_num = get_scp_number(slug)
    if scp_num:
        return f"scp_{scp_num}.tex"
    safe_slug = re.sub(r"[^a-zA-Z0-9_.-]+", "_", slug).strip("_")
    return f"{safe_slug}.tex"


def article_sort_key(article):
    """Sort SCP pages numerically and related pages alphabetically."""
    scp_num = article.get("scp_number")
    if scp_num is not None:
        return (0, int(scp_num), "")
    return (1, 0, article["slug"])


def get_article_status():
    """
    Scan directories and return status of all known downloaded/parsed pages.

    Returns dict mapping page slug to status info.
    """
    articles = {}

    # Find all downloaded wikidot-source files, including related non-SCP pages.
    for txt_file in DOWNLOADS_DIR.glob("*.txt"):
        slug = get_page_slug(txt_file.name)
        stat = txt_file.stat()
        raw_html_path = RAW_DOWNLOADS_DIR / f"{slug}.html"
        articles[slug] = {
            "slug": slug,
            "number": get_scp_number(slug) or slug,
            "scp_number": get_scp_number(slug),
            "display_name": get_display_name(slug),
            "downloaded": True,
            "download_path": str(txt_file),
            "download_size": stat.st_size,
            "download_time": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "raw_html": raw_html_path.exists(),
            "raw_html_path": str(raw_html_path) if raw_html_path.exists() else None,
            "parsed": False,
            "markdown_available": False,
            "latex_generated": False,
            "pdf_compiled": False
        }

    # Check for parsed JSON files
    for json_file in INTERMEDIATE_DIR.glob("*.json"):
        slug = get_page_slug(json_file.name)
        if slug not in articles:
            articles[slug] = {
                "slug": slug,
                "number": get_scp_number(slug) or slug,
                "scp_number": get_scp_number(slug),
                "display_name": get_display_name(slug),
                "downloaded": False,
                "raw_html": False,
                "parsed": False,
                "markdown_available": False,
                "latex_generated": False,
                "pdf_compiled": False
            }
        articles[slug]["parsed"] = True
        articles[slug]["markdown_available"] = True
        articles[slug]["json_path"] = str(json_file)

    # Check for individual LaTeX files
    articles_dir = LATEX_DIR / "articles"
    if articles_dir.exists():
        for slug, article in articles.items():
            tex_file = articles_dir / slug_to_latex_filename(slug)
            if tex_file.exists():
                article["latex_generated"] = True
                article["latex_path"] = str(tex_file)

    # Check for compiled PDFs (individual or book)
    main_pdf = PDF_DIR / "scp_book.pdf"
    if main_pdf.exists():
        for scp_num in articles:
            articles[scp_num]["pdf_compiled"] = True
            articles[scp_num]["pdf_path"] = str(main_pdf)

    return articles


def get_scp_title_from_file(filepath):
    """Try to extract title/item number from SCP file content."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read(2000)  # Read first 2000 chars

        # Look for Item # line
        item_match = re.search(r'\*\*Item #:\*\*\s*(SCP-\d+)', content)
        if item_match:
            return item_match.group(1)

        # Look for object class
        class_match = re.search(r'\*\*Object Class:\*\*\s*(\w+)', content)
        obj_class = class_match.group(1) if class_match else None

        return obj_class
    except:
        return None


@app.route('/')
def index():
    """Main page with article listing."""
    return render_template('index.html')


@app.route('/api/articles')
def api_articles():
    """Get list of all articles with their status."""
    articles = get_article_status()

    # Convert to sorted list
    article_list = sorted(articles.values(), key=article_sort_key)

    return jsonify({
        "articles": article_list,
        "total": len(article_list),
        "downloaded": sum(1 for a in article_list if a["downloaded"]),
        "parsed": sum(1 for a in article_list if a["parsed"]),
        "latex_generated": sum(1 for a in article_list if a["latex_generated"]),
        "pdf_compiled": sum(1 for a in article_list if a["pdf_compiled"])
    })


@app.route('/api/article/<path:page_slug>')
def api_article_detail(page_slug):
    """Get detailed info about a specific downloaded or parsed page."""
    articles = get_article_status()

    if page_slug not in articles:
        return jsonify({"error": f"{page_slug} not found"}), 404

    article = articles[page_slug]

    # Try to load parsed content if available
    if article.get("parsed") and article.get("json_path"):
        try:
            with open(article["json_path"], 'r', encoding='utf-8') as f:
                article["parsed_content"] = json.load(f)
            article["markdown_preview"] = MarkdownRenderer().render_document(article["parsed_content"])
        except:
            pass

    # Load wikidot source preview
    if article.get("downloaded") and article.get("download_path"):
        try:
            with open(article["download_path"], 'r', encoding='utf-8') as f:
                article["source_preview"] = f.read(10000)
        except:
            pass

    # Load full-page raw HTML preview
    if article.get("raw_html_path"):
        try:
            with open(article["raw_html_path"], 'r', encoding='utf-8') as f:
                article["raw_html_preview"] = f.read(10000)
        except:
            pass

    return jsonify(article)


@app.route('/api/download', methods=['POST'])
def api_download():
    """Download one or more SCP articles."""
    data = request.json

    if not data:
        return jsonify({"error": "No data provided"}), 400

    page_slugs = data.get("page_slugs", data.get("scp_numbers", []))
    if isinstance(page_slugs, str):
        page_slugs = [page_slugs]

    # Also support range
    start = data.get("start")
    end = data.get("end")

    if start and end:
        page_slugs = [f"scp-{i}" for i in range(int(start), int(end) + 1)]

    if not page_slugs:
        return jsonify({"error": "No pages provided"}), 400

    results = []
    downloader = SCPDownloader(
        output_dir=str(DOWNLOADS_DIR),
        raw_output_dir=str(RAW_DOWNLOADS_DIR)
    )

    for page_slug in page_slugs:
        try:
            page_slug = normalize_page_input(page_slug)
            path = downloader.download_page(page_slug)
            saved_slug = get_page_slug(path)
            results.append({
                "slug": saved_slug,
                "display_name": get_display_name(saved_slug),
                "success": True,
                "path": path
            })
        except Exception as e:
            results.append({
                "slug": str(page_slug),
                "success": False,
                "error": str(e)
            })

    return jsonify({
        "results": results,
        "total": len(results),
        "successful": sum(1 for r in results if r["success"])
    })


@app.route('/api/parse', methods=['POST'])
def api_parse():
    """Parse downloaded SCP articles to JSON."""
    data = request.json or {}

    page_slugs = data.get("page_slugs", data.get("scp_numbers", []))
    parse_all = data.get("all", False)

    parser = EnhancedWikidotParser()
    results = []

    if parse_all:
        # Parse all downloaded files
        files = list(DOWNLOADS_DIR.glob("*.txt"))
    else:
        # Parse specific files
        files = []
        for page_slug in page_slugs:
            page_slug = normalize_page_input(page_slug)
            filepath = DOWNLOADS_DIR / f"{page_slug}.txt"
            if filepath.exists():
                files.append(filepath)

    for filepath in files:
        page_slug = get_page_slug(filepath.name)
        try:
            doc = parser.parse_file(str(filepath))

            # Save JSON
            json_path = INTERMEDIATE_DIR / f"{page_slug}.json"
            parser.save_json(doc, str(json_path))

            results.append({
                "slug": page_slug,
                "display_name": get_display_name(page_slug),
                "success": True,
                "sections": len(doc.sections),
                "object_class": doc.object_class
            })
        except Exception as e:
            results.append({
                "slug": page_slug,
                "success": False,
                "error": str(e)
            })

    return jsonify({
        "results": results,
        "total": len(results),
        "successful": sum(1 for r in results if r["success"])
    })


@app.route('/api/convert', methods=['POST'])
def api_convert():
    """Convert parsed articles to LaTeX."""
    data = request.json or {}

    page_slugs = data.get("page_slugs", data.get("scp_numbers", []))
    convert_all = data.get("all", False)

    config = PipelineConfig(
        input_dir=str(DOWNLOADS_DIR),
        output_dir=str(OUTPUT_DIR)
    )
    converter = EnhancedLaTeXConverter(config)
    parser = EnhancedWikidotParser()

    results = []

    # Determine which files to convert
    if convert_all:
        json_files = list(INTERMEDIATE_DIR.glob("*.json"))
    else:
        json_files = []
        for page_slug in page_slugs:
            page_slug = normalize_page_input(page_slug)
            json_path = INTERMEDIATE_DIR / f"{page_slug}.json"
            if json_path.exists():
                json_files.append(json_path)
            else:
                # Try parsing first if JSON doesn't exist
                txt_path = DOWNLOADS_DIR / f"{page_slug}.txt"
                if txt_path.exists():
                    try:
                        doc = parser.parse_file(str(txt_path))
                        parser.save_json(doc, str(json_path))
                        json_files.append(json_path)
                    except:
                        pass

    # Ensure articles directory exists
    articles_dir = LATEX_DIR / "articles"
    articles_dir.mkdir(parents=True, exist_ok=True)

    for json_path in json_files:
        page_slug = get_page_slug(json_path.name)
        try:
            # Load parsed document
            with open(json_path, 'r') as f:
                doc_data = json.load(f)

            # Re-parse from original to get proper objects
            txt_path = DOWNLOADS_DIR / f"{page_slug}.txt"
            if txt_path.exists():
                doc = parser.parse_file(str(txt_path))
            else:
                results.append({
                    "slug": page_slug,
                    "success": False,
                    "error": "Source file not found"
                })
                continue

            # Generate LaTeX
            latex_content = converter.generate_document_latex(doc)

            # Save to individual file
            tex_path = articles_dir / slug_to_latex_filename(page_slug)
            with open(tex_path, 'w', encoding='utf-8') as f:
                f.write(latex_content)

            results.append({
                "slug": page_slug,
                "display_name": get_display_name(page_slug),
                "success": True,
                "latex_path": str(tex_path),
                "latex_size": len(latex_content)
            })
        except Exception as e:
            results.append({
                "slug": page_slug,
                "success": False,
                "error": str(e)
            })

    return jsonify({
        "results": results,
        "total": len(results),
        "successful": sum(1 for r in results if r["success"])
    })


@app.route('/api/compile', methods=['POST'])
def api_compile():
    """Compile LaTeX to PDF using the full pipeline."""
    data = request.json or {}

    try:
        # Use the full pipeline
        config = PipelineConfig(
            input_dir=str(DOWNLOADS_DIR),
            output_dir=str(OUTPUT_DIR),
            title=data.get("title", "SCP Foundation Archive"),
            subtitle=data.get("subtitle", "A Collection of Anomalous Objects")
        )

        builder = SCPBookBuilder(config)

        # Build the book
        latex_file = builder.build_book()

        # Compile to PDF
        success, pdf_path, error = compile_latex_to_pdf(
            latex_file,
            output_pdf_dir=str(PDF_DIR),
            build_dir=str(LATEX_DIR / "build")
        )

        if success:
            return jsonify({
                "success": True,
                "pdf_path": pdf_path,
                "latex_path": latex_file,
                "message": "PDF compiled successfully"
            })
        else:
            return jsonify({
                "success": False,
                "error": error,
                "latex_path": latex_file
            })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        })


@app.route('/api/pdf/info')
def api_pdf_info():
    """Get info about the compiled PDF."""
    pdf_path = PDF_DIR / "scp_book.pdf"

    if not pdf_path.exists():
        return jsonify({"exists": False})

    stat = pdf_path.stat()
    page_count = get_pdf_page_count(str(pdf_path))

    return jsonify({
        "exists": True,
        "path": str(pdf_path),
        "size": stat.st_size,
        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        "pages": page_count
    })


@app.route('/api/pdf/preview')
def api_pdf_preview():
    """Generate preview images from PDF."""
    pdf_path = PDF_DIR / "scp_book.pdf"

    if not pdf_path.exists():
        return jsonify({"error": "PDF not found"}), 404

    page = request.args.get("page", type=int)
    dpi = request.args.get("dpi", 150, type=int)

    try:
        # Generate preview images
        image_paths = convert_pdf_to_images(
            str(pdf_path),
            str(PREVIEW_DIR),
            dpi=dpi,
            pages=[page] if page is not None else None
        )

        return jsonify({
            "success": True,
            "images": [str(p) for p in image_paths],
            "count": len(image_paths)
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        })


@app.route('/api/pdf/page/<int:page_num>')
def api_pdf_page(page_num):
    """Get a specific page as an image."""
    # Check if preview already exists
    preview_path = PREVIEW_DIR / f"page_{page_num:03d}.png"

    if not preview_path.exists():
        # Generate it
        pdf_path = PDF_DIR / "scp_book.pdf"
        if not pdf_path.exists():
            abort(404)

        try:
            convert_pdf_to_images(
                str(pdf_path),
                str(PREVIEW_DIR),
                dpi=150,
                pages=[page_num]
            )
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    if preview_path.exists():
        return send_file(preview_path, mimetype='image/png')
    else:
        abort(404)


@app.route('/api/pdf/download')
def api_pdf_download():
    """Download the compiled PDF."""
    pdf_path = PDF_DIR / "scp_book.pdf"

    if not pdf_path.exists():
        abort(404)

    return send_file(pdf_path, as_attachment=True, download_name="scp_book.pdf")


@app.route('/api/source/<path:page_slug>')
def api_source_content(page_slug):
    """Get downloaded wikidot source for a page."""
    source_path = DOWNLOADS_DIR / f"{page_slug}.txt"

    if not source_path.exists():
        return jsonify({"error": "Downloaded source not found"}), 404

    with open(source_path, 'r', encoding='utf-8') as f:
        content = f.read()

    return jsonify({
        "slug": page_slug,
        "content": content,
        "path": str(source_path)
    })


@app.route('/api/raw-html/<path:page_slug>')
def api_raw_html_content(page_slug):
    """Get downloaded raw HTML for a page."""
    html_path = RAW_DOWNLOADS_DIR / f"{page_slug}.html"

    if not html_path.exists():
        return jsonify({"error": "Raw HTML file not found"}), 404

    with open(html_path, 'r', encoding='utf-8') as f:
        content = f.read()

    return jsonify({
        "slug": page_slug,
        "content": content,
        "path": str(html_path)
    })


@app.route('/api/markdown/<path:page_slug>')
def api_markdown_content(page_slug):
    """Get rendered Markdown from parsed JSON, parsing from source if needed."""
    json_path = INTERMEDIATE_DIR / f"{page_slug}.json"

    try:
        if json_path.exists():
            markdown = MarkdownRenderer().render_json_file(json_path)
        else:
            source_path = DOWNLOADS_DIR / f"{page_slug}.txt"
            if not source_path.exists():
                return jsonify({"error": "Page source not found"}), 404
            doc = EnhancedWikidotParser().parse_file(str(source_path))
            markdown = MarkdownRenderer().render_document(doc)

        return jsonify({
            "slug": page_slug,
            "content": markdown,
            "path": str(json_path) if json_path.exists() else None
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/latex/<path:page_slug>')
def api_latex_content(page_slug):
    """Get LaTeX content for a specific page."""
    tex_path = LATEX_DIR / "articles" / slug_to_latex_filename(page_slug)

    if not tex_path.exists():
        return jsonify({"error": "LaTeX file not found"}), 404

    with open(tex_path, 'r', encoding='utf-8') as f:
        content = f.read()

    return jsonify({
        "slug": page_slug,
        "content": content,
        "path": str(tex_path)
    })


@app.route('/api/search')
def api_search():
    """Search for SCPs by number or content."""
    query = request.args.get("q", "").strip()

    if not query:
        return jsonify({"results": []})

    articles = get_article_status()
    results = []

    for slug, article in articles.items():
        # Search by number
        if query.lower() in article["display_name"].lower() or query.lower() in slug.lower():
            results.append(article)
            continue

        # Search in content if downloaded
        if article.get("downloaded"):
            try:
                with open(article["download_path"], 'r', encoding='utf-8') as f:
                    content = f.read()
                if query.lower() in content.lower():
                    results.append(article)
            except:
                pass

    return jsonify({
        "query": query,
        "results": results,
        "count": len(results)
    })


@app.route('/preview/<path:filename>')
def serve_preview(filename):
    """Serve preview images."""
    return send_file(PREVIEW_DIR / filename)


if __name__ == '__main__':
    print(f"Project root: {PROJECT_ROOT}")
    print(f"Downloads: {DOWNLOADS_DIR}")
    print(f"Output: {OUTPUT_DIR}")

    app.run(debug=True, port=5000)

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
from latex.enhanced_converter import EnhancedLaTeXConverter
from pipeline.builder import SCPBookBuilder, PipelineConfig
from pipeline.compile_latex import compile_latex_to_pdf
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


def get_scp_number(filename):
    """Extract SCP number from filename like 'scp-173.txt' -> '173'"""
    match = re.search(r'scp-(\d+)', filename.lower())
    return match.group(1) if match else None


def get_article_status():
    """
    Scan directories and return status of all known SCP articles.

    Returns dict mapping SCP number to status info.
    """
    articles = {}

    # Find all downloaded files
    for txt_file in DOWNLOADS_DIR.glob("scp-*.txt"):
        scp_num = get_scp_number(txt_file.name)
        if scp_num:
            stat = txt_file.stat()
            articles[scp_num] = {
                "number": scp_num,
                "downloaded": True,
                "download_path": str(txt_file),
                "download_size": stat.st_size,
                "download_time": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "parsed": False,
                "latex_generated": False,
                "pdf_compiled": False
            }

    # Check for parsed JSON files
    for json_file in INTERMEDIATE_DIR.glob("scp-*.json"):
        scp_num = get_scp_number(json_file.name)
        if scp_num and scp_num in articles:
            articles[scp_num]["parsed"] = True
            articles[scp_num]["json_path"] = str(json_file)

    # Check for individual LaTeX files
    articles_dir = LATEX_DIR / "articles"
    if articles_dir.exists():
        for tex_file in articles_dir.glob("scp_*.tex"):
            # scp_173.tex -> 173
            match = re.search(r'scp_(\d+)\.tex', tex_file.name)
            if match:
                scp_num = match.group(1)
                if scp_num in articles:
                    articles[scp_num]["latex_generated"] = True
                    articles[scp_num]["latex_path"] = str(tex_file)

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
    article_list = sorted(articles.values(), key=lambda x: int(x["number"]))

    return jsonify({
        "articles": article_list,
        "total": len(article_list),
        "downloaded": sum(1 for a in article_list if a["downloaded"]),
        "parsed": sum(1 for a in article_list if a["parsed"]),
        "latex_generated": sum(1 for a in article_list if a["latex_generated"]),
        "pdf_compiled": sum(1 for a in article_list if a["pdf_compiled"])
    })


@app.route('/api/article/<scp_num>')
def api_article_detail(scp_num):
    """Get detailed info about a specific article."""
    articles = get_article_status()

    if scp_num not in articles:
        return jsonify({"error": f"SCP-{scp_num} not found"}), 404

    article = articles[scp_num]

    # Try to load parsed content if available
    if article.get("parsed") and article.get("json_path"):
        try:
            with open(article["json_path"], 'r') as f:
                article["parsed_content"] = json.load(f)
        except:
            pass

    # Load raw content preview
    if article.get("downloaded") and article.get("download_path"):
        try:
            with open(article["download_path"], 'r', encoding='utf-8') as f:
                article["raw_preview"] = f.read(5000)
        except:
            pass

    return jsonify(article)


@app.route('/api/download', methods=['POST'])
def api_download():
    """Download one or more SCP articles."""
    data = request.json

    if not data:
        return jsonify({"error": "No data provided"}), 400

    scp_numbers = data.get("scp_numbers", [])
    if isinstance(scp_numbers, str):
        scp_numbers = [scp_numbers]

    # Also support range
    start = data.get("start")
    end = data.get("end")

    if start and end:
        scp_numbers = [str(i) for i in range(int(start), int(end) + 1)]

    if not scp_numbers:
        return jsonify({"error": "No SCP numbers provided"}), 400

    results = []
    downloader = SCPDownloader(
        output_dir=str(DOWNLOADS_DIR),
        raw_output_dir=str(RAW_DOWNLOADS_DIR)
    )

    for scp_num in scp_numbers:
        try:
            # Clean up input
            scp_num = str(scp_num).strip()
            if scp_num.lower().startswith("scp-"):
                scp_num = scp_num[4:]

            path = downloader.download_page(scp_num)
            results.append({
                "scp_number": scp_num,
                "success": True,
                "path": path
            })
        except Exception as e:
            results.append({
                "scp_number": scp_num,
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

    scp_numbers = data.get("scp_numbers", [])
    parse_all = data.get("all", False)

    parser = EnhancedWikidotParser()
    results = []

    if parse_all:
        # Parse all downloaded files
        files = list(DOWNLOADS_DIR.glob("scp-*.txt"))
    else:
        # Parse specific files
        files = []
        for scp_num in scp_numbers:
            scp_num = str(scp_num).strip()
            if scp_num.lower().startswith("scp-"):
                scp_num = scp_num[4:]

            filepath = DOWNLOADS_DIR / f"scp-{scp_num}.txt"
            if filepath.exists():
                files.append(filepath)

    for filepath in files:
        scp_num = get_scp_number(filepath.name)
        try:
            doc = parser.parse_file(str(filepath))

            # Save JSON
            json_path = INTERMEDIATE_DIR / f"scp-{scp_num}.json"
            parser.save_json(doc, str(json_path))

            results.append({
                "scp_number": scp_num,
                "success": True,
                "sections": len(doc.sections),
                "object_class": doc.object_class
            })
        except Exception as e:
            results.append({
                "scp_number": scp_num,
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

    scp_numbers = data.get("scp_numbers", [])
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
        json_files = list(INTERMEDIATE_DIR.glob("scp-*.json"))
    else:
        json_files = []
        for scp_num in scp_numbers:
            scp_num = str(scp_num).strip()
            if scp_num.lower().startswith("scp-"):
                scp_num = scp_num[4:]

            json_path = INTERMEDIATE_DIR / f"scp-{scp_num}.json"
            if json_path.exists():
                json_files.append(json_path)
            else:
                # Try parsing first if JSON doesn't exist
                txt_path = DOWNLOADS_DIR / f"scp-{scp_num}.txt"
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
        scp_num = get_scp_number(json_path.name)
        try:
            # Load parsed document
            with open(json_path, 'r') as f:
                doc_data = json.load(f)

            # Re-parse from original to get proper objects
            txt_path = DOWNLOADS_DIR / f"scp-{scp_num}.txt"
            if txt_path.exists():
                doc = parser.parse_file(str(txt_path))
            else:
                results.append({
                    "scp_number": scp_num,
                    "success": False,
                    "error": "Source file not found"
                })
                continue

            # Generate LaTeX
            latex_content = converter.generate_document_latex(doc)

            # Save to individual file
            tex_path = articles_dir / f"scp_{scp_num}.tex"
            with open(tex_path, 'w', encoding='utf-8') as f:
                f.write(latex_content)

            results.append({
                "scp_number": scp_num,
                "success": True,
                "latex_path": str(tex_path),
                "latex_size": len(latex_content)
            })
        except Exception as e:
            results.append({
                "scp_number": scp_num,
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


@app.route('/api/latex/<scp_num>')
def api_latex_content(scp_num):
    """Get LaTeX content for a specific SCP."""
    tex_path = LATEX_DIR / "articles" / f"scp_{scp_num}.tex"

    if not tex_path.exists():
        return jsonify({"error": "LaTeX file not found"}), 404

    with open(tex_path, 'r', encoding='utf-8') as f:
        content = f.read()

    return jsonify({
        "scp_number": scp_num,
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

    for scp_num, article in articles.items():
        # Search by number
        if query.lower() in f"scp-{scp_num}".lower():
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

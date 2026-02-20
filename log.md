# Development Log

## 2026-02-20 REDACTED theme system implemented

Added modular LaTeX theme system:
- `src/latex/themes/scpbase.sty` — base semantic layer (all commands/environments with minimal defaults)
- `src/latex/themes/redacted.sty` — classified-document theme (red accents, Courier headers, tcolorbox sections, classification stamps, styled title page)
- `src/latex/themes/graphics/stamps.tex` — reusable TikZ decorative elements

Pipeline changes:
- `enhanced_converter.py`: removed all hardcoded styling, preamble now just loads `\usepackage{scpbase}` + `\usepackage{<theme>}`
- `builder.py`: added `theme` config field, copies .sty files to latex output dir
- `compile_latex.py`: sets TEXINPUTS so pdflatex finds theme files

Volume 1 compiles cleanly (37 pages, 316KB, zero errors). Theme swap verified — `scpbase`-only also compiles (35 pages).

Up next:
- Visual review of PDF (need poppler for rendering)
- Iterate on styling details

## 2026-02-20 Downloaded original images for SCP-173 and SCP-682

Downloaded the original iconic images that were removed from the wiki:
- **SCP-173**: "Untitled 2004" museum installation photo by Tuyoshi Saito (from cargocollective.com)
- **SCP-682**: Sakhalin Island Sea Wolf photos (4 photos from Cryptid Wiki, converted from WebP to JPEG)

Stored in `output/images/<scp>/originals/` subdirectories. Updated `images.yaml` with `location: originals/` field and kept both original and current wiki images for SCP-682. Updated builder and converter to handle the `location` subdirectory.

Rebuilt Volume 1 PDF (3.5MB) - both original images rendering correctly via wrapfigure.

## 2026-02-14 Original/iconic image research for copyright-removed SCPs

Researched original images that were removed from SCP wiki articles and updated `data/images.yaml` with findings:

- **SCP-173**: "Untitled 2004" by Izumi Kato, photo by Keisuke Yamamoto. Removed Feb 2022 by wiki staff (not demanded by Kato). Artist's page: izumikato.com/Untitled-2004. NOT CC-licensed.
- **SCP-682**: Original was "Sakhalin Island Sea Wolf" (decomposed beluga whale, Sakhalin Island 2006). Replaced with beached humpback whale (CC BY 2.0 by Paxson Woelber, edited by OccultistMave). Original photos available on Cryptid Wiki.
- **SCP-882**: Current image (Gears2.jpg by psyberartist, Flickr CC BY 2.0) appears to be the original -- no evidence of replacement found.
- **SCP-914**: Current image (gears.jpg by Thomas Claveirole, Flickr CC BY-SA 2.0) appears to be the original -- no evidence of replacement found.

Updated images.yaml with URLs, attribution, licensing details, and context for all four.

Up next:
- Download the Sakhalin photos for SCP-682 reference
- Integrate images into PDF builds

## 2026-01-25 Volume 1 first build complete

Built Volume 1: Heritage Collection (14 iconic SCPs from the 2013 Heritage Collection)

**Key achievements:**
- Installed PyMuPDF for PDF-to-image conversion (enables visual layout debugging)
- Created `src/tools/pdf_viewer.py` for converting PDF pages to images
- Created `src/build_volume1.py` for building Volume 1 specifically
- Fixed LaTeX converter issues:
  - Cleaned [[include...]] tags from section titles
  - Fixed scpquote environment (removed broken leftbar dependency)
  - Added Unicode support (Greek letters)
  - Cleaned wikidot markup from content (collapsible, user links, spans, etc.)
- Successfully generated 32-page PDF (326KB)

**Heritage Collection articles:** SCP-055, 076, 087, 093, 173, 231, 239, 343, 500, 682, 701, 882, 914, 963

**Output:** `output/pdf/volume1_heritage_collection.pdf`

**Subsequent improvements:**
- Added SCP names to TOC (via HeritageCollectionBuilder metadata injection)
- Fixed LaTeX two-pass compilation for proper TOC generation
- TOC now shows "SCP-055: [Unknown]", "SCP-682: Hard-to-Destroy Reptile", etc.

**Related pages system:**
- Created `data/related_pages.yaml` to track supplementary content per SCP
- Fixed downloader to handle non-SCP page names (e.g., "document-087-i")
- Fixed token extraction bug (cookie set on page visit, not main page)
- Downloaded all key related pages:
  - SCP-087: 3 exploration logs (279 lines)
  - SCP-682: termination log (2768 lines!)
  - SCP-701: incident reports (133 lines)
  - SCP-963: Dr. Bright evaluations (168 lines)
- Note: SCP-914's experiment logs need special handling (spread across sandbox pages)

**Images:**
- Created `data/images.yaml` tracking all images per SCP
- Downloaded 10 images from wdfiles.com into `output/images/<scp>/`
- SCPs with images: 087 (3), 231 (1), 682 (1), 701 (1), 882 (1), 914 (1), 963 (2)
- SCPs needing original images found online: 173, 682, 882, 914
- SCP-173's original is "Untitled 2004" by Izumi Kato (removed from wiki)

**Up next:**
- Integrate images into PDF
- Find original/iconic images for 173, 682, 882, 914
- Improve chapter organization
- Add basic styling
- Integrate related pages into book builds

## 2026-01-06 Test suite implementation

Added pytest-based test suite with synthetic fixtures:
- Created `tests/fixtures/` with 4 synthetic SCP test files
- Created `tests/expected/` with golden LaTeX output files
- Implemented 3 test types:
  1. Diff test: compares generated LaTeX against expected output
  2. Individual compilation: verifies each article compiles with pdflatex
  3. Book compilation: verifies multi-article book compiles
- Fixed converter to handle Unicode redaction characters (█ → \blackbox{})
- PDFs saved to `tests/output/` (gitignored) for manual inspection
- Tests run with: `uv run --with pytest pytest tests/`

## 2026-01-05 Directory restructure

Reorganized project structure:
- All source code now under `src/`
- All outputs (downloads, generated files) under `output/`
- Removed empty placeholder directories (assets/, templates/, examples/)
- Deleted duplicate `src/output/` directory
- Moved analysis scripts from `examples/single_scp/` to `src/tools/`
- Updated all scripts to use absolute paths via PROJECT_ROOT
- Updated .gitignore to exclude `output/`
- Updated CLAUDE.md with new structure

New structure:
```
src/           # All source code
output/        # All generated content (gitignored)
  downloads/   # Downloaded SCP sources
  raw_downloads/
  intermediate/
  latex/
  pdf/
```

## 2026-01-06 control flow review
reviewed all Python entrypoints, parsers, converters, and tools to map runtime flow and file usage

## 2026-01-06 parser/converter comparison
summarized differences between enhanced vs legacy parser and converter paths for user

## 2026-01-06 architecture doc
wrote parser/converter differences in doc/architecture.md

## 2026-01-06 architecture notes update
replaced doc/architecture.md with the full control flow/dependency summary and parser/converter comparison

## 2026-02-20 formatting pass (redacted theme + image restore)
Implemented a focused formatting pass for Volume 1:
- Restored embedded `component:image-block` images in article bodies (e.g. SCP-087/SCP-963) instead of placeholder text
- Made image paths robust relative to configured LaTeX/output directories
- Refined `redacted.sty` for 6x9: smaller body text, tighter margins, lighter transcript/section boxes
- Reworked redaction bars to marker-style textured censorship bars via TikZ (taller/less unicode-looking)
- Fixed PDF output path regression (`output/output/pdf` -> configured `output/pdf`)

Validated by rebuilding Volume 1 successfully (`output/pdf/scp_book.pdf`).

Up next:
- Visual polish pass after installing PDF page-image tooling in this environment

## 2026-02-20 right-aligned image rendering fix (volume1)
Fixed missing right-aligned top images in `output/pdf/scp_book.pdf`:
- Root cause: `wrapfigure` blocks were emitted before paragraph text at section starts, causing images to disappear in PDF output
- Replaced top image rendering with explicit `flushright` image blocks in converter (`src/latex/enhanced_converter.py`)

Verification:
- Rebuilt Volume 1 (`uv run src/build_volume1.py`)
- Ran PDF-to-image script on the generated PDF:
  - `venv/bin/python src/tools/pdf_viewer.py output/pdf/scp_book.pdf -o output/preview/volume1_check_after -p 11 12 15 16 26 29 32 33 36 38`
- Confirmed right-aligned images now render on target pages (e.g. SCP-087 page 11, SCP-173 page 15, SCP-682 page 26, SCP-963 page 36).

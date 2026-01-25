# Development Log

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
- Downloaded SCP-087 exploration logs (documents I, II, III)
- Note: Some pages fail with token auth errors (SCP-682 experiment log) - needs investigation

**Up next:**
- Improve chapter organization (single "Heritage Collection" chapter vs series split)
- Add basic styling (fonts, spacing, decorative elements)
- Handle images from SCP articles
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

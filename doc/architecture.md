Mapped the control flow and roles across the Python files; logged this in `log.md`.

**Control Flow**
- CLI downloader: `src/scp_downloader.py` -> `output/downloads/*.txt` + `output/raw_downloads/*.html`
- CLI pipeline: `src/pipeline/builder.py` -> parse -> `output/intermediate/*.json` -> LaTeX articles -> `output/latex/scp_book.tex` -> compile -> `output/pdf/*.pdf`
- Web launcher: `src/run_web.py` -> `src/web/app.py`
  - `/api/download` -> `SCPDownloader`
  - `/api/parse` -> `EnhancedWikidotParser`
  - `/api/convert` -> `EnhancedLaTeXConverter`
  - `/api/compile` -> `SCPBookBuilder` -> `compile_latex_to_pdf`
  - `/api/pdf/*` -> `src/web/pdf_utils.py`

**Files by Role**
- Real processing (runtime): `src/scp_downloader.py`, `src/pipeline/builder.py`, `src/pipeline/compile_latex.py`, `src/parsers/enhanced_wikidot_parser.py`, `src/latex/enhanced_converter.py`, `src/web/app.py`, `src/web/pdf_utils.py`, `src/run_web.py`
- Tests (pytest): `tests/test_latex_output.py`, `tests/conftest.py`
- Manual test/analysis scripts: `src/test_downloader.py`, `src/tools/analyze_scp_patterns.py`, `src/tools/test_content_completeness.py`, `src/tools/test_scp5370.py`, `src/tools/test_latex_compilation.py`
- Likely unused/legacy (not used by current pipeline/tests; kept as fallback): `src/parsers/wikidot_parser.py`, `src/latex/converter.py` (only referenced if you pass legacy docs to `EnhancedLaTeXConverter._generate_legacy_scp_section`)
- Package markers only: `src/__init__.py`, `src/web/__init__.py`, `src/parsers/__init__.py`, `src/pipeline/__init__.py`, `src/latex/__init__.py`, `src/tools/__init__.py`

**Dependencies**
- External libs used in runtime:
  - `requests`, `beautifulsoup4` -> `src/scp_downloader.py`
  - `flask` -> `src/web/app.py`
  - `pymupdf` (fitz), optional `pdf2image`, optional ImageMagick `convert`, optional `pdfinfo` -> `src/web/pdf_utils.py`
  - `pdflatex` CLI -> `src/pipeline/compile_latex.py`, `src/tools/test_latex_compilation.py`, `tests/test_latex_output.py`
- Test deps: `pytest` -> `tests/test_latex_output.py`

**Diagram**
```text
run_web.py
  -> web/app.py (Flask)
     /api/download -> scp_downloader.SCPDownloader -> output/downloads + output/raw_downloads
     /api/parse    -> parsers.enhanced_wikidot_parser -> output/intermediate/*.json
     /api/convert  -> latex.enhanced_converter -> output/latex/articles/*.tex
     /api/compile  -> pipeline.builder -> compile_latex_to_pdf -> output/pdf/scp_book.pdf
     /api/pdf/*    -> web/pdf_utils (fitz/pdf2image/convert)

pipeline/builder.py (CLI) -> same parse -> latex -> compile path
scp_downloader.py (CLI)   -> downloads only
```

If you want, I can:
1) Trim or archive the legacy parser/converter.
2) Add a README section that documents the "current" pipeline vs legacy paths.

Here's the delta between the "current" (enhanced) and legacy paths.

**Parser differences**
- Structure: legacy `WikidotParser` returns a flat `SCPDocument` with string sections (`containment_procedures`, `description`, `addenda`) and a loose `elements` list; enhanced `EnhancedWikidotParser` returns `EnhancedSCPDocument` with typed `SCPSection` and `ContentBlock` objects (semantic blocks for paragraphs, lists, quotes, tables, etc.). `src/parsers/wikidot_parser.py`, `src/parsers/enhanced_wikidot_parser.py`
- Semantics: enhanced explicitly detects quote blocks, dialogue lines, list/table blocks, include/module blocks, and adds attributes (e.g., dialogue speakers, quote types). Legacy mostly uses regex section extraction plus simple element parsing (includes/modules/footnotes/formatting). `src/parsers/enhanced_wikidot_parser.py`, `src/parsers/wikidot_parser.py`
- Output: enhanced JSON is nested and typed (blocks + attributes); legacy JSON is mostly flat text. `src/parsers/enhanced_wikidot_parser.py`, `src/parsers/wikidot_parser.py`

**Converter differences**
- Input model: legacy `LaTeXConverter` expects the flat `SCPDocument`; enhanced `EnhancedLaTeXConverter` expects `EnhancedSCPDocument` and iterates `sections -> content_blocks`. `src/latex/converter.py`, `src/latex/enhanced_converter.py`
- Formatting logic: enhanced handles dialogue with `scpdialogue`/`speaker`, quote blocks with `scpquote`, tables, lists, and include placeholders; legacy mainly converts bold/italic/footnotes, wraps bullet lists, and prints sections in a fixed order. `src/latex/enhanced_converter.py`, `src/latex/converter.py`
- Preamble: enhanced adds packages/environments for quotes/dialogue (`enumitem`, `changepage`, `framed`) and redaction boxes (`\\blackbox{}`); legacy has a simpler preamble and its RPG styling uses `fontspec/pgfornament` that the enhanced one doesn't. `src/latex/enhanced_converter.py`, `src/latex/converter.py`
- Fallback: enhanced converter will call legacy conversion only if it gets a legacy-style doc (no `sections`). `src/latex/enhanced_converter.py`

If you want, I can mark legacy-only modules in the repo or add a short doc section explaining this split.

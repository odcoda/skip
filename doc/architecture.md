## control flow
Orchestration script (`src/pipeline/builder.py`) should run all steps, filling missing dependencies, like a build system. By default, the flow proceeds as follows:
1. Download: `src/scp_downloader.py`
  -> `output/downloads/*.txt` (wikidot source)
  -> `output/raw_downloads/*.html` (full pages)
2. Parse:   `src/parsers/enhanced_wikidot_parser.py`
  -> `output/intermediate/*.json` (parsed json file content)
3. Convert:  `src/latex/enhanced_converter.py`  
  -> `output/latex/*.tex` 
4. Compile: `src/pipeline/compile_latex.py`
  -> `output/pdf/*.pdf`

## manual overrides and diffs
Each step of the flow has the potential for mistakes, incorrect parses, and idiosyncratic content errors. We are trying to produce an attractive book which may require some design alterations along the way. To avoid this and streamline the resulting build, there is also a `manual/` directory (parallel to the `output/` directory which is checked-in where the user can supply corrected files at any stage of the process; the builder should use these files if it finds them and skip running earlier steps of the build for these files. The build script will however generate relevant diffs of the output (automatic) and manual files in the `diffs/` directory for manual inspection (this directory is not checked in). Note that only txt and latex files should have diffs generated.

## tests
All scripts of the control flow have simple tests which feed in an input and compare the output with an expected output, except the downloader which hits an external endpoint. For the downloader we have a static html page and we just test the wikidot source extraction. The relevant tests are in `test/` and the corresponding input/output data are in `test/data/`. If a test output doesn’t match what’s expected, show the diff and save the actual output to a .corrected file; the user can easily run the accept-corrections.sh script to update the outputs to match the corrections.

## legacy files (to delete)
- Likely unused/legacy (not used by current pipeline/tests; kept as fallback): `src/parsers/wikidot_parser.py`, `src/latex/converter.py` (only referenced if you pass legacy docs to `EnhancedLaTeXConverter._generate_legacy_scp_section`)

## web launcher
- Web launcher: `src/run_web.py` -> `src/web/app.py`
  - `/api/download` -> `SCPDownloader`
  - `/api/parse` -> `EnhancedWikidotParser`
  - `/api/convert` -> `EnhancedLaTeXConverter`
  - `/api/compile` -> `SCPBookBuilder` -> `compile_latex_to_pdf`
  - `/api/pdf/*` -> `src/web/pdf_utils.py`

## legacy tests (to modernize)
- Tests (pytest): `tests/test_latex_output.py`, `tests/conftest.py`
 
- Manual test/analysis scripts: `src/test_downloader.py`, `src/tools/analyze_scp_patterns.py`, `src/tools/test_content_completeness.py`, `src/tools/test_scp5370.py`, `src/tools/test_latex_compilation.py`

## analysis and misc scripts



**Dependencies**
- External libs used in runtime:
  - `requests`, `beautifulsoup4` -> `src/scp_downloader.py`
  - `flask` -> `src/web/app.py`
  - `pymupdf` (fitz), optional `pdf2image`, optional ImageMagick `convert`, optional `pdfinfo` -> `src/web/pdf_utils.py`
  - `pdflatex` CLI -> `src/pipeline/compile_latex.py`, `src/tools/test_latex_compilation.py`, `tests/test_latex_output.py`
- Test deps: `pytest` -> `tests/test_latex_output.py`
## control flow
The main orchestration script (`src/pipeline/builder.py`) should run all steps, filling missing dependencies, to produce its main target, like a build system. By default, the flow proceeds as follows:
1. Download: `src/scp_downloader.py`
  -> `output/downloads/*.txt` (wikidot source)
  -> `output/raw_downloads/*.html` (full pages)
2. Parse:   `src/parsers/enhanced_wikidot_parser.py`
  -> `output/intermediate/*.json` (parsed json file content)
3. Convert:  `src/latex_pipeline/enhanced_converter.py`  
  -> `output/latex/*.tex` 
4. Compile: `src/latex_pipeline/compile_latex.py`
  -> `output/pdf/*.pdf`

## manual overrides and diffs
Each step of the flow has the potential for mistakes, incorrect parses, and idiosyncratic content errors. We are trying to produce an attractive book which may require some design and content alterations along the way. To avoid having to specify everything in code and still streamline the resulting build, there is also a `manual/` directory (parallel to the `output/` directory which is checked-in where the user can supply corrected files at any stage of the process; the builder should use these files if it finds them. The build script should however generate relevant diffs of the output (automatic) and manual files in the `diffs/` directory for manual inspection (this directory is not checked in). Note that only txt and latex files should have diffs generated.

## supplements and media
Some articles depend on other articles (supplements, logs, etc) or on media files (images, video, etc). To track this, part of the generated output should be an `output/deps` directory showing which other files are dependencies of this file. Use a simple yaml format for dependencies. The main builder should take this into account when building.

All media and other un-parsed downloaded assets should be saved to `output/assets/`.

Both of these types of generated output should also support manual overrides, similarly to the above overrides for the articles themselves, in the corresponding directories under `manual/`. Note that overriding deps will change which things the main orchestrator wants to download; that’s ok! (That’s the point of being able to override it).

## tests
All scripts of the control flow have simple tests which feed in an input and compare the output with an expected output, except the downloader which hits an external endpoint. For the downloader we have a static html page and we just test the wikidot source extraction. The relevant tests are in `test/` and the corresponding input/output data are in `test/data/`. If a test output doesn’t match what’s expected, show the diff and save the actual output to a .corrected file; the user can easily run the accept-corrections.sh script to update the outputs to match the corrections.

## legacy files (to delete)
- Likely unused/legacy (not used by current pipeline/tests; kept as fallback): `src/parsers/wikidot_parser.py`, `src/latex_pipeline/converter.py` (only referenced if you pass legacy docs to `EnhancedLaTeXConverter._generate_legacy_scp_section`)

## web launcher
- Web launcher: `src/run_web.py` -> `src/web/app.py`
  - `/api/download` -> `SCPDownloader`
  - `/api/parse` -> `EnhancedWikidotParser`
  - `/api/convert` -> `EnhancedLaTeXConverter`
  - `/api/compile` -> `SCPBookBuilder` -> `compile_latex_to_pdf`
  - `/api/pdf/*` -> `src/web/pdf_utils.py`

## legacy tests (to modernize)
- Tests (pytest): `tests/test_latex_output.py`, `tests/conftest.py`
 
- Manual test/analysis scripts (some of these should be in (research/): `src/test_downloader.py`, `src/tools/analyze_scp_patterns.py`, `src/tools/test_content_completeness.py`, `src/tools/test_scp5370.py`, `src/tools/test_latex_compilation.py`

## research (analysis and misc scripts)
Any one-off scripts or notebooks which do things like e.g. examine a subset of articles to look for patterns, search for extra information online, etc should be in the `research/` directory. Research code should be dated with when it was created e.g. `research/2025-01-01-analyze-images.py`. It’s fine to just write new research code instead of modifying existing code.


## external libraries
- External libs used in runtime:
  - `requests`, `beautifulsoup4` -> `src/scp_downloader.py`
  - `flask` -> `src/web/app.py`
  - `pymupdf` (fitz), optional `pdf2image`, optional ImageMagick `convert`, optional `pdfinfo` -> `src/web/pdf_utils.py`
  - `pdflatex` CLI -> `src/latex_pipeline/compile_latex.py`, `src/tools/test_latex_compilation.py`, `tests/test_latex_output.py`
- Test deps: `pytest` -> `tests/test_latex_output.py`
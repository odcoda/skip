# Development Log

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

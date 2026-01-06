# Development Log

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

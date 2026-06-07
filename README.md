# SCP Foundation Downloader and Book Builder

A Python tool to download SCP Foundation pages, inspect the raw HTML and wikidot source, parse them into structured JSON and Markdown previews, and optionally build PDF books through a separated LaTeX pipeline.

## Features

- **Download System**: Retrieve wikidot source for individual SCPs or ranges
- **Web Inspector**: Browse downloaded pages and preview raw HTML, wikidot source, parsed JSON, and scraped Markdown
- **Semantic Parser**: Enhanced parser that understands SCP structure (containment, description, addenda)
- **Dialogue Detection**: Automatically formats interview transcripts and dialogue
- **Quote Block Processing**: Handles nested formatting and experiment logs
- **Intermediate Format**: Structured JSON and readable Markdown representations for review
- **LaTeX Generation**: Creates individual LaTeX files plus a main book file
- **PDF Compilation**: Automated LaTeX compilation with proper error handling

## Project Structure

```
skip/
├── README.md                    # This file
├── CLAUDE.md                    # Development notes and progress
├── .gitignore                   # Git ignore patterns
├── GOALS.md                     # Project goals and requirements
├── manual/                      # Optional manual overrides (parallel to output/)
├── output/
│   ├── downloads/               # Downloaded wikidot source files (.txt)
│   ├── raw_downloads/           # Downloaded full page HTML files (.html)
│   ├── intermediate/            # Parsed JSON representations
│   ├── deps/                    # Dependency manifests (.yaml)
│   ├── assets/                  # Downloaded media and unparsed assets
│   ├── latex/
│   │   ├── articles/            # Individual LaTeX files
│   │   └── scp_book.tex         # Main book file with includes
│   └── pdf/                     # Final compiled PDFs
├── diffs/                       # Auto-vs-manual diffs for .txt/.tex (generated)
├── src/
│   ├── scp_downloader.py      # Core download functionality
│   ├── parsers/
│   │   ├── enhanced_wikidot_parser.py  # Semantic parser with dialogue detection
│   │   ├── markdown_renderer.py        # Parsed-document Markdown previews
│   │   └── wikidot_parser.py           # Basic parser (legacy)
│   ├── web/                    # Flask download/parse/preview interface
│   ├── latex_pipeline/         # Optional LaTeX/PDF generation functionality
│   │   ├── enhanced_converter.py       # LaTeX generator with semantic formatting
│   │   ├── compile_latex.py            # PDF compilation utilities
│   │   └── themes/                     # LaTeX theme packages and graphics
│   └── pipeline/
│       └── builder.py         # Main orchestration/build pipeline
├── research/                  # One-off analysis/manual scripts (dated)
└── test/
    ├── data/
    │   ├── input/            # Test inputs
    │   └── expected/         # Golden outputs
    ├── accept-corrections.sh # Promote *.corrected to expected outputs
    └── test_*.py             # Unit/integration tests
```

## Installation

```bash
# Clone the repository
git clone <repository-url>
cd skip

# Install Python dependencies
pip install requests beautifulsoup4 dataclasses

# Install LaTeX (required for PDF generation)
# On macOS with Homebrew:
brew install --cask mactex

# On Ubuntu/Debian:
sudo apt-get install texlive-full

# On Windows:
# Download and install MiKTeX or TeX Live
```

## Quick Start

### 1. Download SCPs

```bash
# Download a single SCP
python src/scp_downloader.py scp-173

# Download a range across multiple series
python src/scp_downloader.py 173 --range --end 182
python src/scp_downloader.py 1123 --range --end 1132
python src/scp_downloader.py 5360 --range --end 5370
```

### 2. Inspect Downloads in the Web View

```bash
uv run src/run_web.py
```

Open the printed local URL. The web view can download pages, parse them, list every downloaded slug (including related non-SCP pages), and preview raw HTML, wikidot source, parsed JSON, and rendered Markdown.

### 3. Build Complete Book

```bash
python src/pipeline/builder.py
```

This will:
1. Resolve missing pages (download + dependency closure)
2. Parse source files into `output/intermediate/*.json`
3. Generate dependency manifests in `output/deps/*.yaml`
4. Download media/unparsed assets to `output/assets/`
5. Generate LaTeX in `output/latex/` and compile PDFs in `output/pdf/`
6. If matching files exist under `manual/`, use those overrides and write diffs to `diffs/`

### 3. Build Volume 1 (Heritage Collection)

```bash
# Fast/stable default: only the 14 Heritage SCPs
uv run src/build_volume1.py

# Include dependency pages/logs too
uv run src/build_volume1.py --with-deps
```

Output paths:
- LaTeX: `output/latex/volume1/scp_book.tex`
- PDF: `output/pdf/volume1/scp_book.pdf`

## Advanced Usage

### Custom Configuration

```python
from pipeline.builder import SCPBookBuilder, PipelineConfig

config = PipelineConfig(
    output_dir='custom_output',
    input_dir='custom_output/downloads',
    title='My Custom SCP Collection',
    author='My Name',
    max_scps_per_chapter=5,
    resolve_dependencies=True,
    download_assets=True
)

builder = SCPBookBuilder(config)
builder.build_book()
```

### Individual Components

```python
# Parse specific files
documents = builder.parse_all_files(['output/downloads/scp-173.txt'])

# Generate only LaTeX without compilation
latex_files = builder.generate_individual_latex_files(documents)
chapters = builder.organize_into_chapters()
main_latex = builder.generate_latex(chapters, latex_files)

# Compile existing LaTeX to PDF
from latex_pipeline.compile_latex import compile_latex_to_pdf
success, pdf_path, error = compile_latex_to_pdf('output/latex/scp_book.tex')
```

### Content Analysis

```python
# Analyze SCP patterns and structure
python research/2026-02-25-analyze-scp-patterns.py

# Test content completeness
python research/2026-02-25-test-content-completeness.py
```

## Architecture

### Parser System

The enhanced parser (`enhanced_wikidot_parser.py`) provides:

- **Semantic Understanding**: Identifies containment procedures, descriptions, addenda
- **Content Typing**: Classifies blocks as paragraphs, lists, quotes, dialogue, tables
- **Dialogue Processing**: Extracts speaker names and stage directions
- **Quote Classification**: Distinguishes experiments, interviews, incident logs

### LaTeX Generation

The enhanced converter (`enhanced_converter.py`) features:

- **Modular Design**: Individual files + main book with includes
- **Semantic Formatting**: Custom environments for different content types
- **Dialogue Environments**: Properly formatted interview transcripts
- **Quote Block Styling**: Indented blocks with context-aware formatting
- **Escape Handling**: Proper LaTeX character escaping

### Build Pipeline

The main pipeline (`builder.py`) orchestrates:

1. **Discovery**: Find all SCP files in input directory
2. **Parsing**: Convert wikidot markup to structured format
3. **Organization**: Group SCPs into chapters by series
4. **Generation**: Create individual LaTeX files and main book
5. **Compilation**: Produce final PDF with error handling

## Output Formats

### Intermediate JSON
Structured representation with:
- SCP metadata (number, title, object class)
- Sectioned content (containment, description, addenda)
- Typed content blocks with attributes
- Include and module references

### Individual LaTeX Files
Clean, modular files containing:
- Section headers with SCP numbers
- Properly formatted content blocks
- Custom commands for SCP elements
- Comment annotations for debugging

### Main Book LaTeX
Professional book structure with:
- Document preamble and styling
- Table of contents
- Chapter organization by series
- Include statements for individual files

## Customization

### Adding New Content Types

1. Extend `ContentType` enum in `enhanced_wikidot_parser.py`
2. Add detection logic in parser methods
3. Implement LaTeX generation in `enhanced_converter.py`
4. Add custom LaTeX environments as needed

### Styling Modifications

- Edit preamble in `enhanced_converter.py`
- Modify color definitions and spacing
- Add new LaTeX packages for advanced features
- Enable RPG styling for fantasy appearance

### Parser Improvements

- Add new regex patterns for specific formatting
- Enhance dialogue detection algorithms
- Improve quote block classification
- Add support for new wikidot modules

## Troubleshooting

### LaTeX Compilation Issues

```bash
# Check for missing packages
pdflatex --version

# Manual compilation for debugging
cd output/latex
pdflatex scp_book.tex
```

### Content Parsing Problems

```bash
# Test individual file parsing
python -c "
from parsers.enhanced_wikidot_parser import EnhancedWikidotParser
parser = EnhancedWikidotParser()
doc = parser.parse_file('output/downloads/scp-173.txt')
print(f'Parsed {len(doc.sections)} sections')
"
```

### Download Issues

- Check internet connection
- Verify SCP numbers exist
- Increase delay between requests
- Check for rate limiting

## License

MIT License

## Disclaimer

This tool is for educational and archival purposes only. Please respect the SCP Foundation's terms of use and do not overload their servers with requests. Always include proper attribution when using content from the SCP Wiki.

## Contributing

When making changes:

1. Test with individual SCPs first
2. Verify LaTeX compilation works
3. Check content completeness with analysis tools
4. Update CLAUDE.md with development notes
5. Add tests for new functionality

For major architectural changes, see CLAUDE.md for detailed development context and progress notes.

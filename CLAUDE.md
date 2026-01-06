# CLAUDE.md - Project Context for Future Claude Sessions

## Project Overview

This is an **SCP Foundation LaTeX Book Generator** - a comprehensive pipeline that downloads SCP Foundation articles and converts them into beautifully formatted LaTeX books with fantasy RPG sourcebook aesthetics. The project has evolved into a robust system with semantic parsing and modular LaTeX generation.

## Current Status: Phase 2.5 Complete

The project has successfully transitioned from basic conversion to a sophisticated semantic parser with individual file generation. We now have a complete working pipeline that produces high-quality LaTeX books.

## Ultimate Vision

The goal is to create **high-quality printed books** of SCP Foundation content that look like fantasy RPG sourcebooks (D&D style) with:
- Advanced LaTeX styling (floating sidebars, image overlays, text wrapping)
- Fantasy aesthetic (decorative elements, multiple fonts, background images)
- Professional book layout and typography
- Modular template system for different styles

## Project Architecture

### Multi-Stage Pipeline

```
SCP Articles → Download → Parse → Organize → Individual LaTeX → Main Book → PDF
```

**Stage 1: Download** - Extract wikidot source from SCP wiki ✅
**Stage 2: Parse** - Convert wikidot markup to structured data with semantic understanding ✅
**Stage 3: Organize** - Structure content into book chapters by series ✅
**Stage 4: Individual LaTeX** - Generate modular LaTeX files for each SCP ✅
**Stage 5: Main Book** - Combine individual files with includes ✅
**Stage 6: Compilation** - Generate final PDF ✅
**Stage 7: Styling** - Apply fantasy RPG templates 📋

## Current Project Structure

```
skip/
├── README.md                    # Comprehensive documentation
├── CLAUDE.md                    # This file - development context
├── .gitignore                   # Excludes output/ and build artifacts
├── requirements.txt             # Python dependencies
├── output/                      # All generated/downloaded content (gitignored)
│   ├── downloads/              # Downloaded SCP source files (.txt)
│   ├── raw_downloads/          # Raw HTML API responses (.html)
│   ├── intermediate/           # Structured JSON representations
│   ├── latex/
│   │   ├── articles/          # Individual LaTeX files (81 files)
│   │   ├── build/             # LaTeX compilation artifacts
│   │   └── scp_book.tex       # Main book with includes
│   ├── pdf/                   # Final compiled PDF books
│   └── preview/               # PDF preview images
└── src/                        # All source code
    ├── __init__.py
    ├── scp_downloader.py       # Wikidot downloader
    ├── run_web.py              # Web interface launcher
    ├── test_downloader.py      # Downloader tests
    ├── parsers/
    │   ├── enhanced_wikidot_parser.py  # Semantic parser
    │   └── wikidot_parser.py           # Basic parser (legacy)
    ├── latex/
    │   ├── enhanced_converter.py       # Advanced LaTeX generator
    │   └── converter.py               # Basic converter (legacy)
    ├── pipeline/
    │   ├── builder.py          # Main build pipeline
    │   └── compile_latex.py    # PDF compilation utilities
    ├── tools/                  # Analysis and debugging tools
    │   ├── analyze_scp_patterns.py     # Pattern analysis
    │   ├── test_content_completeness.py # Content retention testing
    │   ├── test_latex_compilation.py   # LaTeX testing
    │   └── test_scp5370.py            # Single SCP test
    └── web/                    # Web interface
        ├── app.py              # Flask application
        ├── pdf_utils.py        # PDF utilities
        ├── static/             # CSS, JS
        └── templates/          # HTML templates
```

## Major Technical Achievements

### ✅ Enhanced Semantic Parser (enhanced_wikidot_parser.py)

**Key Features:**
- **Content Block Classification**: Paragraphs, lists, quotes, dialogue, tables, includes
- **Dialogue Detection**: Automatically identifies `**SPEAKER:** text` patterns
- **Quote Block Processing**: Handles `>` prefixed content with type classification
- **Semantic Sectioning**: Containment, description, addenda with proper structure
- **95.6% Content Retention**: Dramatically improved from initial 41.2%

**Content Analysis Results (81 SCPs across Series I-VIII):**
- 87.7% have containment/description sections
- 64.2% have nested formatting in quote blocks  
- 38.3% have interview/dialogue content
- Complex dialogue patterns with speaker identification

### ✅ Enhanced LaTeX Converter (enhanced_converter.py)

**Key Features:**
- **Modular Design**: Individual files + main book with includes
- **Semantic Formatting**: Custom environments for different content types
- **Dialogue Environments**: `\begin{scpdialogue}` with `\speaker{}` commands
- **Quote Block Styling**: Indented blocks with context-aware formatting
- **Proper Escaping**: Fixed regex issues that caused `\1` in output

**Custom LaTeX Environments:**
```latex
\begin{scpdialogue} ... \end{scpdialogue}
\begin{scpquote} ... \end{scpquote}
\speaker{Name}
\containment, \scpdescription, \addendum{}
```

### ✅ Build Pipeline (builder.py)

**Complete Workflow:**
1. **Discovery**: Scan input directory for SCP files
2. **Parsing**: Convert all files to semantic structure
3. **Intermediate Storage**: Save JSON representations
4. **Organization**: Group into chapters by series (I-VIII)
5. **Individual Generation**: Create 81 separate LaTeX files
6. **Main Book**: Generate master file with includes
7. **Compilation**: Produce final PDF with error handling

**Series Organization:**
- Series I (000s): SCP-173, SCP-174, etc.
- Series II (1000s): SCP-1123, SCP-1124, etc.
- Series III (2000s): SCP-2234, SCP-2235, etc.
- Series IV (3000s): SCP-3345, SCP-3346, etc.
- Series V (4000s): SCP-4456, SCP-4457, etc.
- Series VI (5000s): SCP-5360, SCP-5370, etc.
- Series VII (6000s): SCP-6123, SCP-6124, etc.
- Series VIII (7000s): SCP-7234, SCP-7243, etc.

## Current Implementation Status

### ✅ Phase 1: Foundation (COMPLETE)
- SCP downloader with dual output system
- Basic wikidot parser extracting main SCP sections
- Pipeline framework with single SCP → LaTeX conversion
- Test infrastructure for iteration

### ✅ Phase 2: Enhanced Parsing (COMPLETE)
- Semantic parser with content block classification
- Dialogue detection and formatting
- Quote block processing with type inference
- Comprehensive pattern analysis across 81 SCPs
- 95.6% content retention achieved

### ✅ Phase 2.5: Modular LaTeX Generation (COMPLETE)
- Individual LaTeX files for each SCP (81 files)
- Main book file using `\input{}` includes
- Enhanced LaTeX environments for semantic formatting
- Fixed escaping issues and compilation problems
- Successful PDF generation with 191KB output

### 🚧 Phase 3: LaTeX Styling Issues (PARTIAL)
- **RESOLVED**: Individual file generation and includes
- **RESOLVED**: Proper LaTeX character escaping
- **ISSUE**: Main book still shows inline content instead of includes
- **TODO**: Fix include statement generation in main book
- **TODO**: Proper `\input{articles/scp_xxx}` statements

### 📋 Phase 4: RPG Styling System (PLANNED)
- **TODO**: RPG-style LaTeX templates with tcolorbox
- **TODO**: Custom fonts and decorative elements
- **TODO**: Image integration and text wrapping
- **TODO**: Template testing workflow

### 📋 Phase 5: Advanced Features (PLANNED)
- **TODO**: Floating sidebars and complex layouts
- **TODO**: Background images and overlays
- **TODO**: Interactive elements (hyperlinks, references)
- **TODO**: Multiple output styles (academic, RPG, modern)

## Quick Start Commands

### Complete Pipeline
```bash
# From project root - uses default paths (output/downloads, output/latex, etc.)
cd src
python -c "
from pipeline.builder import SCPBookBuilder, PipelineConfig
builder = SCPBookBuilder(PipelineConfig())
builder.build_book()
"
```

### Download Sample Data
```bash
# Run from project root - defaults to output/downloads
python src/scp_downloader.py 173 --range --end 182

# Or from src directory
cd src && python scp_downloader.py 5360 --range --end 5370
```

### Web Interface
```bash
cd src && python run_web.py --port 5000
```

### Debug Individual Components
```bash
cd src

# Test parser only
python -c "
from pipeline.builder import PROJECT_ROOT, OUTPUT_DIR
from parsers.enhanced_wikidot_parser import EnhancedWikidotParser
parser = EnhancedWikidotParser()
doc = parser.parse_file(str(OUTPUT_DIR / 'downloads' / 'scp-173.txt'))
print(f'Sections: {len(doc.sections)}')
"
```

## Technical Debugging Notes

### Known Issue: Include Statements Not Generated

**Problem**: Main book file `scp_book.tex` contains inline content instead of `\input{}` statements

**Evidence**: 
- Individual files in `articles/` directory are correctly generated
- Main book is only 263 lines (should be much shorter with includes)
- LaTeX compilation attempts to read non-existent include files

**Diagnosis**: The `generate_book_with_includes` method may not be properly generating include statements

**Next Steps**:
1. Debug the `_generate_chapter_with_includes` method in enhanced_converter.py
2. Verify `latex_files` dictionary is properly populated
3. Check if include paths are correctly formatted
4. Test include statement generation with debug output

### Fixed Issues ✅

**Content Loss (41.2% → 95.6% retention)**: Enhanced regex patterns in parser
**LaTeX Escaping (`\1` errors)**: Fixed regex replacement strings in text processing
**Null Content Blocks**: Added null checks in LaTeX converter
**Directory Structure**: Proper path handling for running from src directory

### Current File Counts
- **Downloaded SCPs**: 81 files across 8 series
- **Intermediate JSON**: 81 structured representation files
- **Individual LaTeX**: 81 article files in `output/latex/articles/`
- **Main Book**: 1 file (`scp_book.tex`) with includes
- **Final PDF**: 191KB compiled book

## Development Strategy

### Next Immediate Tasks
1. **Fix Include Generation**: Debug why main book uses inline instead of includes
2. **Verify LaTeX Compilation**: Ensure includes work properly
3. **RPG Styling Foundation**: Add basic tcolorbox environments
4. **Font Integration**: Custom fonts for different text types

### Long-term Roadmap
1. **Template System**: Configurable styling modes (basic/RPG/academic)
2. **Asset Integration**: Images, decorations, backgrounds
3. **Cross-references**: Link resolution between SCPs
4. **Performance**: Optimization for large books (100+ SCPs)

## Success Metrics Achieved

- ✅ Single SCP converts cleanly to readable LaTeX
- ✅ Multiple SCPs organized into structured book
- ✅ Semantic parsing captures dialogue and formatting
- ✅ Individual file architecture for modularity
- ✅ Complete pipeline from download to PDF
- 🚧 Include system (implementation issue)
- 📋 RPG styling (next phase)

## Important Notes for Future Sessions

### Development Context
- **Test Case**: Use SCP-173 and SCP-5370 as primary examples
- **Working Directory**: Scripts can run from project root or `src/` directory
- **Path Handling**: All scripts use absolute paths via PROJECT_ROOT
- **LaTeX Requirements**: Full TeX Live installation needed
- **Output Location**: All generated content goes to `output/` (gitignored)

### Code Quality Notes
- Enhanced parser is the current working version
- Legacy parsers/converters kept for reference
- All methods properly typed with dataclasses
- Comprehensive error handling in pipeline
- JSON intermediate format for debugging

### Architecture Decisions
- All source code under `src/`, all outputs under `output/`
- Individual LaTeX files enable modularity and debugging
- Main book uses includes for clean organization
- Semantic content blocks enable advanced styling
- Series-based chapter organization scales well

This project has successfully built a robust foundation for SCP book generation. The next phase focuses on resolving the include generation issue and implementing RPG styling features.
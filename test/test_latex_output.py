#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "pytest>=7.0",
# ]
# ///
"""
Tests for LaTeX output generation and compilation.

Test types:
1. Diff test: Parse input files, convert to LaTeX, compare against expected output
2. Individual compilation: Check that each generated LaTeX file compiles with pdflatex
3. Book compilation: Check that a book composed of multiple files compiles
"""
import subprocess
import difflib
from pathlib import Path

import pytest


def assert_matches_expected(actual_latex: str, expected_file: Path, label: str):
    """Compare output with expected text and emit .corrected files on mismatch."""
    expected_latex = expected_file.read_text(encoding='utf-8')
    if actual_latex == expected_latex:
        return

    corrected_file = expected_file.with_suffix(expected_file.suffix + ".corrected")
    corrected_file.write_text(actual_latex, encoding='utf-8')

    diff = ''.join(
        difflib.unified_diff(
            expected_latex.splitlines(keepends=True),
            actual_latex.splitlines(keepends=True),
            fromfile=str(expected_file),
            tofile=str(corrected_file),
        )
    )
    pytest.fail(
        f"\nLaTeX output mismatch for {label}\n"
        f"Saved corrected output to: {corrected_file}\n"
        f"{'=' * 60}\n{diff}\n{'=' * 60}"
    )


class TestLatexDiff:
    """Test that generated LaTeX matches expected output."""

    def test_latex_output_matches_expected(self, fixtures_dir, expected_dir, parser, converter):
        """
        Parse each test file, convert to LaTeX, and diff against expected.

        This test will fail if any differences are found, printing a unified diff.
        """
        test_files = sorted(fixtures_dir.glob("scp-test-*.txt"))

        for test_file in test_files:
            # Parse the input file
            doc = parser.parse_file(str(test_file))

            # Generate LaTeX
            actual_latex = converter.generate_document_latex(doc)

            # Load expected output
            expected_file = expected_dir / f"{test_file.stem}.tex"

            if not expected_file.exists():
                pytest.skip(f"Expected file {expected_file} not found. Run 'pytest --generate-expected' to create it.")

            assert_matches_expected(actual_latex, expected_file, test_file.name)

    @pytest.mark.parametrize("fixture_name", [
        "scp-test-001",
        "scp-test-002",
        "scp-test-003",
        "scp-test-004",
    ])
    def test_individual_file_diff(self, fixture_name, fixtures_dir, expected_dir, parser, converter):
        """Test each fixture file individually for better isolation."""
        test_file = fixtures_dir / f"{fixture_name}.txt"
        expected_file = expected_dir / f"{fixture_name}.tex"

        if not test_file.exists():
            pytest.skip(f"Fixture {test_file} not found")

        if not expected_file.exists():
            pytest.skip(f"Expected file {expected_file} not found")

        # Parse and convert
        doc = parser.parse_file(str(test_file))
        actual_latex = converter.generate_document_latex(doc)

        assert_matches_expected(actual_latex, expected_file, fixture_name)


class TestLatexCompilation:
    """Test that generated LaTeX compiles successfully."""

    def _check_pdflatex_available(self):
        """Check if pdflatex is available on the system."""
        try:
            result = subprocess.run(
                ['pdflatex', '--version'],
                capture_output=True,
                text=True
            )
            return result.returncode == 0
        except FileNotFoundError:
            return False

    def _compile_latex(self, latex_content: str, build_dir: Path, filename: str = "test.tex") -> tuple[bool, str]:
        """
        Compile LaTeX content and return (success, error_message).
        """
        tex_file = build_dir / filename

        # Write LaTeX file
        with open(tex_file, 'w', encoding='utf-8') as f:
            f.write(latex_content)

        # Run pdflatex (twice for references)
        for _ in range(2):
            result = subprocess.run(
                ['pdflatex', '-interaction=nonstopmode', '-halt-on-error', filename],
                cwd=build_dir,
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.returncode != 0:
                # Extract relevant error lines from log
                log_file = build_dir / filename.replace('.tex', '.log')
                error_lines = []
                if log_file.exists():
                    with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                        log_content = f.read()
                        # Find error lines
                        for line in log_content.split('\n'):
                            if line.startswith('!') or 'Error' in line:
                                error_lines.append(line)

                error_msg = '\n'.join(error_lines[:10]) if error_lines else result.stdout[-2000:]
                return False, error_msg

        # Check PDF was created
        pdf_file = build_dir / filename.replace('.tex', '.pdf')
        if pdf_file.exists():
            return True, ""
        else:
            return False, "PDF file was not created"

    def _wrap_as_document(self, article_latex: str) -> str:
        """Wrap article LaTeX in a minimal document for compilation testing."""
        return f"""\\documentclass[12pt]{{article}}
\\usepackage[utf8]{{inputenc}}
\\usepackage[T1]{{fontenc}}
\\usepackage{{geometry}}
\\usepackage{{hyperref}}

% Custom commands used by the converter
\\newcommand{{\\scpnumber}}[1]{{\\section*{{#1}}}}
\\newcommand{{\\objectclass}}[1]{{\\textbf{{Object Class:}} #1\\par}}
\\newcommand{{\\containment}}{{\\subsection*{{Special Containment Procedures}}}}
\\newcommand{{\\scpdescription}}{{\\subsection*{{Description}}}}
\\newcommand{{\\addendum}}[1]{{\\subsection*{{#1}}}}
\\newenvironment{{scpdialogue}}{{\\begin{{quote}}\\itshape}}{{\\end{{quote}}}}
\\newenvironment{{scpquote}}{{\\begin{{quote}}}}{{\\end{{quote}}}}
\\newcommand{{\\speaker}}[1]{{\\textbf{{#1:}} }}
\\newcommand{{\\logheader}}[1]{{\\textbf{{#1}}\\par}}
\\newcommand{{\\blackbox}}{{\\rule{{1ex}}{{1.2ex}}}}
\\newcommand{{\\redact}}[1]{{\\rule{{#1ex}}{{1.2ex}}}}

\\begin{{document}}

{article_latex}

\\end{{document}}
"""

    @pytest.mark.parametrize("fixture_name", [
        "scp-test-001",
        "scp-test-002",
        "scp-test-003",
        "scp-test-004",
    ])
    def test_individual_compilation(self, fixture_name, fixtures_dir, parser, converter, test_output_dir):
        """Test that each individual article compiles successfully."""
        if not self._check_pdflatex_available():
            pytest.skip("pdflatex not available")

        test_file = fixtures_dir / f"{fixture_name}.txt"
        if not test_file.exists():
            pytest.skip(f"Fixture {test_file} not found")

        # Parse and convert
        doc = parser.parse_file(str(test_file))
        article_latex = converter.generate_document_latex(doc)

        # Wrap in document
        full_latex = self._wrap_as_document(article_latex)

        # Compile (output saved to test/output/ for inspection)
        success, error = self._compile_latex(full_latex, test_output_dir, f"{fixture_name}.tex")

        if not success:
            pytest.fail(f"LaTeX compilation failed for {fixture_name}:\n{error}")


class TestBookCompilation:
    """Test that a complete book with multiple articles compiles."""

    def _check_pdflatex_available(self):
        """Check if pdflatex is available on the system."""
        try:
            result = subprocess.run(
                ['pdflatex', '--version'],
                capture_output=True,
                text=True
            )
            return result.returncode == 0
        except FileNotFoundError:
            return False

    def test_book_compilation(self, fixtures_dir, parser, test_output_dir):
        """Test that a book composed of multiple test articles compiles."""
        if not self._check_pdflatex_available():
            pytest.skip("pdflatex not available")

        from latex.enhanced_converter import EnhancedLaTeXConverter
        from pipeline.builder import PipelineConfig

        # Parse all test files
        test_files = sorted(fixtures_dir.glob("scp-test-*.txt"))
        if not test_files:
            pytest.skip("No test fixtures found")

        documents = []
        for test_file in test_files:
            doc = parser.parse_file(str(test_file))
            documents.append(doc)

        # Create config pointing to test output dir
        book_dir = test_output_dir / "book"
        book_dir.mkdir(exist_ok=True)

        config = PipelineConfig(
            latex_dir=str(book_dir),
            title="Test SCP Book",
            subtitle="Test Collection"
        )
        converter = EnhancedLaTeXConverter(config)

        # Copy theme assets required by generated preamble.
        themes_src = Path(__file__).parent.parent / "src" / "latex" / "themes"
        for sty in themes_src.glob("*.sty"):
            target = book_dir / sty.name
            target.write_text(sty.read_text(encoding='utf-8'), encoding='utf-8')

        graphics_src = themes_src / "graphics"
        graphics_dst = book_dir / "graphics"
        if graphics_src.exists():
            graphics_dst.mkdir(exist_ok=True)
            for tex_file in graphics_src.glob("*.tex"):
                target = graphics_dst / tex_file.name
                target.write_text(tex_file.read_text(encoding='utf-8'), encoding='utf-8')

        # Create articles directory
        articles_dir = book_dir / "articles"
        articles_dir.mkdir(exist_ok=True)

        # Generate individual article files
        latex_files = {}
        for doc in documents:
            article_latex = converter.generate_document_latex(doc)
            filename = f"{doc.scp_number.lower().replace('-', '_')}.tex"
            filepath = articles_dir / filename
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(article_latex)
            latex_files[doc.scp_number] = f"articles/{filename}"

        # Generate main book
        chapters = [{
            'title': 'Test Articles',
            'documents': documents,
            'series': 0
        }]
        book_latex = converter.generate_book_with_includes(chapters, latex_files)

        # Write main book file
        book_file = book_dir / "test_book.tex"
        with open(book_file, 'w', encoding='utf-8') as f:
            f.write(book_latex)

        # Compile (run twice for ToC) - output saved to test/output/book/ for inspection
        for run in range(2):
            result = subprocess.run(
                ['pdflatex', '-interaction=nonstopmode', '-halt-on-error', 'test_book.tex'],
                cwd=book_dir,
                capture_output=True,
                text=True,
                timeout=120
            )

            if result.returncode != 0:
                # Extract error info
                log_file = book_dir / "test_book.log"
                error_lines = []
                if log_file.exists():
                    with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                        for line in f:
                            if line.startswith('!') or 'Error' in line:
                                error_lines.append(line.strip())

                error_msg = '\n'.join(error_lines[:15]) if error_lines else result.stdout[-2000:]
                pytest.fail(f"Book compilation failed (run {run + 1}):\n{error_msg}")

        # Verify PDF was created
        pdf_file = book_dir / "test_book.pdf"
        assert pdf_file.exists(), "Book PDF was not created"
        assert pdf_file.stat().st_size > 0, "Book PDF is empty"


# Utility function to generate expected files (run with pytest --generate-expected)
def generate_expected_files():
    """Generate expected LaTeX output files from current converter."""
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

    from parsers.enhanced_wikidot_parser import EnhancedWikidotParser
    from latex.enhanced_converter import EnhancedLaTeXConverter
    from pipeline.builder import PipelineConfig

    fixtures_dir = Path(__file__).parent / "data" / "input"
    expected_dir = Path(__file__).parent / "data" / "expected"
    expected_dir.mkdir(exist_ok=True)

    parser = EnhancedWikidotParser()
    converter = EnhancedLaTeXConverter(PipelineConfig())

    for test_file in sorted(fixtures_dir.glob("scp-test-*.txt")):
        print(f"Processing {test_file.name}...")

        doc = parser.parse_file(str(test_file))
        latex = converter.generate_document_latex(doc)

        output_file = expected_dir / f"{test_file.stem}.tex"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(latex)

        print(f"  -> {output_file}")

    print("\nExpected files generated. Please review them before committing.")


if __name__ == "__main__":
    # Allow running as script to generate expected files
    generate_expected_files()

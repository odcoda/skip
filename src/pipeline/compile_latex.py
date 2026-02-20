#!/usr/bin/env python3
"""
LaTeX Compilation Module

Handles compilation of LaTeX files with proper directory organization.
Keeps build artifacts separate from source and final PDFs.
"""

import os
import subprocess
import shutil
from pathlib import Path

# Theme directory (src/latex/themes)
THEMES_DIR = Path(__file__).parent.parent / "latex" / "themes"


def compile_latex_to_pdf(latex_file, output_pdf_dir=None, build_dir=None, themes_dir=None):
    """
    Compile LaTeX file to PDF with organized directory structure.
    
    Args:
        latex_file: Path to the .tex file
        output_pdf_dir: Directory for final PDF (default: output/pdf)
        build_dir: Directory for build artifacts (default: output/latex/build)
        
    Returns:
        Tuple of (success, pdf_path, error_message)
    """
    
    if not os.path.exists(latex_file):
        return False, None, f"LaTeX file not found: {latex_file}"
    
    # Set up directories
    latex_dir = os.path.dirname(os.path.abspath(latex_file))
    latex_filename = os.path.basename(latex_file)
    
    # Default directories
    if build_dir is None:
        build_dir = os.path.join(latex_dir, 'build')
    if output_pdf_dir is None:
        base_dir = Path(latex_file).parent.parent.parent
        output_pdf_dir = base_dir / "output" / "pdf"
    
    # Create directories
    os.makedirs(build_dir, exist_ok=True)
    os.makedirs(output_pdf_dir, exist_ok=True)
    
    # Build TEXINPUTS so pdflatex can find theme .sty files
    if themes_dir is None:
        themes_dir = str(THEMES_DIR)
    env = os.environ.copy()
    # TEXINPUTS: latex_dir (for main .tex), themes_dir (for .sty), then defaults
    env["TEXINPUTS"] = f"{latex_dir}:{themes_dir}:{env.get('TEXINPUTS', '')}"

    try:
        # Run pdflatex twice for proper TOC generation
        # First pass generates .aux file with TOC entries
        # Second pass uses .aux file to populate TOC
        for pass_num in range(2):
            result = subprocess.run([
                'pdflatex',
                '-interaction=nonstopmode',
                f'-output-directory={build_dir}',
                latex_filename
            ],
                cwd=latex_dir,
                capture_output=True,
                text=True,
                timeout=120,  # 2 minute timeout
                env=env
            )

            if result.returncode != 0:
                return False, None, f"LaTeX compilation failed (pass {pass_num + 1}):\n{result.stdout}\n{result.stderr}"
        
        # Move PDF to final location
        pdf_file = latex_filename.replace('.tex', '.pdf')
        build_pdf_path = os.path.join(build_dir, pdf_file)
        final_pdf_path = os.path.join(output_pdf_dir, pdf_file)
        
        if os.path.exists(build_pdf_path):
            shutil.move(build_pdf_path, final_pdf_path)
            return True, final_pdf_path, None
        else:
            return False, None, "PDF was not generated"
        
    except subprocess.TimeoutExpired:
        return False, None, "LaTeX compilation timed out"
    
    except FileNotFoundError:
        return False, None, "pdflatex not found. Please install a LaTeX distribution."
    
    except Exception as e:
        return False, None, f"Unexpected error: {e}"


def clean_build_artifacts(build_dir):
    """Clean up build artifacts directory"""
    if os.path.exists(build_dir):
        shutil.rmtree(build_dir)
        print(f"Cleaned build directory: {build_dir}")


def main():
    """Test the compilation function"""
    import sys
    
    if len(sys.argv) != 2:
        print("Usage: python compile_latex.py <tex_file>")
        sys.exit(1)
    
    latex_file = sys.argv[1]
    success, pdf_path, error = compile_latex_to_pdf(latex_file)
    
    if success:
        print(f"✅ Compilation successful!")
        print(f"PDF created: {pdf_path}")
        pdf_size = os.path.getsize(pdf_path)
        print(f"Size: {pdf_size:,} bytes")
    else:
        print(f"❌ Compilation failed!")
        print(f"Error: {error}")
        sys.exit(1)


if __name__ == "__main__":
    main()
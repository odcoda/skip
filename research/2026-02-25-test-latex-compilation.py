#!/usr/bin/env python3
"""
LaTeX Compilation Test Script

This script tests whether the generated LaTeX file compiles successfully
and provides detailed error reporting for debugging.
"""

import subprocess
import os
import sys
from pathlib import Path


def test_latex_compilation(latex_file):
    """Test LaTeX compilation and return results"""
    
    if not os.path.exists(latex_file):
        return False, f"LaTeX file not found: {latex_file}"
    
    # Set up directories
    latex_dir = os.path.dirname(os.path.abspath(latex_file))
    latex_filename = os.path.basename(latex_file)
    
    # Create build directory for auxiliary files
    build_dir = os.path.join(latex_dir, 'build')
    os.makedirs(build_dir, exist_ok=True)
    
    # Create PDF output directory
    base_dir = Path(latex_file).parent.parent  # Go up to project root
    pdf_dir = base_dir / "output" / "pdf"
    os.makedirs(pdf_dir, exist_ok=True)
    
    print(f"Testing LaTeX compilation...")
    print(f"Source: {latex_dir}/{latex_filename}")
    print(f"Build dir: {build_dir}")
    print(f"PDF dir: {pdf_dir}")
    
    try:
        # Run pdflatex with output directory specified
        result = subprocess.run([
            'pdflatex', 
            '-interaction=nonstopmode',
            f'-output-directory={build_dir}',
            latex_filename
        ],
            cwd=latex_dir,
            capture_output=True,
            text=True,
            timeout=60  # 60 second timeout
        )
        
        success = result.returncode == 0
        
        # Check for PDF output in build directory
        pdf_file = latex_filename.replace('.tex', '.pdf')
        build_pdf_path = os.path.join(build_dir, pdf_file)
        final_pdf_path = os.path.join(pdf_dir, pdf_file)
        
        pdf_created = False
        if success and os.path.exists(build_pdf_path):
            # Move PDF to final location
            import shutil
            shutil.move(build_pdf_path, final_pdf_path)
            pdf_created = True
            print(f"   PDF moved to: {final_pdf_path}")
        
        # List auxiliary files that stayed in build directory
        if os.path.exists(build_dir):
            aux_files = [f for f in os.listdir(build_dir) if f.startswith(latex_filename.replace('.tex', ''))]
            if aux_files:
                print(f"   Build artifacts in {build_dir}: {', '.join(aux_files)}")
        
        return success, {
            'returncode': result.returncode,
            'stdout': result.stdout,
            'stderr': result.stderr,
            'pdf_created': pdf_created,
            'pdf_path': final_pdf_path if pdf_created else None,
            'build_dir': build_dir
        }
        
    except subprocess.TimeoutExpired:
        return False, "LaTeX compilation timed out after 60 seconds"
    
    except FileNotFoundError:
        return False, "pdflatex not found. Please install a LaTeX distribution (TeX Live, MiKTeX, etc.)"
    
    except Exception as e:
        return False, f"Unexpected error: {e}"


def analyze_latex_errors(compilation_output):
    """Analyze LaTeX output for common errors"""
    
    if isinstance(compilation_output, str):
        return [compilation_output]
    
    stdout = compilation_output.get('stdout', '')
    stderr = compilation_output.get('stderr', '')
    
    errors = []
    warnings = []
    
    # Common LaTeX error patterns
    error_patterns = [
        ('Undefined control sequence', 'Unknown LaTeX command'),
        ('Missing } inserted', 'Unmatched braces'),
        ('Runaway argument', 'Unmatched braces or missing command end'),
        ('Package', 'Package error'),
        ('! Emergency stop', 'Critical error'),
        ('File ended while scanning', 'Unmatched braces or environments'),
        ('Missing $ inserted', 'Math mode error'),
    ]
    
    warning_patterns = [
        ('Overfull \\hbox', 'Text overflow (cosmetic)'),
        ('Underfull \\hbox', 'Text spacing issue (cosmetic)'),
        ('Package', 'Package warning'),
    ]
    
    # Scan for errors
    for line in stdout.split('\n'):
        line = line.strip()
        if line.startswith('!'):
            errors.append(line)
        else:
            for pattern, description in error_patterns:
                if pattern in line:
                    errors.append(f"{description}: {line}")
                    break
            
            for pattern, description in warning_patterns:
                if pattern in line and '!' not in line:
                    warnings.append(f"{description}: {line}")
                    break
    
    return errors, warnings


def main():
    """Main test function"""
    
    # Find the LaTeX file
    base_dir = Path(__file__).parent.parent  # Go up to project root
    latex_file = base_dir / "output" / "latex" / "scp_book.tex"
    
    print("=== LaTeX Compilation Test ===")
    print(f"Testing file: {latex_file}")
    
    # Test compilation
    success, result = test_latex_compilation(str(latex_file))
    
    if success:
        print("✅ LaTeX compilation SUCCESSFUL!")
        if result['pdf_created']:
            print(f"✅ PDF created: {result['pdf_path']}")
            
            # Get file size
            pdf_size = os.path.getsize(result['pdf_path'])
            print(f"   PDF size: {pdf_size:,} bytes")
        else:
            print("⚠️  PDF file not found despite successful compilation")
    else:
        print("❌ LaTeX compilation FAILED!")
        
        # Analyze errors
        if isinstance(result, dict):
            errors, warnings = analyze_latex_errors(result)
            
            print(f"\nReturn code: {result['returncode']}")
            
            if errors:
                print(f"\n🔥 Errors found ({len(errors)}):")
                for i, error in enumerate(errors[:5], 1):  # Show first 5 errors
                    print(f"   {i}. {error}")
                if len(errors) > 5:
                    print(f"   ... and {len(errors) - 5} more errors")
            
            if warnings:
                print(f"\n⚠️  Warnings found ({len(warnings)}):")
                for i, warning in enumerate(warnings[:3], 1):  # Show first 3 warnings
                    print(f"   {i}. {warning}")
                if len(warnings) > 3:
                    print(f"   ... and {len(warnings) - 3} more warnings")
            
            # Show last few lines of output for context
            if result['stdout']:
                lines = result['stdout'].strip().split('\n')
                if len(lines) > 10:
                    print(f"\nLast few lines of output:")
                    for line in lines[-10:]:
                        if line.strip():
                            print(f"   {line}")
        else:
            print(f"Error: {result}")
    
    print(f"\n=== Test Complete ===")
    return success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

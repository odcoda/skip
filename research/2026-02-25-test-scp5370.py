#!/usr/bin/env python3
"""
Test Script: Single SCP to LaTeX

This script demonstrates the pipeline by converting a single SCP file
(SCP-5370) to LaTeX format. Useful for testing and iteration.
"""

import sys
import os
from pathlib import Path

# Add src to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from pipeline.builder import SCPBookBuilder, PipelineConfig

OUTPUT_DIR = PROJECT_ROOT / "output"


def test_scp5370():
    """Test converting SCP-5370 to LaTeX"""

    # Configure for single SCP test (use defaults which point to output/)
    config = PipelineConfig(
        title="SCP-5370 Test Document",
        use_rpg_styling=False  # Start with basic styling
    )

    # Find SCP-5370 file
    scp_file = str(OUTPUT_DIR / "downloads" / "scp-5370.txt")
    
    if not os.path.exists(scp_file):
        print(f"Error: {scp_file} not found!")
        print(f"Please ensure SCP-5370 has been downloaded to {config.input_dir}")
        return False
    
    print("=== SCP-5370 LaTeX Test ===")
    print(f"Input file: {scp_file}")
    
    # Build book with single file
    builder = SCPBookBuilder(config)
    latex_file = builder.build_book([scp_file])
    
    print(f"\n=== Test Complete ===")
    print(f"Generated: {latex_file}")
    print(f"To view: cat '{latex_file}'")
    print(f"To compile: cd {os.path.dirname(latex_file)} && pdflatex {os.path.basename(latex_file)}")
    
    return True


def main():
    """Run the test"""
    success = test_scp5370()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

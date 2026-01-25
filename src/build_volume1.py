#!/usr/bin/env python3
"""
Build Volume 1: Heritage Collection

This script builds Volume 1 of the SCP book using the Heritage Collection
articles - the 14 most iconic SCPs inducted in 2013.

Heritage Collection SCPs:
- SCP-055: [Unknown]
- SCP-076: "Able"
- SCP-087: The Stairwell
- SCP-093: Red Sea Object
- SCP-173: The Sculpture
- SCP-231: Special Personnel Requirements
- SCP-239: The Witch Child
- SCP-343: "God"
- SCP-500: Panacea
- SCP-682: Hard-to-Destroy Reptile
- SCP-701: The Hanged King's Tragedy
- SCP-882: A Machine
- SCP-914: The Clockworks
- SCP-963: Immortality
"""

import sys
from pathlib import Path

# Add src to path
SRC_DIR = Path(__file__).parent
sys.path.insert(0, str(SRC_DIR))

from pipeline.builder import SCPBookBuilder, PipelineConfig, OUTPUT_DIR

# Heritage Collection SCP numbers
HERITAGE_COLLECTION = [
    "055", "076", "087", "093", "173", "231", "239",
    "343", "500", "682", "701", "882", "914", "963"
]

# Heritage Collection metadata for table of contents
HERITAGE_METADATA = {
    "SCP-055": {"name": "[Unknown]", "class": "Keter"},
    "SCP-076": {"name": "Able", "class": "Keter"},
    "SCP-087": {"name": "The Stairwell", "class": "Euclid"},
    "SCP-093": {"name": "Red Sea Object", "class": "Euclid"},
    "SCP-173": {"name": "The Sculpture", "class": "Euclid"},
    "SCP-231": {"name": "Special Personnel Requirements", "class": "Keter"},
    "SCP-239": {"name": "The Witch Child", "class": "Keter"},
    "SCP-343": {"name": "God", "class": "Safe"},
    "SCP-500": {"name": "Panacea", "class": "Safe"},
    "SCP-682": {"name": "Hard-to-Destroy Reptile", "class": "Keter"},
    "SCP-701": {"name": "The Hanged King's Tragedy", "class": "Euclid"},
    "SCP-882": {"name": "A Machine", "class": "Euclid"},
    "SCP-914": {"name": "The Clockworks", "class": "Safe"},
    "SCP-963": {"name": "Immortality", "class": "Safe"},
}


def get_heritage_files() -> list:
    """Get list of Heritage Collection file paths"""
    downloads_dir = OUTPUT_DIR / "downloads"
    files = []

    for scp_num in HERITAGE_COLLECTION:
        filepath = downloads_dir / f"scp-{scp_num}.txt"
        if filepath.exists():
            files.append(str(filepath))
        else:
            print(f"Warning: Missing {filepath}")

    return files


def build_volume1():
    """Build Volume 1 using Heritage Collection"""

    # Create Volume 1 specific config
    config = PipelineConfig(
        title="SCP Foundation Archive",
        subtitle="Volume I: The Heritage Collection",
        author="The SCP Foundation",
        latex_dir=str(OUTPUT_DIR / "latex" / "volume1"),
        pdf_dir=str(OUTPUT_DIR / "pdf"),
        intermediate_dir=str(OUTPUT_DIR / "intermediate" / "volume1"),
    )

    # Get Heritage Collection files
    files = get_heritage_files()
    if len(files) != 14:
        print(f"Warning: Expected 14 files, found {len(files)}")

    print("=" * 50)
    print("Building Volume 1: The Heritage Collection")
    print("=" * 50)
    print(f"\nArticles: {len(files)}")
    for f in files:
        print(f"  - {Path(f).stem}")
    print()

    # Build the book
    builder = SCPBookBuilder(config)
    latex_file = builder.build_book(files)

    return latex_file


if __name__ == "__main__":
    build_volume1()

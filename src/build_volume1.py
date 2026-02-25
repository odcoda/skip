#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "requests>=2.31",
#     "beautifulsoup4>=4.12",
# ]
# ///
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

import argparse
import sys
from pathlib import Path
from typing import List

# Add src to path
SRC_DIR = Path(__file__).parent
sys.path.insert(0, str(SRC_DIR))

from pipeline.builder import SCPBookBuilder, PipelineConfig, OUTPUT_DIR
from parsers.enhanced_wikidot_parser import EnhancedSCPDocument

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


class HeritageCollectionBuilder(SCPBookBuilder):
    """Builder that injects Heritage Collection metadata"""

    def parse_all_files(self, file_list: List[str] = None) -> List[EnhancedSCPDocument]:
        """Parse files and inject Heritage Collection metadata"""
        documents = super().parse_all_files(file_list)

        # Inject proper titles from Heritage Collection metadata
        for doc in documents:
            if doc.scp_number in HERITAGE_METADATA:
                metadata = HERITAGE_METADATA[doc.scp_number]
                doc.title = metadata["name"]
                if not doc.object_class:
                    doc.object_class = metadata["class"]

        return documents


def get_heritage_pages() -> list[str]:
    """Get canonical page names for Heritage Collection."""
    return [f"scp-{scp_num}" for scp_num in HERITAGE_COLLECTION]


def count_local_heritage_files() -> int:
    """Count how many Heritage source files already exist locally."""
    downloads_dir = OUTPUT_DIR / "downloads"
    existing = 0

    for scp_num in HERITAGE_COLLECTION:
        filepath = downloads_dir / f"scp-{scp_num}.txt"
        if filepath.exists():
            existing += 1
    return existing


def build_volume1(
    with_deps: bool = False,
    download_missing: bool = True,
    download_assets: bool = True,
    compile_pdf: bool = True,
    theme: str = "redacted",
) -> str:
    """Build Volume 1 using Heritage Collection."""
    config = PipelineConfig(
        title="SCP Foundation Archive",
        subtitle="Volume I: The Heritage Collection",
        author="The SCP Foundation",
        latex_dir=str(OUTPUT_DIR / "latex" / "volume1"),
        pdf_dir=str(OUTPUT_DIR / "pdf" / "volume1"),
        intermediate_dir=str(OUTPUT_DIR / "intermediate" / "volume1"),
        deps_dir=str(OUTPUT_DIR / "deps" / "volume1"),
        resolve_dependencies=with_deps,
        download_missing=download_missing,
        download_assets=download_assets,
        compile_pdf=compile_pdf,
        theme=theme,
    )

    pages = get_heritage_pages()
    local_count = count_local_heritage_files()

    print("=" * 50)
    print("Building Volume 1: The Heritage Collection")
    print("=" * 50)
    print(f"\nArticles: {len(pages)}")
    print(f"Local sources already present: {local_count}/{len(pages)}")
    print(f"Dependency expansion: {'enabled' if with_deps else 'disabled'}")
    print(f"Asset downloads: {'enabled' if download_assets else 'disabled'}")
    print(f"PDF compilation: {'enabled' if compile_pdf else 'disabled'}")
    for page in pages:
        print(f"  - {page}")
    print()

    builder = HeritageCollectionBuilder(config)
    return builder.build_book(pages)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build Volume 1 (Heritage Collection) with sensible defaults."
    )
    parser.add_argument(
        "--with-deps",
        action="store_true",
        help="Include dependency pages/logs/supplements in addition to the 14 core SCPs.",
    )
    parser.add_argument(
        "--no-download",
        action="store_true",
        help="Do not fetch missing source pages.",
    )
    parser.add_argument(
        "--no-assets",
        action="store_true",
        help="Do not fetch media assets.",
    )
    parser.add_argument(
        "--skip-pdf",
        action="store_true",
        help="Generate LaTeX only; skip pdflatex compilation.",
    )
    parser.add_argument(
        "--theme",
        default="redacted",
        help="Theme package name for LaTeX generation.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    build_volume1(
        with_deps=args.with_deps,
        download_missing=not args.no_download,
        download_assets=not args.no_assets,
        compile_pdf=not args.skip_pdf,
        theme=args.theme,
    )

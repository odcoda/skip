#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "requests>=2.31",
#     "beautifulsoup4>=4.12",
# ]
# ///
"""
SCP Book Pipeline Builder

Orchestrates the conversion of SCP wikidot files into a LaTeX book.
Provides a modular pipeline for testing and iteration.

Usage:
    uv run src/pipeline/builder.py --input-dir downloads --output-dir output
"""

import os
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
OUTPUT_DIR = PROJECT_ROOT / "output"

from parsers.enhanced_wikidot_parser import EnhancedWikidotParser, EnhancedSCPDocument


@dataclass
class PipelineConfig:
    """Configuration for the book building pipeline"""
    input_dir: str = field(default_factory=lambda: str(OUTPUT_DIR / "downloads"))
    output_dir: str = field(default_factory=lambda: str(OUTPUT_DIR))
    intermediate_dir: str = field(default_factory=lambda: str(OUTPUT_DIR / "intermediate"))
    latex_dir: str = field(default_factory=lambda: str(OUTPUT_DIR / "latex"))
    pdf_dir: str = field(default_factory=lambda: str(OUTPUT_DIR / "pdf"))
    template_dir: str = field(default_factory=lambda: str(PROJECT_ROOT / "templates"))
    
    # Book organization
    title: str = "SCP Foundation Archive"
    subtitle: str = "A Collection of Anomalous Objects"
    author: str = "The SCP Foundation"
    
    # Processing options
    include_addenda: bool = True
    include_footnotes: bool = True
    max_scps_per_chapter: int = 10
    
    # LaTeX options
    document_class: str = "book"
    font_size: str = "12pt"
    paper_size: str = "letterpaper"
    use_rpg_styling: bool = False  # Deprecated — use theme instead
    theme: str = "redacted"  # Theme name: "redacted", "scpbase", etc.


class SCPBookBuilder:
    """Main pipeline for building SCP books"""
    
    def __init__(self, config: PipelineConfig = None):
        self.config = config or PipelineConfig()
        self.parser = EnhancedWikidotParser()
        self.documents = []
        
    def discover_scp_files(self) -> List[str]:
        """Find all SCP files in the input directory"""
        input_path = Path(self.config.input_dir)
        scp_files = []
        
        if input_path.exists():
            # Look for SCP files (scp-XXXX.txt pattern)
            for file in input_path.glob("scp-*.txt"):
                scp_files.append(str(file))
        
        # Sort by SCP number for consistent ordering
        scp_files.sort(key=lambda x: self._extract_scp_number(x))
        return scp_files
    
    def _extract_scp_number(self, filepath: str) -> int:
        """Extract numeric SCP number for sorting"""
        import re
        match = re.search(r'scp-(\d+)', os.path.basename(filepath))
        return int(match.group(1)) if match else 999999
    
    def parse_all_files(self, file_list: List[str] = None) -> List[EnhancedSCPDocument]:
        """Parse all SCP files and return structured documents"""
        if file_list is None:
            file_list = self.discover_scp_files()
        
        documents = []
        
        print(f"Parsing {len(file_list)} SCP files...")
        for filepath in file_list:
            try:
                print(f"  Parsing {os.path.basename(filepath)}...")
                doc = self.parser.parse_file(filepath)
                documents.append(doc)
            except Exception as e:
                print(f"  Error parsing {filepath}: {e}")
        
        self.documents = documents
        return documents
    
    def save_intermediate_files(self):
        """Save parsed documents as JSON for debugging/inspection"""
        os.makedirs(self.config.intermediate_dir, exist_ok=True)
        
        for doc in self.documents:
            filename = f"{doc.scp_number.lower()}.json"
            filepath = os.path.join(self.config.intermediate_dir, filename)
            self.parser.save_json(doc, filepath)
            print(f"  Saved intermediate: {filename}")
    
    def organize_into_chapters(self) -> List[Dict[str, Any]]:
        """Organize SCPs into book chapters"""
        chapters = []
        current_chapter = []
        
        # Group by SCP series (000s, 1000s, 2000s, etc.)
        series_groups = {}
        
        for doc in self.documents:
            # Extract series number (thousands digit)
            scp_num = int(doc.scp_number.replace('SCP-', ''))
            series = (scp_num // 1000) * 1000
            
            if series not in series_groups:
                series_groups[series] = []
            series_groups[series].append(doc)
        
        # Create chapters from series
        for series_num in sorted(series_groups.keys()):
            series_docs = series_groups[series_num]
            
            # Determine chapter title
            if series_num == 0:
                chapter_title = "Series I (SCP-001 through SCP-999)"
            else:
                start = series_num
                end = series_num + 999
                chapter_title = f"Series {(series_num // 1000) + 1} (SCP-{start:03d} through SCP-{end})"
            
            # Split large series into sub-chapters if needed
            max_per_chapter = self.config.max_scps_per_chapter
            if len(series_docs) > max_per_chapter:
                for i in range(0, len(series_docs), max_per_chapter):
                    chunk = series_docs[i:i + max_per_chapter]
                    start_scp = chunk[0].scp_number
                    end_scp = chunk[-1].scp_number
                    sub_title = f"{chapter_title}: {start_scp} - {end_scp}"
                    
                    chapters.append({
                        'title': sub_title,
                        'documents': chunk,
                        'series': series_num
                    })
            else:
                chapters.append({
                    'title': chapter_title,
                    'documents': series_docs,
                    'series': series_num
                })
        
        return chapters
    
    def load_image_map(self) -> Dict[str, list]:
        """Load image mappings from data/images.yaml"""
        import yaml
        images_yaml = PROJECT_ROOT / "data" / "images.yaml"
        if not images_yaml.exists():
            return {}
        with open(images_yaml, 'r') as f:
            data = yaml.safe_load(f) or {}
        image_map = {}
        for scp_key, info in data.items():
            images = info.get('images', [])
            # Filter to images that actually exist on disk
            existing = []
            for img in images:
                if img.get('url') and img.get('filename'):
                    subdir = img.get('location', '')
                    img_path = OUTPUT_DIR / "images" / scp_key.lower() / subdir / img['filename']
                    if img_path.exists():
                        existing.append(img)
            if existing:
                image_map[scp_key.upper().replace('SCP', 'SCP')] = existing
        return image_map

    def copy_theme_files(self):
        """Copy theme .sty and graphics files into the latex output directory"""
        import shutil
        themes_src = Path(__file__).parent.parent / "latex" / "themes"
        themes_dst = Path(self.config.latex_dir)

        # Copy .sty files
        for sty in themes_src.glob("*.sty"):
            shutil.copy2(sty, themes_dst / sty.name)

        # Copy graphics directory
        graphics_src = themes_src / "graphics"
        graphics_dst = themes_dst / "graphics"
        if graphics_src.exists():
            if graphics_dst.exists():
                shutil.rmtree(graphics_dst)
            shutil.copytree(graphics_src, graphics_dst)

    def generate_individual_latex_files(self, documents: List[EnhancedSCPDocument]) -> Dict[str, str]:
        """Generate individual LaTeX files for each SCP document"""
        from latex.enhanced_converter import EnhancedLaTeXConverter

        image_map = self.load_image_map()
        converter = EnhancedLaTeXConverter(self.config, image_map=image_map)
        latex_files = {}

        # Create latex/articles directory
        articles_dir = os.path.join(self.config.latex_dir, "articles")
        os.makedirs(articles_dir, exist_ok=True)
        
        print(f"   Generating {len(documents)} individual LaTeX files...")
        
        for doc in documents:
            # Generate LaTeX content for this document
            latex_content = converter.generate_document_latex(doc)
            
            # Create filename based on SCP number
            filename = f"{doc.scp_number.lower().replace('-', '_')}.tex"
            filepath = os.path.join(articles_dir, filename)
            
            # Write the LaTeX file
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(latex_content)
            
            # Store relative path for includes
            relative_path = f"articles/{filename}"
            latex_files[doc.scp_number] = relative_path
            
        return latex_files
    
    def generate_latex(self, chapters: List[Dict[str, Any]], latex_files: Dict[str, str]) -> str:
        """Generate main LaTeX book file with includes"""
        from latex.enhanced_converter import EnhancedLaTeXConverter
        
        converter = EnhancedLaTeXConverter(self.config)
        return converter.generate_book_with_includes(chapters, latex_files)
    
    def build_book(self, scp_files: List[str] = None) -> str:
        """Complete pipeline: parse → organize → generate LaTeX"""
        
        print("=== SCP Book Builder ===")
        
        # Step 1: Parse all files
        print("\n1. Parsing wikidot files...")
        self.parse_all_files(scp_files)
        print(f"   Parsed {len(self.documents)} documents")
        
        # Step 2: Save intermediate files
        print("\n2. Saving intermediate files...")
        self.save_intermediate_files()
        
        # Step 3: Organize into chapters
        print("\n3. Organizing into chapters...")
        chapters = self.organize_into_chapters()
        print(f"   Created {len(chapters)} chapters")
        
        # Step 4: Generate individual LaTeX files
        print("\n4. Generating individual LaTeX files...")
        latex_files = self.generate_individual_latex_files(self.documents)
        
        # Step 5: Generate main LaTeX book
        print("\n5. Generating main LaTeX book...")
        latex_content = self.generate_latex(chapters, latex_files)
        
        # Step 6: Save main LaTeX file
        os.makedirs(self.config.latex_dir, exist_ok=True)
        latex_file = os.path.join(self.config.latex_dir, "scp_book.tex")
        with open(latex_file, 'w', encoding='utf-8') as f:
            f.write(latex_content)
        
        print(f"   Generated main LaTeX: {latex_file}")
        
        # Step 6.5: Copy theme files
        print("\n6. Copying theme files...")
        self.copy_theme_files()
        print(f"   Theme: {self.config.theme}")

        # Step 7: Compile to PDF
        print("\n7. Compiling to PDF...")
        from pipeline.compile_latex import compile_latex_to_pdf
        
        success, pdf_path, error = compile_latex_to_pdf(latex_file)
        if success:
            print(f"   Generated PDF: {pdf_path}")
            pdf_size = os.path.getsize(pdf_path)
            print(f"   PDF size: {pdf_size:,} bytes")
        else:
            print(f"   PDF compilation failed: {error}")
            print(f"   LaTeX file available: {latex_file}")
        
        print(f"\n=== Build Complete ===")
        print(f"LaTeX file: {latex_file}")
        if success:
            print(f"PDF file: {pdf_path}")
        else:
            print(f"PDF compilation failed - check LaTeX file manually")
        
        return latex_file


def main():
    """CLI interface for the book builder"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Build SCP Foundation LaTeX book')
    parser.add_argument('--input-dir', default=str(OUTPUT_DIR / "downloads"), help='Input directory with SCP files')
    parser.add_argument('--output-dir', default=str(OUTPUT_DIR), help='Output directory')
    parser.add_argument('--title', default='SCP Foundation Archive', help='Book title')
    parser.add_argument('--rpg-styling', action='store_true', help='Enable RPG styling (experimental)')
    parser.add_argument('--single-file', help='Process only a single SCP file')
    
    args = parser.parse_args()
    
    # Create configuration
    config = PipelineConfig(
        input_dir=args.input_dir,
        output_dir=args.output_dir,
        title=args.title,
        use_rpg_styling=args.rpg_styling
    )
    
    # Build book
    builder = SCPBookBuilder(config)
    
    if args.single_file:
        # Single file mode for testing
        latex_file = builder.build_book([args.single_file])
    else:
        # Full book mode
        latex_file = builder.build_book()


if __name__ == "__main__":
    main()
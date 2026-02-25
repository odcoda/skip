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

Orchestrates the SCP pipeline as a build system:
1. Download/source resolution (with manual overrides)
2. Parse to intermediate JSON (with manual overrides)
3. Convert to LaTeX (with manual overrides)
4. Compile to PDF

Also handles dependency manifests and asset collection.
"""

from __future__ import annotations

import argparse
import difflib
import json
import os
import re
import shutil
import sys
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple
from urllib.parse import unquote, urlparse

import requests

# Add src/ to import path when running as a script.
SRC_DIR = Path(__file__).parent.parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from parsers.enhanced_wikidot_parser import (
    ContentBlock,
    ContentType,
    EnhancedSCPDocument,
    EnhancedWikidotParser,
    SCPSection,
)
from scp_downloader import SCPDownloader

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
OUTPUT_DIR = PROJECT_ROOT / "output"
MANUAL_DIR = PROJECT_ROOT / "manual"
DIFFS_DIR = PROJECT_ROOT / "diffs"

_MEDIA_EXTENSIONS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".svg",
    ".bmp",
    ".mp3",
    ".wav",
    ".ogg",
    ".flac",
    ".mp4",
    ".webm",
    ".mov",
    ".m4v",
    ".mkv",
    ".pdf",
}


@dataclass
class PipelineConfig:
    """Configuration for the build pipeline."""

    output_dir: str = field(default_factory=lambda: str(OUTPUT_DIR))
    input_dir: Optional[str] = None
    raw_downloads_dir: Optional[str] = None
    intermediate_dir: Optional[str] = None
    latex_dir: Optional[str] = None
    pdf_dir: Optional[str] = None
    deps_dir: Optional[str] = None
    assets_dir: Optional[str] = None

    manual_dir: Optional[str] = None
    diffs_dir: Optional[str] = None
    template_dir: str = field(default_factory=lambda: str(PROJECT_ROOT / "templates"))

    # Book organization
    title: str = "SCP Foundation Archive"
    subtitle: str = "A Collection of Anomalous Objects"
    author: str = "The SCP Foundation"

    # Processing options
    include_addenda: bool = True
    include_footnotes: bool = True
    max_scps_per_chapter: int = 10
    resolve_dependencies: bool = True
    max_dependency_depth: int = 3
    download_missing: bool = True
    download_assets: bool = True
    compile_pdf: bool = True

    # LaTeX options
    document_class: str = "book"
    font_size: str = "10pt"
    paper_size: str = "letterpaper"  # Theme overrides actual geometry
    use_rpg_styling: bool = False  # Deprecated — use theme instead
    theme: str = "redacted"  # Theme name: "redacted", "scpbase", etc.

    def __post_init__(self):
        output = Path(self.output_dir)
        if self.input_dir is None:
            self.input_dir = str(output / "downloads")
        if self.raw_downloads_dir is None:
            self.raw_downloads_dir = str(output / "raw_downloads")
        if self.intermediate_dir is None:
            self.intermediate_dir = str(output / "intermediate")
        if self.latex_dir is None:
            self.latex_dir = str(output / "latex")
        if self.pdf_dir is None:
            self.pdf_dir = str(output / "pdf")
        if self.deps_dir is None:
            self.deps_dir = str(output / "deps")
        if self.assets_dir is None:
            self.assets_dir = str(output / "assets")
        if self.manual_dir is None:
            self.manual_dir = str(MANUAL_DIR)
        if self.diffs_dir is None:
            self.diffs_dir = str(DIFFS_DIR)


class SCPBookBuilder:
    """Main pipeline for building SCP books."""

    def __init__(self, config: PipelineConfig = None):
        self.config = config or PipelineConfig()
        self.parser = EnhancedWikidotParser()
        self.documents: List[EnhancedSCPDocument] = []

        self.project_root = PROJECT_ROOT
        self.output_dir = Path(self.config.output_dir)
        self.downloads_dir = Path(self.config.input_dir)
        self.raw_downloads_dir = Path(self.config.raw_downloads_dir)
        self.intermediate_dir = Path(self.config.intermediate_dir)
        self.latex_dir = Path(self.config.latex_dir)
        self.pdf_dir = Path(self.config.pdf_dir)
        self.deps_dir = Path(self.config.deps_dir)
        self.assets_dir = Path(self.config.assets_dir)

        self.manual_dir = Path(self.config.manual_dir)
        self.manual_downloads_dir = self.manual_dir / "downloads"
        self.manual_raw_downloads_dir = self.manual_dir / "raw_downloads"
        self.manual_intermediate_dir = self.manual_dir / "intermediate"
        self.manual_latex_dir = self.manual_dir / "latex"
        self.manual_deps_dir = self.manual_dir / "deps"
        self.manual_assets_dir = self.manual_dir / "assets"

        self.diffs_dir = Path(self.config.diffs_dir)

        self._downloader: Optional[SCPDownloader] = None
        self._auto_documents_by_slug: Dict[str, EnhancedSCPDocument] = {}
        self._doc_slug_by_id: Dict[int, str] = {}
        self._resolved_source_paths: Dict[str, Path] = {}
        self._resolved_auto_paths: Dict[str, Path] = {}
        self._explicit_source_paths: Dict[str, Path] = {}

        self._related_page_hints = self._load_related_page_hints(self.project_root / "data" / "related_pages.yaml")
        self._image_index = self._load_image_index(self.project_root / "data" / "images.yaml")

    # -------- Public API --------

    def discover_scp_files(self) -> List[str]:
        """Find all SCP source files in output/manual downloads."""
        files: Dict[str, Path] = {}

        for folder in [self.downloads_dir, self.manual_downloads_dir]:
            if not folder.exists():
                continue
            for file in folder.glob("scp-*.txt"):
                slug = self._normalize_slug(file.stem)
                files[slug] = file

        return [str(files[slug]) for slug in sorted(files, key=self._slug_sort_key)]

    def parse_all_files(self, file_list: List[str] = None) -> List[EnhancedSCPDocument]:
        """Parse all requested files and apply manual intermediate overrides."""
        slugs = self._slugs_from_file_list(file_list)
        documents: List[EnhancedSCPDocument] = []
        self._auto_documents_by_slug = {}
        self._doc_slug_by_id = {}

        print(f"Parsing {len(slugs)} source files...")

        for slug in slugs:
            effective_source = self._resolved_source_paths.get(slug)
            auto_source = self._resolved_auto_paths.get(slug)

            if effective_source is None:
                explicit_candidate = self._explicit_source_paths.get(slug)
                auto_candidate = self.downloads_dir / f"{slug}.txt"
                manual_candidate = self.manual_downloads_dir / f"{slug}.txt"
                if manual_candidate.exists():
                    effective_source = manual_candidate
                elif explicit_candidate and explicit_candidate.exists():
                    effective_source = explicit_candidate
                    auto_source = explicit_candidate
                elif auto_candidate.exists():
                    effective_source = auto_candidate
                    auto_source = auto_candidate

            if effective_source is None or not effective_source.exists():
                print(f"  Skipping {slug}: no source file")
                continue

            parse_source = auto_source if auto_source and auto_source.exists() else effective_source

            try:
                auto_doc = self.parser.parse_file(str(parse_source))
            except Exception as exc:
                print(f"  Error parsing {parse_source}: {exc}")
                continue

            auto_doc.metadata["page_slug"] = slug
            auto_doc.metadata["source_file"] = str(parse_source)
            self._auto_documents_by_slug[slug] = auto_doc

            manual_json = self.manual_intermediate_dir / f"{slug}.json"
            if manual_json.exists():
                manual_doc = self._load_document_from_json_file(manual_json)
                if manual_doc is not None:
                    doc = manual_doc
                    doc.metadata["manual_intermediate_override"] = str(manual_json)
                    print(f"  Using manual intermediate override for {slug}")
                else:
                    doc = auto_doc
                    print(f"  Failed to read manual intermediate override for {slug}; using parsed output")
            else:
                doc = auto_doc

            doc.metadata["page_slug"] = slug
            documents.append(doc)
            self._doc_slug_by_id[id(doc)] = slug

        self.documents = documents
        return documents

    def save_intermediate_files(self):
        """Save parsed documents to output/intermediate/*.json."""
        self.intermediate_dir.mkdir(parents=True, exist_ok=True)

        if self._auto_documents_by_slug:
            iterator = self._auto_documents_by_slug.items()
        else:
            iterator = []
            for doc in self.documents:
                slug = self._slug_for_document(doc)
                iterator.append((slug, doc))

        for slug, doc in iterator:
            out_path = self.intermediate_dir / f"{slug}.json"
            self.parser.save_json(doc, str(out_path))
            print(f"  Saved intermediate: {out_path.name}")

    def organize_into_chapters(self) -> List[Dict[str, Any]]:
        """Organize SCPs by series and place non-SCP files in a supplements chapter."""
        chapters: List[Dict[str, Any]] = []
        series_groups: Dict[int, List[EnhancedSCPDocument]] = {}
        supplements: List[EnhancedSCPDocument] = []

        for doc in self.documents:
            scp_num = self._extract_numeric_scp(doc)
            if scp_num is None:
                supplements.append(doc)
                continue

            series = (scp_num // 1000) * 1000
            series_groups.setdefault(series, []).append(doc)

        for series_num in sorted(series_groups.keys()):
            series_docs = sorted(series_groups[series_num], key=self._document_sort_key)
            if series_num == 0:
                chapter_title = "Series I (SCP-001 through SCP-999)"
            else:
                start = series_num
                end = series_num + 999
                chapter_title = f"Series {(series_num // 1000) + 1} (SCP-{start:03d} through SCP-{end})"

            max_per_chapter = self.config.max_scps_per_chapter
            if len(series_docs) > max_per_chapter:
                for i in range(0, len(series_docs), max_per_chapter):
                    chunk = series_docs[i : i + max_per_chapter]
                    start_label = chunk[0].scp_number
                    end_label = chunk[-1].scp_number
                    chapters.append(
                        {
                            "title": f"{chapter_title}: {start_label} - {end_label}",
                            "documents": chunk,
                            "series": series_num,
                        }
                    )
            else:
                chapters.append(
                    {
                        "title": chapter_title,
                        "documents": series_docs,
                        "series": series_num,
                    }
                )

        if supplements:
            supplements.sort(key=self._document_sort_key)
            chapters.append(
                {
                    "title": "Supplementary Documents",
                    "documents": supplements,
                    "series": 999999,
                }
            )

        return chapters

    def load_image_map(self) -> Dict[str, list]:
        """Load image mappings from data/images.yaml with output/assets and legacy output/images fallback."""
        image_map: Dict[str, list] = {}

        for slug, images in self._image_index.items():
            existing = []
            for img in images:
                filename = img.get("filename", "").strip()
                if not filename:
                    continue
                subdir = img.get("location", "").strip("/")

                new_path = self.assets_dir / slug
                old_path = self.output_dir / "images" / slug
                if subdir:
                    new_path = new_path / subdir
                    old_path = old_path / subdir
                new_path = new_path / filename
                old_path = old_path / filename

                candidate = new_path if new_path.exists() else old_path
                if candidate.exists() and self._is_valid_media_file(candidate):
                    existing.append(img)

            if existing and slug.startswith("scp-"):
                image_map[slug.upper()] = existing

        return image_map

    def copy_theme_files(self):
        """Copy theme files into output/latex for pdflatex resolution."""
        themes_src = Path(__file__).parent.parent / "latex" / "themes"
        themes_dst = self.latex_dir
        themes_dst.mkdir(parents=True, exist_ok=True)

        for sty in themes_src.glob("*.sty"):
            shutil.copy2(sty, themes_dst / sty.name)

        graphics_src = themes_src / "graphics"
        graphics_dst = themes_dst / "graphics"
        if graphics_src.exists():
            if graphics_dst.exists():
                shutil.rmtree(graphics_dst)
            shutil.copytree(graphics_src, graphics_dst)

    def generate_individual_latex_files(self, documents: List[EnhancedSCPDocument]) -> Dict[str, str]:
        """Generate per-document LaTeX, applying manual overrides when present."""
        from latex.enhanced_converter import EnhancedLaTeXConverter

        self.latex_dir.mkdir(parents=True, exist_ok=True)
        articles_dir = self.latex_dir / "articles"
        articles_dir.mkdir(parents=True, exist_ok=True)

        image_map = self.load_image_map()
        converter = EnhancedLaTeXConverter(self.config, image_map=image_map)
        latex_files: Dict[str, str] = {}

        print(f"   Generating {len(documents)} individual LaTeX files...")

        for doc in documents:
            slug = self._slug_for_document(doc)
            filename = self._article_filename_for_slug(slug)
            out_path = articles_dir / filename

            latex_content = converter.generate_document_latex(doc)
            out_path.write_text(latex_content, encoding="utf-8")

            include_path = f"articles/{filename}"
            manual_path = self.manual_latex_dir / "articles" / filename
            if manual_path.exists():
                self._write_text_diff(out_path, manual_path)
                include_path = os.path.relpath(manual_path, self.latex_dir).replace(os.sep, "/")

            key = self._latex_key_for_document(doc)
            latex_files[key] = include_path

        return latex_files

    def generate_latex(self, chapters: List[Dict[str, Any]], latex_files: Dict[str, str]) -> str:
        """Generate the main book LaTeX file."""
        from latex.enhanced_converter import EnhancedLaTeXConverter

        converter = EnhancedLaTeXConverter(self.config)
        return converter.generate_book_with_includes(chapters, latex_files)

    def build_book(self, scp_files: List[str] = None) -> str:
        """Complete pipeline with dependency-aware orchestration and overrides."""

        print("=== SCP Book Builder ===")
        self.ensure_directories()
        self._sync_manual_assets()

        initial_slugs = self._slugs_from_file_list(scp_files)
        if not initial_slugs:
            raise RuntimeError("No input SCP files found. Add files to output/downloads or pass --single-file.")

        print("\n1. Resolving downloads and dependencies...")
        all_slugs = self._resolve_dependency_closure(initial_slugs)
        print(f"   Build targets: {len(all_slugs)} pages")

        print("\n2. Parsing source files...")
        self.parse_all_files(all_slugs)
        print(f"   Parsed {len(self.documents)} documents")

        print("\n3. Saving intermediate files...")
        self.save_intermediate_files()

        print("\n4. Organizing chapters...")
        chapters = self.organize_into_chapters()
        print(f"   Created {len(chapters)} chapters")

        print("\n5. Generating individual LaTeX files...")
        latex_files = self.generate_individual_latex_files(self.documents)

        print("\n6. Generating main LaTeX book...")
        latex_content = self.generate_latex(chapters, latex_files)
        self.latex_dir.mkdir(parents=True, exist_ok=True)
        auto_main_latex = self.latex_dir / "scp_book.tex"
        auto_main_latex.write_text(latex_content, encoding="utf-8")

        compile_target = auto_main_latex
        manual_main = self.manual_latex_dir / "scp_book.tex"
        if manual_main.exists():
            self._write_text_diff(auto_main_latex, manual_main)
            compile_target = manual_main
            print(f"   Using manual LaTeX override: {manual_main}")

        print("\n7. Copying theme files...")
        self.copy_theme_files()
        print(f"   Theme: {self.config.theme}")

        if self.config.compile_pdf:
            print("\n8. Compiling to PDF...")
            from pipeline.compile_latex import compile_latex_to_pdf

            success, pdf_path, error = compile_latex_to_pdf(
                str(compile_target),
                output_pdf_dir=str(self.pdf_dir),
                build_dir=str(self.latex_dir / "build"),
            )

            if success:
                print(f"   Generated PDF: {pdf_path}")
                if pdf_path and os.path.exists(pdf_path):
                    print(f"   PDF size: {os.path.getsize(pdf_path):,} bytes")
            else:
                print(f"   PDF compilation failed: {error}")
                print(f"   LaTeX file available: {compile_target}")

        print("\n=== Build Complete ===")
        print(f"LaTeX file: {compile_target}")
        if self.config.compile_pdf:
            print(f"PDF output dir: {self.pdf_dir}")

        return str(compile_target)

    # -------- Orchestration helpers --------

    def ensure_directories(self):
        output_dirs = [
            self.output_dir,
            self.downloads_dir,
            self.raw_downloads_dir,
            self.intermediate_dir,
            self.latex_dir,
            self.pdf_dir,
            self.deps_dir,
            self.assets_dir,
            self.diffs_dir,
        ]
        for d in output_dirs:
            d.mkdir(parents=True, exist_ok=True)

        manual_dirs = [
            self.manual_dir,
            self.manual_downloads_dir,
            self.manual_raw_downloads_dir,
            self.manual_intermediate_dir,
            self.manual_latex_dir / "articles",
            self.manual_deps_dir,
            self.manual_assets_dir,
        ]
        for d in manual_dirs:
            d.mkdir(parents=True, exist_ok=True)

    def _get_downloader(self) -> SCPDownloader:
        if self._downloader is None:
            self._downloader = SCPDownloader(
                output_dir=str(self.downloads_dir),
                raw_output_dir=str(self.raw_downloads_dir),
            )
        return self._downloader

    def _resolve_dependency_closure(self, initial_slugs: List[str]) -> List[str]:
        """Resolve download/dep graph and build source maps for downstream steps."""
        queue = deque((slug, 0) for slug in initial_slugs)
        seen: set[str] = set()
        ordered: List[str] = []

        while queue:
            slug, depth = queue.popleft()
            if slug in seen:
                continue
            seen.add(slug)

            effective_source, auto_source = self._prepare_source(slug)
            if effective_source is None:
                print(f"  Warning: missing source for {slug}")
                continue

            self._resolved_source_paths[slug] = effective_source
            if auto_source is not None and auto_source.exists():
                self._resolved_auto_paths[slug] = auto_source

            dep_pages = []
            if self.config.resolve_dependencies:
                dep_pages = self._resolve_dependencies_for_slug(slug, effective_source)

            if depth < self.config.max_dependency_depth:
                for dep in dep_pages:
                    if dep not in seen:
                        queue.append((dep, depth + 1))

            ordered.append(slug)

        return sorted(ordered, key=self._slug_sort_key)

    def _prepare_source(self, slug: str) -> Tuple[Optional[Path], Optional[Path]]:
        """Ensure source file exists (download if needed), apply manual override precedence."""
        explicit = self._explicit_source_paths.get(slug)
        if explicit and explicit.exists():
            manual_txt = self.manual_downloads_dir / f"{slug}.txt"
            if manual_txt.exists():
                self._write_text_diff(explicit, manual_txt)
                return manual_txt, explicit
            return explicit, explicit

        auto_txt = self.downloads_dir / f"{slug}.txt"
        manual_txt = self.manual_downloads_dir / f"{slug}.txt"

        if not auto_txt.exists() and self.config.download_missing:
            try:
                print(f"  Downloading missing page: {slug}")
                downloader = self._get_downloader()
                downloader.download_page(slug, output_filename=f"{slug}.txt")
            except Exception as exc:
                print(f"  Warning: failed to download {slug}: {exc}")

        if manual_txt.exists():
            self._write_text_diff(auto_txt, manual_txt)
            return manual_txt, auto_txt if auto_txt.exists() else None

        if auto_txt.exists():
            return auto_txt, auto_txt

        return None, None

    def _resolve_dependencies_for_slug(self, slug: str, source_path: Path) -> List[str]:
        """Resolve deps + assets for a page and emit output/deps manifest."""
        manual_dep_file = self.manual_deps_dir / f"{slug}.yaml"
        pages: List[str]
        assets: List[str]
        source_label: str

        if manual_dep_file.exists():
            pages, assets = self._read_dependency_manifest(manual_dep_file)
            source_label = "manual_override"
            assets = self._materialize_manual_assets_for_manifest(slug, assets)
        else:
            source_text = source_path.read_text(encoding="utf-8", errors="replace")
            pages = self._extract_page_dependencies(source_text, slug)
            if self.config.download_assets:
                self._download_assets_for_slug(slug, source_text)
            assets = self._list_assets_for_slug(slug)
            source_label = "auto"

        self._write_dependency_manifest(slug, pages, assets, source_label)
        return pages

    # -------- Dependency + asset handling --------

    def _extract_page_dependencies(self, source_text: str, page_slug: str) -> List[str]:
        deps: set[str] = set()

        # [[include page-name]]
        for match in re.finditer(r"\[\[include\s+([^\]]+)\]\]", source_text, flags=re.IGNORECASE | re.DOTALL):
            payload = match.group(1).strip()
            first_token = payload.splitlines()[0].strip().split()[0]
            first_token = first_token.split("|", 1)[0].strip()
            dep = self._normalize_slug(first_token)
            if self._is_supplement_candidate(dep, page_slug):
                deps.add(dep)

        # [[[page-name]]] / [[[page-name|text]]]
        for match in re.finditer(r"\[\[\[([^\]|#]+)", source_text):
            dep = self._normalize_slug(match.group(1))
            if self._is_supplement_candidate(dep, page_slug):
                deps.add(dep)

        # Direct links to SCP wiki pages
        for match in re.finditer(r"https?://scp-wiki\.wikidot\.com/([a-z0-9:_\-]+)", source_text, flags=re.IGNORECASE):
            dep = self._normalize_slug(match.group(1))
            if self._is_supplement_candidate(dep, page_slug):
                deps.add(dep)

        # Manual hints from related_pages.yaml
        deps.update(self._related_page_hints.get(page_slug, []))

        deps.discard(page_slug)
        return sorted(deps, key=self._slug_sort_key)

    def _is_supplement_candidate(self, dep_slug: str, page_slug: str) -> bool:
        if not dep_slug or dep_slug == page_slug:
            return False

        lowered = dep_slug.lower()
        if lowered.startswith(("component:", "theme:", "module:", "css:", "template:")):
            return False

        if lowered.startswith("scp-") and lowered != page_slug:
            return False

        keywords = (
            "experiment",
            "exploration",
            "destruction",
            "incident",
            "document",
            "routine",
            "log",
            "fragment:",
            "supplement",
            "addendum",
        )
        if any(keyword in lowered for keyword in keywords):
            return True

        # Keep same-page fragments/annexes by prefix.
        return lowered.startswith(f"{page_slug}-")

    def _download_assets_for_slug(self, slug: str, source_text: str):
        urls: set[str] = set()

        # Direct media URLs in source.
        for match in re.finditer(r"https?://[^\s\]\)>'\"]+", source_text):
            raw_url = match.group(0).rstrip(".,;)")
            if self._looks_like_asset_url(raw_url):
                urls.add(raw_url)

        # [[image ...]] blocks with either URL or local filename.
        for match in re.finditer(r"\[\[image\s+([^\]\s|]+)", source_text, flags=re.IGNORECASE):
            target = match.group(1).strip()
            if target.startswith("http") and self._looks_like_asset_url(target):
                urls.add(target)
            elif self._looks_like_asset_name(target):
                urls.add(f"https://scp-wiki.wdfiles.com/local--files/{slug}/{target}")

        # Curated image index hints.
        for img in self._image_index.get(slug, []):
            url = img.get("url", "").strip()
            if not url:
                continue
            filename = img.get("filename", "").strip() or None
            subdir = img.get("location", "").strip("/")
            self._download_asset(url, slug, preferred_filename=filename, subdir=subdir)

        for url in sorted(urls):
            self._download_asset(url, slug)

    def _download_asset(
        self,
        url: str,
        slug: str,
        preferred_filename: Optional[str] = None,
        subdir: str = "",
    ) -> Optional[str]:
        parsed = urlparse(url)
        filename = preferred_filename or unquote(Path(parsed.path).name)
        if not filename:
            return None

        filename = self._sanitize_asset_filename(filename)
        asset_dir = self.assets_dir / slug
        if subdir:
            asset_dir = asset_dir / subdir
        asset_dir.mkdir(parents=True, exist_ok=True)

        out_path = asset_dir / filename
        if out_path.exists() and out_path.stat().st_size > 0:
            return str(out_path.relative_to(self.assets_dir)).replace(os.sep, "/")

        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            if not self._is_valid_media_bytes(filename, response.content):
                print(f"  Warning: downloaded asset does not match expected media format: {url}")
                return None
            out_path.write_bytes(response.content)
            return str(out_path.relative_to(self.assets_dir)).replace(os.sep, "/")
        except Exception as exc:
            print(f"  Warning: failed to download asset {url}: {exc}")
            return None

    def _materialize_manual_assets_for_manifest(self, slug: str, assets: List[str]) -> List[str]:
        materialized: set[str] = set()

        for entry in assets:
            item = entry.strip()
            if not item:
                continue

            if item.startswith("http://") or item.startswith("https://"):
                downloaded = self._download_asset(item, slug)
                if downloaded:
                    materialized.add(downloaded)
                continue

            relative = item.replace("\\", "/").lstrip("/")
            source_candidate = self.manual_assets_dir / relative
            if not source_candidate.exists():
                source_candidate = self.manual_assets_dir / slug / relative

            target_candidate = self.assets_dir / relative
            if not target_candidate.exists() and source_candidate.exists():
                target_candidate.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source_candidate, target_candidate)

            if target_candidate.exists():
                materialized.add(str(target_candidate.relative_to(self.assets_dir)).replace(os.sep, "/"))

        materialized.update(self._list_assets_for_slug(slug))
        return sorted(materialized)

    def _list_assets_for_slug(self, slug: str) -> List[str]:
        slug_dir = self.assets_dir / slug
        if not slug_dir.exists():
            return []

        assets: List[str] = []
        for file in slug_dir.rglob("*"):
            if file.is_file():
                assets.append(str(file.relative_to(self.assets_dir)).replace(os.sep, "/"))
        return sorted(set(assets))

    def _sync_manual_assets(self):
        """Mirror manual/assets into output/assets for override support."""
        if not self.manual_assets_dir.exists():
            return

        for file in self.manual_assets_dir.rglob("*"):
            if not file.is_file():
                continue
            rel = file.relative_to(self.manual_assets_dir)
            dest = self.assets_dir / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(file, dest)

    # -------- Dependency manifest IO --------

    def _read_dependency_manifest(self, path: Path) -> Tuple[List[str], List[str]]:
        pages: List[str] = []
        assets: List[str] = []

        current_list: Optional[str] = None
        for raw_line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            line = raw_line.rstrip()
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue

            if stripped == "pages:":
                current_list = "pages"
                continue
            if stripped == "assets:":
                current_list = "assets"
                continue

            if stripped.startswith("- "):
                value = stripped[2:].strip()
                if current_list == "pages":
                    dep = self._normalize_dep_entry(value)
                    if dep:
                        pages.append(dep)
                elif current_list == "assets":
                    assets.append(value)
                continue

            if stripped.startswith("include:"):
                current_list = "include"
                continue

        # Support related_pages-style include list if used as manual deps.
        if current_list == "include":
            for raw_line in path.read_text(encoding="utf-8", errors="replace").splitlines():
                stripped = raw_line.strip()
                if stripped.startswith("- "):
                    dep = self._normalize_dep_entry(stripped[2:].strip())
                    if dep:
                        pages.append(dep)

        pages = sorted({p for p in pages if p}, key=self._slug_sort_key)
        assets = sorted({a.strip() for a in assets if a.strip()})
        return pages, assets

    def _write_dependency_manifest(self, slug: str, pages: List[str], assets: List[str], source_label: str):
        path = self.deps_dir / f"{slug}.yaml"
        path.parent.mkdir(parents=True, exist_ok=True)

        lines = [
            f"page: {slug}",
            f"source: {source_label}",
            f"generated_at: {datetime.now(timezone.utc).isoformat()}",
            "depends_on:",
            "  pages:",
        ]

        for dep in sorted(set(pages), key=self._slug_sort_key):
            lines.append(f"    - {dep}")

        lines.append("  assets:")
        for asset in sorted(set(assets)):
            lines.append(f"    - {asset}")

        path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    # -------- Manual override diff handling --------

    def _write_text_diff(self, auto_path: Path, manual_path: Path):
        if not manual_path.exists() or not auto_path.exists():
            return
        if auto_path.suffix not in {".txt", ".tex"}:
            return

        auto_text = auto_path.read_text(encoding="utf-8", errors="replace")
        manual_text = manual_path.read_text(encoding="utf-8", errors="replace")

        rel_path: Path
        try:
            rel_path = auto_path.relative_to(self.output_dir)
        except ValueError:
            rel_path = auto_path.name and Path(auto_path.name) or Path("override")

        diff_path = self.diffs_dir / rel_path
        diff_path = diff_path.with_suffix(diff_path.suffix + ".diff")
        diff_path.parent.mkdir(parents=True, exist_ok=True)

        diff_lines = list(
            difflib.unified_diff(
                auto_text.splitlines(keepends=True),
                manual_text.splitlines(keepends=True),
                fromfile=str(auto_path),
                tofile=str(manual_path),
            )
        )

        if diff_lines:
            diff_path.write_text("".join(diff_lines), encoding="utf-8")
        elif diff_path.exists():
            diff_path.unlink()

    # -------- Data loading --------

    def _load_related_page_hints(self, path: Path) -> Dict[str, List[str]]:
        """Parse data/related_pages.yaml with a light-weight parser (no external yaml dep)."""
        if not path.exists():
            return {}

        hints: Dict[str, List[str]] = {}
        current_slug: Optional[str] = None
        in_include = False

        for raw_line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            line = raw_line.rstrip("\n")
            top = re.match(r"^(SCP-\d+):\s*$", line)
            if top:
                current_slug = self._normalize_slug(top.group(1))
                hints.setdefault(current_slug, [])
                in_include = False
                continue

            if current_slug is None:
                continue

            if re.match(r"^\s{2}include:\s*$", line):
                in_include = True
                continue

            if re.match(r"^\s{2}[a-zA-Z_][^:]*:\s*", line):
                # Any other top-level key under current SCP.
                if not line.strip().startswith("include:"):
                    in_include = False

            if in_include:
                item = re.match(r"^\s*-\s*(.+)$", line)
                if item:
                    dep = self._normalize_dep_entry(item.group(1).strip())
                    if dep:
                        hints[current_slug].append(dep)

        deduped: Dict[str, List[str]] = {}
        for slug, deps in hints.items():
            deduped[slug] = sorted({d for d in deps if d}, key=self._slug_sort_key)
        return deduped

    def _load_image_index(self, path: Path) -> Dict[str, List[Dict[str, str]]]:
        """Parse data/images.yaml into {page_slug: [{filename,url,location,...}, ...]}"""
        if not path.exists():
            return {}

        index: Dict[str, List[Dict[str, str]]] = {}
        current_slug: Optional[str] = None
        in_images = False
        current_image: Optional[Dict[str, str]] = None

        for raw_line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            line = raw_line.rstrip("\n")
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue

            top = re.match(r"^(SCP-\d+):\s*$", line)
            if top:
                current_slug = self._normalize_slug(top.group(1))
                index.setdefault(current_slug, [])
                in_images = False
                current_image = None
                continue

            if current_slug is None:
                continue

            if re.match(r"^\s{2}images:\s*$", line):
                in_images = True
                current_image = None
                continue

            if re.match(r"^\s{2}[a-zA-Z_][^:]*:\s*", line) and not line.strip().startswith("images:"):
                in_images = False
                current_image = None

            if not in_images:
                continue

            list_item = re.match(r"^\s*-\s*(.+)$", line)
            if list_item:
                current_image = {}
                index[current_slug].append(current_image)
                payload = list_item.group(1).strip()
                if ":" in payload:
                    key, value = payload.split(":", 1)
                    current_image[key.strip()] = self._strip_yaml_scalar(value.strip())
                continue

            kv = re.match(r"^\s+([a-zA-Z_][a-zA-Z0-9_-]*):\s*(.*)$", line)
            if kv and current_image is not None:
                key = kv.group(1).strip()
                value = self._strip_yaml_scalar(kv.group(2).strip())
                current_image[key] = value

        return index

    def _strip_yaml_scalar(self, value: str) -> str:
        if value in {"|", ">"}:
            return ""
        value = value.strip()
        if value.startswith("\"") and value.endswith("\"") and len(value) >= 2:
            return value[1:-1]
        if value.startswith("'") and value.endswith("'") and len(value) >= 2:
            return value[1:-1]
        return value

    # -------- Document reconstruction --------

    def _load_document_from_json_file(self, path: Path) -> Optional[EnhancedSCPDocument]:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return self._document_from_dict(data)
        except Exception as exc:
            print(f"  Warning: failed to parse JSON override {path}: {exc}")
            return None

    def _document_from_dict(self, data: Dict[str, Any]) -> EnhancedSCPDocument:
        sections = [self._section_from_dict(item) for item in data.get("sections", [])]
        includes = [self._block_from_dict(item) for item in data.get("includes", [])]
        modules = [self._block_from_dict(item) for item in data.get("modules", [])]

        doc = EnhancedSCPDocument(
            scp_number=data.get("scp_number", "SCP-UNKNOWN"),
            title=data.get("title", ""),
            object_class=data.get("object_class", ""),
            sections=sections,
            includes=includes,
            modules=modules,
            metadata=data.get("metadata") or {},
        )
        return doc

    def _section_from_dict(self, data: Dict[str, Any]) -> SCPSection:
        return SCPSection(
            section_type=data.get("section_type", "unknown"),
            title=data.get("title", ""),
            content_blocks=[self._block_from_dict(item) for item in data.get("content_blocks", [])],
        )

    def _block_from_dict(self, data: Dict[str, Any]) -> ContentBlock:
        raw_type = data.get("type", ContentType.PARAGRAPH.value)
        if isinstance(raw_type, ContentType):
            block_type = raw_type
        else:
            try:
                block_type = ContentType(str(raw_type))
            except ValueError:
                block_type = ContentType.PARAGRAPH

        return ContentBlock(
            type=block_type,
            content=data.get("content", ""),
            attributes=data.get("attributes") or {},
            formatting=data.get("formatting") or [],
        )

    # -------- Naming, normalization, sorting --------

    def _slugs_from_file_list(self, file_list: Optional[Iterable[str]]) -> List[str]:
        if file_list:
            slugs: List[str] = []
            self._explicit_source_paths = {}
            for item in file_list:
                slug = self._normalize_slug(item)
                if not slug:
                    continue
                slugs.append(slug)
                candidate = Path(str(item))
                if candidate.exists():
                    self._explicit_source_paths[slug] = candidate
            return sorted({slug for slug in slugs if slug}, key=self._slug_sort_key)

        self._explicit_source_paths = {}
        discovered = self.discover_scp_files()
        slugs = [self._normalize_slug(Path(path).stem) for path in discovered]
        return sorted({slug for slug in slugs if slug}, key=self._slug_sort_key)

    def _normalize_slug(self, value: str) -> str:
        text = str(value).strip()
        if not text:
            return ""

        if text.startswith("http://") or text.startswith("https://"):
            text = urlparse(text).path.strip("/").split("/")[-1]

        text = os.path.basename(text)
        text = Path(text).stem
        text = text.lower()

        if text.isdigit():
            return f"scp-{text}"

        # Keep colon for fragment pages; normalize separators elsewhere.
        text = text.replace(" ", "-")
        if text.startswith("scp_"):
            text = text.replace("scp_", "scp-", 1)
        return text

    def _normalize_dep_entry(self, entry: str) -> str:
        value = entry.strip()
        if not value:
            return ""

        # Drop trailing human-readable reason, e.g. "page-name: reason".
        if ": " in value:
            value = value.split(": ", 1)[0]

        if value.startswith("http://") or value.startswith("https://"):
            value = urlparse(value).path.strip("/").split("/")[-1]

        return self._normalize_slug(value)

    def _slug_sort_key(self, slug: str) -> Tuple[int, Any]:
        match = re.match(r"^scp-(\d+)$", slug)
        if match:
            return (0, int(match.group(1)))
        return (1, slug)

    def _document_sort_key(self, doc: EnhancedSCPDocument) -> Tuple[int, Any]:
        slug = self._slug_for_document(doc)
        return self._slug_sort_key(slug)

    def _extract_numeric_scp(self, doc: EnhancedSCPDocument) -> Optional[int]:
        match = re.search(r"SCP-(\d+)", doc.scp_number or "")
        if not match:
            slug = self._slug_for_document(doc)
            match = re.search(r"scp-(\d+)", slug)
        if match:
            return int(match.group(1))
        return None

    def _slug_for_document(self, doc: EnhancedSCPDocument) -> str:
        metadata_slug = (doc.metadata or {}).get("page_slug") if doc.metadata else None
        if metadata_slug:
            return self._normalize_slug(metadata_slug)

        remembered = self._doc_slug_by_id.get(id(doc))
        if remembered:
            return remembered

        if doc.scp_number and re.match(r"SCP-\d+", doc.scp_number):
            return self._normalize_slug(doc.scp_number)

        title_slug = re.sub(r"[^a-z0-9]+", "-", (doc.title or "unknown").lower()).strip("-")
        return title_slug or "unknown"

    def _latex_key_for_document(self, doc: EnhancedSCPDocument) -> str:
        slug = self._slug_for_document(doc)
        return slug

    def _article_filename_for_slug(self, slug: str) -> str:
        match = re.match(r"^scp-(\d+)$", slug)
        if match:
            return f"scp_{match.group(1)}.tex"

        safe = re.sub(r"[^a-z0-9]+", "_", slug.lower()).strip("_")
        return f"{safe or 'document'}.tex"

    def _sanitize_asset_filename(self, filename: str) -> str:
        return re.sub(r"[^A-Za-z0-9._-]", "_", filename)

    def _looks_like_asset_url(self, url: str) -> bool:
        path = urlparse(url).path.lower()
        return any(path.endswith(ext) for ext in _MEDIA_EXTENSIONS)

    def _looks_like_asset_name(self, name: str) -> bool:
        lowered = name.lower()
        return any(lowered.endswith(ext) for ext in _MEDIA_EXTENSIONS)

    def _is_valid_media_file(self, path: Path) -> bool:
        try:
            blob = path.read_bytes()
        except Exception:
            return False
        return self._is_valid_media_bytes(path.name, blob)

    def _is_valid_media_bytes(self, filename: str, blob: bytes) -> bool:
        ext = Path(filename).suffix.lower()
        if ext in {".jpg", ".jpeg"}:
            return blob.startswith(b"\xff\xd8\xff")
        if ext == ".png":
            return blob.startswith(b"\x89PNG\r\n\x1a\n")
        if ext == ".gif":
            return blob.startswith((b"GIF87a", b"GIF89a"))
        if ext == ".webp":
            return len(blob) >= 12 and blob.startswith(b"RIFF") and blob[8:12] == b"WEBP"
        if ext == ".bmp":
            return blob.startswith(b"BM")
        if ext == ".pdf":
            return blob.startswith(b"%PDF-")
        # For audio/video and unknown types, only enforce non-empty.
        return len(blob) > 0

    # -------- CLI --------


def main():
    """CLI interface for the book builder."""
    parser = argparse.ArgumentParser(description="Build SCP Foundation LaTeX book")
    parser.add_argument("--input-dir", default=str(OUTPUT_DIR / "downloads"), help="Input directory with SCP files")
    parser.add_argument("--output-dir", default=str(OUTPUT_DIR), help="Output directory")
    parser.add_argument("--title", default="SCP Foundation Archive", help="Book title")
    parser.add_argument("--theme", default="redacted", help="Theme package name")
    parser.add_argument("--single-file", help="Process only a single SCP/page file")
    parser.add_argument("--no-download", action="store_true", help="Do not fetch missing source files")
    parser.add_argument("--no-assets", action="store_true", help="Do not fetch assets/media files")
    parser.add_argument("--no-deps", action="store_true", help="Do not resolve dependency pages")
    parser.add_argument("--skip-pdf", action="store_true", help="Skip pdflatex compilation")

    args = parser.parse_args()

    config = PipelineConfig(
        input_dir=args.input_dir,
        output_dir=args.output_dir,
        title=args.title,
        theme=args.theme,
        download_missing=not args.no_download,
        download_assets=not args.no_assets,
        resolve_dependencies=not args.no_deps,
        compile_pdf=not args.skip_pdf,
    )

    builder = SCPBookBuilder(config)
    if args.single_file:
        builder.build_book([args.single_file])
    else:
        builder.build_book()


if __name__ == "__main__":
    main()

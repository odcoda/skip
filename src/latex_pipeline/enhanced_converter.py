#!/usr/bin/env python3
"""
Enhanced LaTeX Converter

Converts the enhanced semantic SCP structure to well-formatted LaTeX
with proper handling of dialogue, quote blocks, and complex formatting.
"""

import re
import os
from pathlib import Path
from typing import List, Dict, Any
from parsers.enhanced_wikidot_parser import EnhancedSCPDocument, ContentBlock, SCPSection


class EnhancedLaTeXConverter:
    """Converts enhanced SCP documents to LaTeX with semantic formatting"""

    def __init__(self, config, image_map=None):
        self.config = config
        self.footnote_counter = 0
        self.image_map = image_map or {}  # SCP number -> list of image info dicts
        self.theme = getattr(config, 'theme', 'redacted')
        self.current_scp_number = None
        self.output_dir = Path(getattr(config, 'output_dir', 'output')).resolve()
        self.latex_dir = Path(getattr(config, 'latex_dir', 'output/latex')).resolve()
        
    def generate_book(self, chapters: List[Dict[str, Any]]) -> str:
        """Generate complete LaTeX book from organized chapters"""
        
        # Start with document preamble
        latex = self._generate_preamble()
        
        # Begin document
        latex += "\\begin{document}\n\n"
        
        # Title page
        latex += self._generate_title_page()
        
        # Table of contents
        latex += "\\tableofcontents\n\\newpage\n\n"
        
        # Process each chapter
        for chapter in chapters:
            latex += self._generate_chapter(chapter)
        
        # End document
        latex += "\\end{document}\n"
        
        return latex
    
    def generate_document_latex(self, document: EnhancedSCPDocument) -> str:
        """Generate LaTeX content for a single SCP document (without preamble)"""
        latex = ""
        previous_scp = self.current_scp_number
        self.current_scp_number = document.scp_number

        try:
            # Clean and add SCP number and title
            clean_title = self._clean_wikidot_title(document.title)
            if clean_title:
                latex += f"\\section{{{document.scp_number}: {self._escape_latex(clean_title)}}}\n\n"
            else:
                latex += f"\\section{{{document.scp_number}}}\n\n"

            # Add image if available (float right, before content)
            images = self.image_map.get(document.scp_number, [])
            if images:
                latex += self._generate_image_latex(images[0], document.scp_number)

            # Add object class if available
            if document.object_class and document.object_class.strip():
                latex += f"\\objectclass{{{self._escape_latex(document.object_class)}}}\n\n"

            # Process each section
            for section in document.sections:
                latex += self._generate_section_latex(section)

            # Add includes and modules as comments for reference
            if document.includes:
                latex += "% Includes referenced in original document:\n"
                for include in document.includes[:3]:  # Limit to avoid clutter
                    component = include.attributes.get('component', 'unknown')
                    latex += f"%   - {component}\n"
                latex += "\n"
        finally:
            self.current_scp_number = previous_scp

        return latex
    
    def generate_book_with_includes(self, chapters: List[Dict[str, Any]], latex_files: Dict[str, str]) -> str:
        """Generate complete LaTeX book using include files"""
        
        # Start with document preamble
        latex = self._generate_preamble()
        
        # Begin document
        latex += "\\begin{document}\n\n"
        
        # Title page
        latex += self._generate_title_page()
        
        # Table of contents
        latex += "\\tableofcontents\n\\newpage\n\n"
        
        # Process each chapter using includes
        for chapter in chapters:
            latex += self._generate_chapter_with_includes(chapter, latex_files)
        
        # End document
        latex += "\\end{document}\n"
        
        return latex
    
    def _generate_chapter_with_includes(self, chapter: Dict[str, Any], latex_files: Dict[str, str]) -> str:
        """Generate a chapter using include statements for individual SCPs"""
        
        latex = f"\\scpchapter{{{self._escape_latex(chapter['title'])}}}\n\n"

        # Include each SCP document in this chapter
        for document in chapter['documents']:
            key = document.metadata.get('page_slug') if getattr(document, 'metadata', None) else None
            if not key:
                key = document.scp_number

            if key in latex_files:
                # Use include for the individual LaTeX file
                include_path = latex_files[key]
                # Remove .tex extension for include command
                include_name = include_path.replace('.tex', '')
                latex += f"\\input{{{include_name}}}\n\n"
            else:
                # Fallback: generate inline (shouldn't happen)
                latex += f"% Could not find include file for {document.scp_number}\n"
                latex += self.generate_document_latex(document)
        
        latex += "\\newpage\n\n"
        return latex
    
    def _generate_preamble(self) -> str:
        """Generate LaTeX document preamble — delegates styling to theme .sty files"""

        theme = self.theme
        preamble = f"""\\documentclass[{self.config.font_size},{self.config.paper_size}]{{{self.config.document_class}}}

% Theme: {theme}
% scpbase provides all semantic commands/environments with minimal defaults.
% The theme package overrides them with visual styling.
\\usepackage{{scpbase}}
\\usepackage{{{theme}}}

"""
        return preamble
    
    def _generate_title_page(self) -> str:
        """Generate the book title page — delegates to theme's \\scptitlepage command"""
        title = self._escape_latex(self.config.title)
        subtitle = self._escape_latex(self.config.subtitle)
        author = self._escape_latex(self.config.author)
        return f"\\scptitlepage{{{title}}}{{{subtitle}}}{{{author}}}\n\n"
    
    def _generate_chapter(self, chapter: Dict[str, Any]) -> str:
        """Generate LaTeX for a single chapter"""
        latex = f"\\scpchapter{{{self._escape_latex(chapter['title'])}}}\n\n"
        
        # Process each SCP in the chapter
        for doc in chapter['documents']:
            if hasattr(doc, 'sections'):  # Enhanced document
                latex += self._generate_enhanced_scp_section(doc)
            else:  # Legacy document format
                latex += self._generate_legacy_scp_section(doc)
            latex += "\n\\newpage\n\n"
        
        return latex
    
    def _generate_enhanced_scp_section(self, doc: EnhancedSCPDocument) -> str:
        """Generate LaTeX for an enhanced SCP document"""
        previous_scp = self.current_scp_number
        self.current_scp_number = doc.scp_number

        try:
            latex = f"\\section{{{doc.scp_number}}}\n\n"

            # Add title if present
            if doc.title and not doc.title.startswith('[['):
                latex += f"\\textit{{{self._escape_latex(doc.title)}}}\\\\[0.5cm]\n\n"

            # Object Class
            if doc.object_class:
                latex += f"\\objectclass{{{self._escape_latex(doc.object_class)}}}\n\n"

            # Process sections
            for section in doc.sections:
                latex += self._generate_section_latex(section)
        finally:
            self.current_scp_number = previous_scp

        return latex
    
    def _generate_section_latex(self, section: SCPSection) -> str:
        """Generate LaTeX for a document section"""
        
        # Section header
        if section.section_type == 'containment':
            latex = "\\containment\n\n"
        elif section.section_type == 'description':
            latex = "\\scpdescription\n\n"
        elif section.section_type == 'addendum':
            latex = f"\\addendum{{{self._escape_latex(section.title)}}}\n\n"
        else:
            latex = f"\\textbf{{{self._escape_latex(section.title)}}}\\n\n"
        
        # Process content blocks
        for block in section.content_blocks:
            latex += self._generate_content_block_latex(block)
            latex += "\n\n"
        
        return latex
    
    def _generate_content_block_latex(self, block: ContentBlock) -> str:
        """Generate LaTeX for a content block"""
        
        # Handle null type blocks
        if block.type is None:
            return self._process_text_content(block.content) if block.content else ""
        
        if block.type.value == 'paragraph':
            return self._process_text_content(block.content)
        
        elif block.type.value == 'list':
            return self._generate_list_latex(block)
        
        elif block.type.value == 'quote_block':
            return self._generate_quote_block_latex(block)
        
        elif block.type.value == 'table':
            return self._generate_table_latex(block)
        
        elif block.type.value == 'divider':
            return "\\hrule\\vspace{0.5cm}"
        
        elif block.type.value == 'include':
            return self._generate_include_latex(block)
        
        else:
            # Fallback to text processing
            return self._process_text_content(block.content)
    
    def _generate_list_latex(self, block: ContentBlock) -> str:
        """Generate LaTeX for list blocks"""
        
        items = block.attributes.get('items', [])
        if not items:
            return self._process_text_content(block.content)
        
        latex = "\\begin{itemize}\n"
        for item in items:
            latex += f"\\item {self._process_text_content(item)}\n"
        latex += "\\end{itemize}"
        
        return latex
    
    def _generate_quote_block_latex(self, block: ContentBlock) -> str:
        """Generate LaTeX for quote blocks with enhanced dialogue handling"""
        
        quote_type = block.attributes.get('quote_type')
        has_dialogue = 'dialogue' in block.formatting
        
        if has_dialogue:
            return self._generate_dialogue_latex(block)
        else:
            # Regular quote block
            content = self._process_text_content(block.content)
            return f"\\begin{{scpquote}}\n{content}\n\\end{{scpquote}}"
    
    def _generate_dialogue_latex(self, block: ContentBlock) -> str:
        """Generate LaTeX for dialogue blocks"""
        
        latex = "\\begin{scpdialogue}\n"
        
        # Add header if quote type is detected
        quote_type = block.attributes.get('quote_type')
        if quote_type:
            latex += f"\\logheader{{{quote_type.title()} Log}}\n\n"
        
        dialogue_lines = block.attributes.get('dialogue', [])
        
        if dialogue_lines:
            # Process structured dialogue
            for dialogue in dialogue_lines:
                speaker = dialogue['speaker']
                text = dialogue['text']
                stage_direction = dialogue.get('stage_direction')
                
                # Format speaker and text
                latex += f"\\speaker{{{self._escape_latex(speaker)}}} "
                latex += self._process_text_content(text)
                
                # Add stage direction if present
                if stage_direction:
                    latex += f" \\textit{{({self._escape_latex(stage_direction)})}}"
                
                latex += "\n\n"
        else:
            # Fallback to processing the raw content
            content = self._process_text_content(block.content)
            latex += content
        
        latex += "\\end{scpdialogue}"
        return latex
    
    def _generate_table_latex(self, block: ContentBlock) -> str:
        """Generate LaTeX for table blocks"""
        
        rows = block.attributes.get('rows', [])
        if not rows:
            return self._process_text_content(block.content)
        
        # Determine number of columns
        max_cols = max(len(row) for row in rows) if rows else 0
        col_spec = '|' + 'l|' * max_cols
        
        latex = f"\\begin{{tabular}}{{{col_spec}}}\n\\hline\n"
        
        for row in rows:
            # Pad row to max columns
            padded_row = row + [''] * (max_cols - len(row))
            processed_row = [self._process_text_content(cell.strip()) for cell in padded_row]
            latex += " & ".join(processed_row) + " \\\\\n\\hline\n"
        
        latex += "\\end{tabular}"
        return latex
    
    def _generate_image_latex(self, image_info: dict, scp_number: str) -> str:
        """Generate LaTeX for an SCP image, right-aligned at full reliability."""
        filename = image_info.get('filename', '')
        caption = image_info.get('caption', '')
        scp_slug = scp_number.lower()
        subdir = image_info.get('location', '')
        img_path = self._relative_image_path(scp_slug, filename, subdir)

        # Avoid wrapfigure at section starts: it can silently drop images when
        # there is no immediate paragraph text to wrap against.
        latex = "\\begin{flushright}\n"
        latex += f"  \\includegraphics[width=0.38\\textwidth]{{{img_path}}}\n"
        if caption:
            clean_caption = self._escape_latex(caption)
            latex += f"  \\\\{{\\footnotesize\\itshape {clean_caption}}}\n"
        latex += "\\end{flushright}\n\n"

        return latex

    def _generate_include_latex(self, block: ContentBlock) -> str:
        """Generate LaTeX for include blocks (placeholders for now)"""
        component = block.attributes.get('component') or block.content or 'unknown'
        image_block = self._parse_image_block_component(component)

        if image_block and self.current_scp_number:
            filename = image_block.get('name', '')
            caption = image_block.get('caption', '')
            align = image_block.get('align', 'center').strip().lower()

            if filename:
                entry = self._find_image_entry(self.current_scp_number, filename)
                scp_slug = self.current_scp_number.lower()
                subdir = entry.get('location', image_block.get('location', ''))
                img_path = self._relative_image_path(scp_slug, filename, subdir)
                width = self._image_width_from_block(image_block.get('width', ''))

                if align == 'left':
                    environment = "flushleft"
                elif align == 'right':
                    environment = "flushright"
                else:
                    environment = "center"

                latex = f"\\begin{{{environment}}}\n"
                latex += f"\\includegraphics[width={width}]{{{img_path}}}\n"
                if caption:
                    clean_caption = self._escape_latex(caption)
                    latex += f"\\\\{{\\footnotesize\\itshape {clean_caption}}}\n"
                latex += f"\\end{{{environment}}}"
                return latex

        if 'image-block' in component:
            # If parsing/image lookup failed, keep an explicit placeholder.
            name = image_block.get('name', 'image') if image_block else block.attributes.get('name', 'image')
            caption = image_block.get('caption', '') if image_block else block.attributes.get('caption', '')
            return f"\\textit{{[Image: {name}]}}\\\\[0.2cm]\n\\textit{{{caption}}}"
        else:
            return f"\\textit{{[Include: {component}]}}"

    def _relative_image_path(self, scp_slug: str, filename: str, subdir: str = "") -> str:
        """Build an image path relative to the main LaTeX directory.

        Prefer output/assets (new location), fall back to output/images (legacy).
        """
        base_new = self.output_dir / "assets" / scp_slug
        base_old = self.output_dir / "images" / scp_slug
        if subdir:
            clean_subdir = subdir.strip("/")
            base_new = base_new / clean_subdir
            base_old = base_old / clean_subdir

        new_path = base_new / filename
        old_path = base_old / filename
        image_path = new_path if new_path.exists() or not old_path.exists() else old_path

        relative_path = os.path.relpath(image_path, self.latex_dir)
        return relative_path.replace(os.sep, "/")

    def _parse_image_block_component(self, component: str) -> Dict[str, str]:
        """Parse component:image-block include strings into key/value params."""
        if not component or "component:image-block" not in component:
            return {}

        params: Dict[str, str] = {}
        raw_params = component.split("component:image-block", 1)[1].strip()
        if not raw_params:
            return params

        for field in raw_params.split('|'):
            field = field.strip()
            if not field or '=' not in field:
                continue
            key, value = field.split('=', 1)
            params[key.strip().lower()] = value.strip()

        return params

    def _find_image_entry(self, scp_number: str, filename: str) -> Dict[str, Any]:
        """Find image metadata entry for filename under a given SCP."""
        for image in self.image_map.get(scp_number, []):
            if image.get('filename', '').lower() == filename.lower():
                return image
        return {}

    def _image_width_from_block(self, raw_width: str) -> str:
        """Convert wiki width hints (e.g. 150px) to LaTeX textwidth fractions."""
        default_width = "0.36\\textwidth"
        if not raw_width:
            return default_width

        width = raw_width.strip().lower()
        if width.endswith('px'):
            try:
                px = int(width[:-2])
                fraction = max(0.22, min(0.62, px / 420.0))
                return f"{fraction:.2f}\\textwidth"
            except ValueError:
                return default_width

        if width.endswith('%'):
            try:
                pct = float(width[:-1])
                fraction = max(0.22, min(0.8, pct / 100.0))
                return f"{fraction:.2f}\\textwidth"
            except ValueError:
                return default_width

        return raw_width
    
    def _process_text_content(self, text: str) -> str:
        """Process and format text content for LaTeX"""
        if not text:
            return ""
        
        # Escape LaTeX special characters
        text = self._escape_latex(text)
        
        # Process wikidot formatting
        text = self._convert_wikidot_formatting(text)
        
        # Handle paragraphs
        text = self._format_paragraphs(text)
        
        return text
    
    def _convert_wikidot_formatting(self, text: str) -> str:
        """Convert wikidot markup to LaTeX"""
        
        # Bold text: **text** -> \textbf{text}
        text = re.sub(r'\*\*([^*]+)\*\*', r'\\textbf{\1}', text)
        
        # Italic text: //text// -> \textit{text}  
        text = re.sub(r'//([^/]+)//', r'\\textit{\1}', text)
        
        # Handle footnotes
        text = re.sub(r'\[\[footnote\]\]([^\[]+)\[\[/footnote\]\]', 
                     self._convert_footnote, text)
        
        return text
    
    def _convert_footnote(self, match) -> str:
        """Convert a footnote to LaTeX"""
        self.footnote_counter += 1
        footnote_text = self._escape_latex(match.group(1))
        return f"\\footnote{{{footnote_text}}}"
    
    def _format_paragraphs(self, text: str) -> str:
        """Format paragraph breaks for LaTeX"""
        # Double newlines become paragraph breaks
        text = re.sub(r'\n\n+', '\n\n', text)
        return text
    
    def _clean_wikidot_title(self, title: str) -> str:
        """Clean wikidot markup from titles"""
        if not title:
            return ""

        # Remove [[include ...]] tags (including multi-line)
        title = re.sub(r'\[\[include\s+[^\]]*\]\]', '', title, flags=re.IGNORECASE | re.DOTALL)

        # Remove partial [[include tags (when title gets truncated mid-tag)
        title = re.sub(r'\[\[include\s+.*', '', title, flags=re.IGNORECASE | re.DOTALL)

        # Remove [[module ...]] tags
        title = re.sub(r'\[\[module[^\]]*\]\]', '', title, flags=re.IGNORECASE)

        # Remove [[size ...]]...[[/size]] hidden text
        title = re.sub(r'\[\[size\s+0%?\]\].*?\[\[/size\]\]', '', title, flags=re.DOTALL)

        # Remove [[>]] alignment and similar
        title = re.sub(r'\[\[/?>\]\]', '', title)

        # Remove other [[...]] tags
        title = re.sub(r'\[\[[^\]]*\]\]', '', title)

        # Remove anything starting with [[ (incomplete tags)
        title = re.sub(r'\[\[.*', '', title, flags=re.DOTALL)

        # Clean up whitespace
        title = ' '.join(title.split())

        return title.strip()

    def _clean_wikidot_content(self, text: str) -> str:
        """Clean wikidot markup from content"""
        if not text:
            return ""

        # Remove [[size 0%]]...[[/size]] hidden text
        text = re.sub(r'\[\[size\s+0%?\]\].*?\[\[/size\]\]', '', text, flags=re.DOTALL)

        # Remove [[>]] and [[/>]] alignment tags
        text = re.sub(r'\[\[>?\]\]', '', text)
        text = re.sub(r'\[\[/>\]\]', '', text)

        # Remove [[include component:image-block ...]] (for now, handle images later)
        text = re.sub(r'\[\[include\s+component:image-block[^\]]*\]\]', '[Image]', text, flags=re.IGNORECASE)

        # Remove other [[include ...]] tags
        text = re.sub(r'\[\[include[^\]]*\]\]', '', text, flags=re.IGNORECASE)

        # Remove [[collapsible ...]]...[[/collapsible]] - keep the content
        text = re.sub(r'\[\[collapsible[^\]]*\]\]', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\[\[/collapsible\]\]', '', text, flags=re.IGNORECASE)

        # Remove [[*user Username]] and [[user Username]] - replace with just username
        text = re.sub(r'\[\[\*?user\s+([^\]]+)\]\]', r'\1', text, flags=re.IGNORECASE)

        # Remove [[span ...]]...[[/span]]
        text = re.sub(r'\[\[span[^\]]*\]\]', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\[\[/span\]\]', '', text, flags=re.IGNORECASE)

        # Remove [[div ...]]...[[/div]]
        text = re.sub(r'\[\[div[^\]]*\]\]', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\[\[/div\]\]', '', text, flags=re.IGNORECASE)

        # Remove [[footnote]]...[[/footnote]] - handle footnotes separately
        text = re.sub(r'\[\[footnote\]\](.*?)\[\[/footnote\]\]', r' [note: \1]', text, flags=re.DOTALL)

        # Remove [[[link|text]]] wiki links - keep the text
        text = re.sub(r'\[\[\[([^\]|]+)\|([^\]]+)\]\]\]', r'\2', text)
        text = re.sub(r'\[\[\[([^\]]+)\]\]\]', r'\1', text)

        # Remove [http://... text] external links - keep the text
        text = re.sub(r'\[https?://[^\s\]]+\s+([^\]]+)\]', r'\1', text)
        text = re.sub(r'\[https?://[^\]]+\]', '[link]', text)

        return text

    def _escape_latex(self, text: str) -> str:
        """Escape special LaTeX characters"""
        if not text:
            return ""

        # First clean wikidot markup
        text = self._clean_wikidot_content(text)

        # Convert runs of █ characters to placeholders (protected from escaping)
        redact_placeholders = []
        def _redact_replace(m):
            idx = len(redact_placeholders)
            redact_placeholders.append(len(m.group(0)))
            return f'REDACTPLACEHOLDER{idx}ENDPLACEHOLDER'
        text = re.sub(r'█+', _redact_replace, text)

        # LaTeX special characters - order matters!
        replacements = [
            ('\\\\', '\\textbackslash{}'),
            ('&', '\\&'),
            ('%', '\\%'),
            ('$', '\\$'),
            ('#', '\\#'),
            ('^', '\\textasciicircum{}'),
            ('_', '\\_'),
            ('{', '\\{'),
            ('}', '\\}'),
            ('~', '\\textasciitilde{}'),
            ('<', '\\textless{}'),
            ('>', '\\textgreater{}'),
            # Greek letters commonly seen
            ('ρ', '$\\rho$'),
            ('α', '$\\alpha$'),
            ('β', '$\\beta$'),
            ('γ', '$\\gamma$'),
            ('δ', '$\\delta$'),
            ('π', '$\\pi$'),
            ('Ω', '$\\Omega$'),
        ]

        for char, replacement in replacements:
            text = text.replace(char, replacement)

        # Restore redaction placeholders as \redact{N} commands
        for idx, count in enumerate(redact_placeholders):
            text = text.replace(
                f'REDACTPLACEHOLDER{idx}ENDPLACEHOLDER',
                f'\\redact{{{count}}}'
            )

        return text
    
    def _generate_legacy_scp_section(self, doc) -> str:
        """Generate LaTeX for legacy document format (fallback)"""
        # This would use the old converter logic
        from latex_pipeline.converter import LaTeXConverter
        old_converter = LaTeXConverter(self.config)
        return old_converter._generate_scp_basic_style(doc)


def main():
    """Test the enhanced converter"""
    from parsers.enhanced_wikidot_parser import EnhancedWikidotParser
    from pipeline.builder import PipelineConfig
    
    # Test with enhanced document
    parser = EnhancedWikidotParser()
    doc = parser.parse_file('downloads/scp-5370.txt')
    
    config = PipelineConfig()
    converter = EnhancedLaTeXConverter(config)
    
    chapters = [{'title': 'Test Chapter', 'documents': [doc]}]
    latex = converter.generate_book(chapters)
    
    print(latex[:2000])  # Show first 2000 characters


if __name__ == "__main__":
    main()

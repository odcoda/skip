#!/usr/bin/env python3
"""
Enhanced LaTeX Converter

Converts the enhanced semantic SCP structure to well-formatted LaTeX
with proper handling of dialogue, quote blocks, and complex formatting.
"""

import re
import os
from typing import List, Dict, Any
from parsers.enhanced_wikidot_parser import EnhancedSCPDocument, ContentBlock, SCPSection


class EnhancedLaTeXConverter:
    """Converts enhanced SCP documents to LaTeX with semantic formatting"""
    
    def __init__(self, config):
        self.config = config
        self.footnote_counter = 0
        
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
        
        # Add SCP number and title
        latex += f"\\section{{{document.scp_number}: {self._escape_latex(document.title)}}}\n\n"
        
        # Add object class if available
        if document.object_class and document.object_class.strip():
            latex += f"\\textbf{{Object Class:}} {self._escape_latex(document.object_class)}\n\n"
        
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
        
        latex = f"\\chapter{{{self._escape_latex(chapter['title'])}}}\n\n"
        
        # Include each SCP document in this chapter
        for document in chapter['documents']:
            if document.scp_number in latex_files:
                # Use include for the individual LaTeX file
                include_path = latex_files[document.scp_number]
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
        """Generate LaTeX document preamble with enhanced packages"""
        
        preamble = f"""\\documentclass[{self.config.font_size},{self.config.paper_size}]{{{self.config.document_class}}}

% Basic packages
\\usepackage[utf8]{{inputenc}}
\\usepackage[T1]{{fontenc}}
\\usepackage{{lmodern}}
\\usepackage{{geometry}}
\\usepackage{{fancyhdr}}
\\usepackage{{graphicx}}
\\usepackage{{float}}
\\usepackage{{hyperref}}
\\usepackage{{amsmath}}
\\usepackage{{amsfonts}}
\\usepackage{{xcolor}}
\\usepackage{{multicol}}
\\usepackage{{wrapfig}}
\\usepackage{{enumitem}}
\\usepackage{{changepage}}
\\usepackage{{framed}}

% Page layout
\\geometry{{margin=1in, headheight=15pt}}

% Headers and footers
\\pagestyle{{fancy}}
\\fancyhf{{}}
\\fancyhead[LE,RO]{{\\thepage}}
\\fancyhead[LO,RE]{{SCP Foundation Archive}}

% Custom commands for SCP formatting
\\newcommand{{\\scpnumber}}[1]{{\\textbf{{\\large #1}}}}
\\newcommand{{\\objectclass}}[1]{{\\textbf{{Object Class:}} #1}}
\\newcommand{{\\containment}}{{\\textbf{{Special Containment Procedures:}}}}
\\newcommand{{\\scpdescription}}{{\\textbf{{Description:}}}}
\\newcommand{{\\addendum}}[1]{{\\textbf{{Addendum #1:}}}}

% Enhanced formatting for dialogue and quotes
\\definecolor{{quotebg}}{{RGB}}{{248, 248, 248}}
\\definecolor{{dialoguebg}}{{RGB}}{{240, 245, 255}}
\\definecolor{{scpred}}{{RGB}}{{187, 0, 0}}
\\definecolor{{scpgray}}{{RGB}}{{102, 102, 102}}

% Quote block environment
\\newenvironment{{scpquote}}
{{\\begin{{adjustwidth}}{{0.5cm}}{{0.5cm}}\\begin{{leftbar}}\\small}}
{{\\end{{leftbar}}\\end{{adjustwidth}}}}

% Dialogue environment
\\newenvironment{{scpdialogue}}
{{\\begin{{adjustwidth}}{{1cm}}{{1cm}}\\small\\color{{black}}}}
{{\\end{{adjustwidth}}}}

% Speaker command for dialogue
\\newcommand{{\\speaker}}[1]{{\\textbf{{#1:}}}}

% Experiment/log header
\\newcommand{{\\logheader}}[1]{{\\textbf{{#1}}\\\\[0.3cm]}}

% Redaction black box (for redacted text like dates and names)
\\newcommand{{\\blackbox}}{{\\rule{{1ex}}{{1.2ex}}}}

"""

        # Add RPG styling if enabled
        if self.config.use_rpg_styling:
            preamble += self._get_rpg_styling()
        
        return preamble
    
    def _get_rpg_styling(self) -> str:
        """Additional styling for fantasy RPG appearance"""
        return """
% RPG-style packages
\\usepackage{tcolorbox}
\\usepackage{tikz}

% Custom colors for RPG style
\\definecolor{parchment}{RGB}{255, 248, 220}
\\definecolor{darkbrown}{RGB}{101, 67, 33}
\\definecolor{burgundy}{RGB}{128, 0, 32}

% Enhanced SCP box styling
\\newtcolorbox{scpbox}{
    colback=parchment,
    colframe=darkbrown,
    boxrule=2pt,
    arc=5pt,
    left=10pt,
    right=10pt,
    top=10pt,
    bottom=10pt
}

"""
    
    def _generate_title_page(self) -> str:
        """Generate the book title page"""
        return f"""
\\title{{{self.config.title}}}
\\author{{{self.config.author}}}
\\date{{\\today}}

\\maketitle
\\thispagestyle{{empty}}

\\vspace*{{\\fill}}
\\begin{{center}}
\\textit{{{self.config.subtitle}}}

\\vspace{{1cm}}

\\textbf{{CLASSIFIED}} \\\\
\\textbf{{LEVEL 4 CLEARANCE REQUIRED}}

\\vspace{{0.5cm}}

\\textit{{Property of the SCP Foundation}} \\\\
\\textit{{Unauthorized access is prohibited}}
\\end{{center}}
\\vspace*{{\\fill}}

\\newpage

"""
    
    def _generate_chapter(self, chapter: Dict[str, Any]) -> str:
        """Generate LaTeX for a single chapter"""
        latex = f"\\chapter{{{chapter['title']}}}\n\n"
        
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
        
        if self.config.use_rpg_styling:
            latex = "\\begin{scpbox}\n"
        else:
            latex = ""
        
        latex += f"\\section{{{doc.scp_number}}}\n\n"
        
        # Add title if present
        if doc.title and not doc.title.startswith('[['):
            latex += f"\\textit{{{self._escape_latex(doc.title)}}}\\\\[0.5cm]\n\n"
        
        # Object Class
        if doc.object_class:
            latex += f"\\objectclass{{{doc.object_class}}}\\\\[0.3cm]\n\n"
        
        # Process sections
        for section in doc.sections:
            latex += self._generate_section_latex(section)
        
        if self.config.use_rpg_styling:
            latex += "\\end{scpbox}\n"
        
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
    
    def _generate_include_latex(self, block: ContentBlock) -> str:
        """Generate LaTeX for include blocks (placeholders for now)"""
        
        component = block.attributes.get('component', 'unknown')
        
        if 'image-block' in component:
            # Handle image includes
            name = block.attributes.get('name', 'image')
            caption = block.attributes.get('caption', '')
            
            return f"\\textit{{[Image: {name}]}}\\\\[0.2cm]\n\\textit{{{caption}}}"
        else:
            return f"\\textit{{[Include: {component}]}}"
    
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
    
    def _escape_latex(self, text: str) -> str:
        """Escape special LaTeX characters"""
        if not text:
            return ""

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
            # Unicode redaction characters - convert to black boxes
            ('█', '\\blackbox{}'),
        ]

        for char, replacement in replacements:
            text = text.replace(char, replacement)

        return text
    
    def _generate_legacy_scp_section(self, doc) -> str:
        """Generate LaTeX for legacy document format (fallback)"""
        # This would use the old converter logic
        from latex.converter import LaTeXConverter
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
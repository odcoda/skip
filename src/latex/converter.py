#!/usr/bin/env python3
"""
LaTeX Converter for SCP Documents

Converts structured SCP documents to LaTeX format with configurable styling.
Designed to support both basic academic formatting and fantasy RPG aesthetics.
"""

import re
import os
from typing import List, Dict, Any
from parsers.wikidot_parser import SCPDocument, SCPElement


class LaTeXConverter:
    """Converts SCP documents to LaTeX format"""
    
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
    
    def _generate_preamble(self) -> str:
        """Generate LaTeX document preamble with packages and styling"""
        
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

% SCP-specific styling
\\definecolor{{scpred}}{{RGB}}{{187, 0, 0}}
\\definecolor{{scpgray}}{{RGB}}{{102, 102, 102}}

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
\\usepackage{fontspec}  % For custom fonts
\\usepackage{tikz}
\\usepackage{pgfornament}

% Custom colors for RPG style
\\definecolor{parchment}{RGB}{255, 248, 220}
\\definecolor{darkbrown}{RGB}{101, 67, 33}
\\definecolor{burgundy}{RGB}{128, 0, 32}

% SCP box styling
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

% Decorative elements
\\newcommand{\\ornament}{\\pgfornament[width=2cm]{61}}

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
            latex += self._generate_scp_section(doc)
            latex += "\n\\newpage\n\n"  # Each SCP on new page
        
        return latex
    
    def _generate_scp_section(self, doc: SCPDocument) -> str:
        """Generate LaTeX for a single SCP document"""
        
        if self.config.use_rpg_styling:
            return self._generate_scp_rpg_style(doc)
        else:
            return self._generate_scp_basic_style(doc)
    
    def _generate_scp_basic_style(self, doc: SCPDocument) -> str:
        """Generate basic academic-style LaTeX for SCP"""
        
        latex = f"\\section{{{doc.scp_number}}}\n\n"
        
        # Add title if present
        if doc.title:
            latex += f"\\textit{{{self._escape_latex(doc.title)}}}\\\\[0.5cm]\n\n"
        
        # Object Class
        if doc.object_class:
            latex += f"\\objectclass{{{doc.object_class}}}\\\\[0.3cm]\n\n"
        
        # Containment Procedures
        if doc.containment_procedures:
            latex += "\\containment\n\n"
            latex += self._process_text_content(doc.containment_procedures)
            latex += "\n\n"
        
        # Description
        if doc.description:
            latex += "\\scpdescription\n\n"
            latex += self._process_text_content(doc.description)
            latex += "\n\n"
        
        # Addenda
        for addendum in doc.addenda:
            latex += f"\\addendum{{{self._escape_latex(addendum['title'])}}}\n\n"
            latex += self._process_text_content(addendum['content'])
            latex += "\n\n"
        
        return latex
    
    def _generate_scp_rpg_style(self, doc: SCPDocument) -> str:
        """Generate RPG-style LaTeX for SCP"""
        
        latex = "\\begin{scpbox}\n"
        latex += f"\\scpnumber{{{doc.scp_number}}}\n\n"
        
        # Add decorative element
        latex += "\\begin{center}\\ornament\\end{center}\n\n"
        
        # Rest similar to basic style but within the styled box
        if doc.title:
            latex += f"\\textit{{{self._escape_latex(doc.title)}}}\\\\[0.5cm]\n\n"
        
        if doc.object_class:
            latex += f"\\textcolor{{burgundy}}{{\\textbf{{Object Class:}}}} {doc.object_class}\\\\[0.3cm]\n\n"
        
        # Continue with other sections...
        latex += "\\end{scpbox}\n"
        
        return latex
    
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
        
        # Handle bullet points
        text = re.sub(r'^\* (.+)$', r'\\item \1', text, flags=re.MULTILINE)
        
        # Wrap bullet point sections in itemize
        text = self._wrap_itemize_blocks(text)
        
        return text
    
    def _convert_footnote(self, match) -> str:
        """Convert a footnote to LaTeX"""
        self.footnote_counter += 1
        footnote_text = self._escape_latex(match.group(1))
        return f"\\footnote{{{footnote_text}}}"
    
    def _wrap_itemize_blocks(self, text: str) -> str:
        """Wrap consecutive \\item lines in itemize environment"""
        lines = text.split('\n')
        result = []
        in_itemize = False
        
        for line in lines:
            if line.strip().startswith('\\item'):
                if not in_itemize:
                    result.append('\\begin{itemize}')
                    in_itemize = True
                result.append(line)
            else:
                if in_itemize:
                    result.append('\\end{itemize}')
                    in_itemize = False
                result.append(line)
        
        # Close itemize if still open
        if in_itemize:
            result.append('\\end{itemize}')
        
        return '\n'.join(result)
    
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
            ('\\', '\\textbackslash{}'),
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
            ('>', '\\textgreater{}')
        ]
        
        for char, replacement in replacements:
            text = text.replace(char, replacement)
        
        return text


def main():
    """Test the converter with a sample document"""
    from parsers.wikidot_parser import WikidotParser, SCPDocument
    from pipeline.builder import PipelineConfig
    
    # Create a test document
    test_doc = SCPDocument(
        scp_number="SCP-TEST",
        title="Test Object",
        object_class="Safe",
        containment_procedures="Keep in a box.",
        description="This is a **test** object with //some// formatting."
    )
    
    config = PipelineConfig()
    converter = LaTeXConverter(config)
    
    # Generate LaTeX for test
    chapters = [{'title': 'Test Chapter', 'documents': [test_doc]}]
    latex = converter.generate_book(chapters)
    
    print(latex)


if __name__ == "__main__":
    main()
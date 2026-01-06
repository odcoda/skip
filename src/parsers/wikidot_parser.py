#!/usr/bin/env python3
"""
Wikidot Parser for SCP Foundation Articles

This module parses wikidot markup from SCP Foundation articles and converts
them to a structured intermediate format that can be processed by the LaTeX
generation pipeline.
"""

import re
import json
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict


@dataclass
class SCPElement:
    """Base class for all SCP document elements"""
    element_type: str
    content: str = ""
    attributes: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.attributes is None:
            self.attributes = {}


@dataclass 
class SCPDocument:
    """Represents a complete SCP document"""
    scp_number: str
    title: str = ""
    object_class: str = ""
    containment_procedures: str = ""
    description: str = ""
    addenda: List[Dict[str, Any]] = None
    elements: List[SCPElement] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.addenda is None:
            self.addenda = []
        if self.elements is None:
            self.elements = []
        if self.metadata is None:
            self.metadata = {}


class WikidotParser:
    """Parser for SCP Foundation wikidot markup"""
    
    def __init__(self):
        self.current_scp = None
        
    def parse_file(self, filepath: str) -> SCPDocument:
        """Parse a wikidot source file and return structured SCP document"""
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        return self.parse_content(content, filepath)
    
    def parse_content(self, content: str, source_file: str = "") -> SCPDocument:
        """Parse wikidot content string and return structured SCP document"""
        
        # Extract SCP number from content or filename
        scp_number = self._extract_scp_number(content, source_file)
        
        # Initialize document
        doc = SCPDocument(scp_number=scp_number)
        doc.metadata['source_file'] = source_file
        
        # Parse main sections
        doc.title = self._extract_title(content)
        doc.object_class = self._extract_object_class(content)
        doc.containment_procedures = self._extract_containment_procedures(content)
        doc.description = self._extract_description(content)
        doc.addenda = self._extract_addenda(content)
        
        # Parse all elements for detailed processing
        doc.elements = self._parse_elements(content)
        
        return doc
    
    def _extract_scp_number(self, content: str, source_file: str) -> str:
        """Extract SCP number from content or filename"""
        
        # Try to find in content first
        item_match = re.search(r'\*\*Item #:\*\* (SCP-\d+)', content)
        if item_match:
            return item_match.group(1)
        
        # Try filename
        filename_match = re.search(r'scp-(\d+)', source_file.lower())
        if filename_match:
            return f"SCP-{filename_match.group(1)}"
        
        return "SCP-UNKNOWN"
    
    def _extract_title(self, content: str) -> str:
        """Extract page title if present"""
        # Look for page titles in various formats
        patterns = [
            r'^\s*([^*\[].+?)\s*$',  # Simple title line
            r'\[\[.*title\s*=\s*([^\]]+)\]\]'  # Include title attribute
        ]
        
        lines = content.split('\n')
        for line in lines[:10]:  # Check first 10 lines
            if line.strip() and not line.startswith(('[[', '**', '>', '#')):
                if len(line.strip()) < 100:  # Reasonable title length
                    return line.strip()
        
        return ""
    
    def _extract_object_class(self, content: str) -> str:
        """Extract Object Class from content"""
        match = re.search(r'\*\*Object Class:\*\*\s*(\w+)', content)
        return match.group(1) if match else ""
    
    def _extract_containment_procedures(self, content: str) -> str:
        """Extract Special Containment Procedures section"""
        pattern = r'\*\*Special Containment Procedures:\*\*(.*?)(?=\*\*[^*]|\[\[|$)'
        match = re.search(pattern, content, re.DOTALL)
        if match:
            return self._clean_text(match.group(1))
        return ""
    
    def _extract_description(self, content: str) -> str:
        """Extract Description section"""
        pattern = r'\*\*Description:\*\*(.*?)(?=\*\*Addendum|@@\s*@@|$)'
        match = re.search(pattern, content, re.DOTALL)
        if match:
            return self._clean_text(match.group(1))
        return ""
    
    def _extract_addenda(self, content: str) -> List[Dict[str, Any]]:
        """Extract all addenda sections"""
        addenda = []
        
        # Look for addendum patterns - be more inclusive in what we capture
        addendum_pattern = r'\*\*Addendum ([^:*]+):\*\*(.*?)(?=\*\*Addendum|\[\[footnoteblock\]\]|\[\[include component:license-box\]\]|$)'
        matches = re.finditer(addendum_pattern, content, re.DOTALL)
        
        for match in matches:
            addendum = {
                'title': match.group(1).strip(),
                'content': self._clean_text(match.group(2))
            }
            addenda.append(addendum)
        
        return addenda
    
    def _parse_elements(self, content: str) -> List[SCPElement]:
        """Parse all document elements for detailed processing"""
        elements = []
        
        # Parse includes
        include_pattern = r'\[\[include\s+([^\]]+)\]\]'
        for match in re.finditer(include_pattern, content):
            elements.append(SCPElement(
                element_type="include",
                content=match.group(1).strip(),
                attributes=self._parse_include_attributes(match.group(1))
            ))
        
        # Parse footnotes
        footnote_pattern = r'\[\[footnote\]\](.*?)\[\[/footnote\]\]'
        for match in re.finditer(footnote_pattern, content, re.DOTALL):
            elements.append(SCPElement(
                element_type="footnote",
                content=self._clean_text(match.group(1))
            ))
        
        # Parse modules
        module_pattern = r'\[\[module\s+([^\]]+)\]\]'
        for match in re.finditer(module_pattern, content):
            elements.append(SCPElement(
                element_type="module",
                content=match.group(1).strip()
            ))
        
        # Parse formatting elements
        elements.extend(self._parse_formatting(content))
        
        return elements
    
    def _parse_include_attributes(self, include_content: str) -> Dict[str, Any]:
        """Parse attributes from include statement"""
        attributes = {}
        
        # Split on whitespace and parse key=value pairs
        parts = include_content.split()
        if parts:
            attributes['component'] = parts[0]
            
            for part in parts[1:]:
                if '=' in part:
                    key, value = part.split('=', 1)
                    attributes[key] = value.strip('|')
        
        return attributes
    
    def _parse_formatting(self, content: str) -> List[SCPElement]:
        """Parse formatting elements like bold, italic, etc."""
        elements = []
        
        # Bold text
        for match in re.finditer(r'\*\*([^*]+)\*\*', content):
            elements.append(SCPElement(
                element_type="bold",
                content=match.group(1)
            ))
        
        # Italic text  
        for match in re.finditer(r'//([^/]+)//', content):
            elements.append(SCPElement(
                element_type="italic", 
                content=match.group(1)
            ))
        
        return elements
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize text content"""
        # Remove excessive whitespace
        text = re.sub(r'\n\s*\n', '\n\n', text)
        text = re.sub(r'^\s+|\s+$', '', text)
        
        return text
    
    def to_json(self, doc: SCPDocument) -> str:
        """Convert document to JSON format"""
        return json.dumps(asdict(doc), indent=2, ensure_ascii=False)
    
    def save_json(self, doc: SCPDocument, filepath: str):
        """Save document as JSON file"""
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(self.to_json(doc))


def main():
    """Test the parser with a sample file"""
    import sys
    
    if len(sys.argv) != 2:
        print("Usage: python wikidot_parser.py <scp_file.txt>")
        sys.exit(1)
    
    parser = WikidotParser()
    try:
        doc = parser.parse_file(sys.argv[1])
        print(parser.to_json(doc))
    except Exception as e:
        print(f"Error parsing file: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
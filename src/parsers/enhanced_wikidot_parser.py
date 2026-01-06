#!/usr/bin/env python3
"""
Enhanced Wikidot Parser for SCP Foundation Articles

A more sophisticated parser that understands semantic structure and
properly handles complex formatting like dialogue, quote blocks, and
nested content.
"""

import re
import json
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, asdict
from enum import Enum


class ContentType(Enum):
    """Types of content blocks"""
    PARAGRAPH = "paragraph"
    QUOTE_BLOCK = "quote_block"
    DIALOGUE = "dialogue"
    LOG_ENTRY = "log_entry"
    EXPERIMENT = "experiment"
    INTERVIEW = "interview"
    LIST = "list"
    TABLE = "table"
    DIVIDER = "divider"
    INCLUDE = "include"
    MODULE = "module"
    FOOTNOTE = "footnote"


@dataclass
class ContentBlock:
    """Represents a block of content with semantic meaning"""
    type: ContentType
    content: str
    attributes: Dict[str, Any] = None
    formatting: List[str] = None
    
    def __post_init__(self):
        if self.attributes is None:
            self.attributes = {}
        if self.formatting is None:
            self.formatting = []


@dataclass
class DialogueLine:
    """Represents a line of dialogue"""
    speaker: str
    text: str
    stage_direction: Optional[str] = None
    formatting: List[str] = None
    
    def __post_init__(self):
        if self.formatting is None:
            self.formatting = []


@dataclass
class QuoteBlock:
    """Represents a quote block with structured content"""
    content_blocks: List[ContentBlock]
    title: Optional[str] = None
    quote_type: Optional[str] = None  # experiment, interview, log, etc.
    

@dataclass
class SCPSection:
    """Represents a major section of an SCP document"""
    section_type: str  # containment, description, addendum
    title: str
    content_blocks: List[ContentBlock]
    

@dataclass
class EnhancedSCPDocument:
    """Enhanced SCP document with semantic structure"""
    scp_number: str
    title: str = ""
    object_class: str = ""
    sections: List[SCPSection] = None
    includes: List[ContentBlock] = None
    modules: List[ContentBlock] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.sections is None:
            self.sections = []
        if self.includes is None:
            self.includes = []
        if self.modules is None:
            self.modules = []
        if self.metadata is None:
            self.metadata = {}


class EnhancedWikidotParser:
    """Enhanced parser with semantic understanding"""
    
    def __init__(self):
        self.dialogue_speakers = set()
        self.footnote_counter = 0
        
    def parse_file(self, filepath: str) -> EnhancedSCPDocument:
        """Parse a wikidot source file"""
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        return self.parse_content(content, filepath)
    
    def parse_content(self, content: str, source_file: str = "") -> EnhancedSCPDocument:
        """Parse wikidot content with semantic understanding"""
        
        # Extract basic info
        scp_number = self._extract_scp_number(content, source_file)
        doc = EnhancedSCPDocument(scp_number=scp_number)
        doc.metadata['source_file'] = source_file
        
        # Extract title and object class
        doc.title = self._extract_title(content)
        doc.object_class = self._extract_object_class(content)
        
        # Parse includes and modules first (they affect layout)
        doc.includes = self._parse_includes(content)
        doc.modules = self._parse_modules(content)
        
        # Parse main sections
        doc.sections = self._parse_sections(content)
        
        return doc
    
    def _extract_scp_number(self, content: str, source_file: str) -> str:
        """Extract SCP number"""
        item_match = re.search(r'\*\*Item #:\*\*\s*(SCP-\d+)', content)
        if item_match:
            return item_match.group(1)
        
        filename_match = re.search(r'scp-(\d+)', source_file.lower())
        if filename_match:
            return f"SCP-{filename_match.group(1)}"
        
        return "SCP-UNKNOWN"
    
    def _extract_title(self, content: str) -> str:
        """Extract document title"""
        lines = content.split('\n')
        for line in lines[:10]:
            if line.strip() and not line.startswith(('[[', '**', '>', '#', '|')):
                if len(line.strip()) < 100:
                    return line.strip()
        return ""
    
    def _extract_object_class(self, content: str) -> str:
        """Extract object class"""
        match = re.search(r'\*\*Object Class:\*\*\s*(\w+)', content)
        return match.group(1) if match else ""
    
    def _parse_includes(self, content: str) -> List[ContentBlock]:
        """Parse include statements"""
        includes = []
        
        for match in re.finditer(r'\[\[include\s+([^\]]+)\]\]', content, re.DOTALL):
            include_content = match.group(1).strip()
            
            # Parse include attributes
            attributes = self._parse_include_attributes(include_content)
            
            includes.append(ContentBlock(
                type=ContentType.INCLUDE,
                content=include_content,
                attributes=attributes
            ))
        
        return includes
    
    def _parse_modules(self, content: str) -> List[ContentBlock]:
        """Parse module statements"""
        modules = []
        
        for match in re.finditer(r'\[\[module\s+([^\]]+)\]\]', content):
            module_content = match.group(1).strip()
            
            modules.append(ContentBlock(
                type=ContentType.MODULE,
                content=module_content
            ))
        
        return modules
    
    def _parse_sections(self, content: str) -> List[SCPSection]:
        """Parse main document sections"""
        sections = []
        
        # Define section patterns
        section_patterns = [
            (r'\*\*Special Containment Procedures:\*\*', 'containment'),
            (r'\*\*Description:\*\*', 'description'),
            (r'\*\*Addendum ([^:*]+):\*\*', 'addendum'),
        ]
        
        # Find all section boundaries
        section_matches = []
        for pattern, section_type in section_patterns:
            for match in re.finditer(pattern, content):
                section_matches.append({
                    'start': match.start(),
                    'end': match.end(),
                    'type': section_type,
                    'title': match.group(1) if section_type == 'addendum' else section_type,
                    'full_match': match.group(0)
                })
        
        # Sort by position
        section_matches.sort(key=lambda x: x['start'])
        
        # Extract content for each section
        for i, section_match in enumerate(section_matches):
            # Determine content boundaries
            content_start = section_match['end']
            
            # Find content end (next section or end of document)
            if i + 1 < len(section_matches):
                content_end = section_matches[i + 1]['start']
            else:
                # Look for document end markers
                end_markers = [
                    r'\[\[footnoteblock\]\]',
                    r'\[\[include.*license-box.*\]\]',
                    r'\[\[div class="footer-wikiwalk-nav"\]\]'
                ]
                content_end = len(content)
                for marker in end_markers:
                    match = re.search(marker, content[content_start:])
                    if match:
                        content_end = content_start + match.start()
                        break
            
            # Extract and parse section content
            section_content = content[content_start:content_end].strip()
            content_blocks = self._parse_content_blocks(section_content)
            
            sections.append(SCPSection(
                section_type=section_match['type'],
                title=section_match['title'],
                content_blocks=content_blocks
            ))
        
        return sections
    
    def _parse_content_blocks(self, content: str) -> List[ContentBlock]:
        """Parse content into semantic blocks"""
        blocks = []
        lines = content.split('\n')
        
        current_block = []
        current_block_type = None
        in_quote_block = False
        
        i = 0
        while i < len(lines):
            line = lines[i]
            
            # Skip empty lines between blocks
            if not line.strip():
                if current_block and current_block_type is not None:
                    blocks.append(self._finalize_content_block(current_block, current_block_type))
                    current_block = []
                    current_block_type = None
                i += 1
                continue
            
            # Detect block type
            block_type = self._detect_block_type(line)
            
            # Handle quote blocks specially
            if line.startswith('>'):
                if not in_quote_block:
                    # Start of quote block
                    if current_block:
                        blocks.append(self._finalize_content_block(current_block, current_block_type))
                        current_block = []
                    in_quote_block = True
                    current_block_type = ContentType.QUOTE_BLOCK
                
                current_block.append(line)
            else:
                if in_quote_block:
                    # End of quote block
                    blocks.append(self._finalize_content_block(current_block, current_block_type))
                    current_block = []
                    in_quote_block = False
                
                # Handle non-quote content
                if current_block_type is None:
                    current_block_type = block_type
                elif current_block_type != block_type:
                    # Block type changed
                    blocks.append(self._finalize_content_block(current_block, current_block_type))
                    current_block = []
                    current_block_type = block_type
                
                current_block.append(line)
            
            i += 1
        
        # Finalize last block
        if current_block:
            blocks.append(self._finalize_content_block(current_block, current_block_type))
        
        return blocks
    
    def _detect_block_type(self, line: str) -> ContentType:
        """Detect the type of content block"""
        
        if line.startswith('>'):
            return ContentType.QUOTE_BLOCK
        elif line.startswith('* ') or re.match(r'^\d+\.', line):
            return ContentType.LIST
        elif '||' in line:
            return ContentType.TABLE
        elif line.strip() == '----' or '----' in line:
            return ContentType.DIVIDER
        elif line.startswith('[[include'):
            return ContentType.INCLUDE
        elif line.startswith('[[module'):
            return ContentType.MODULE
        else:
            return ContentType.PARAGRAPH
    
    def _finalize_content_block(self, lines: List[str], block_type: ContentType) -> ContentBlock:
        """Convert lines into a finalized content block"""
        
        content = '\n'.join(lines)
        attributes = {}
        formatting = []
        
        if block_type == ContentType.QUOTE_BLOCK:
            # Process quote block specially
            return self._parse_quote_block(lines)
        elif block_type == ContentType.LIST:
            # Extract list items
            items = []
            for line in lines:
                if line.startswith('* '):
                    items.append(line[2:].strip())
                elif re.match(r'^\d+\.', line):
                    items.append(re.sub(r'^\d+\.\s*', '', line))
            attributes['items'] = items
        elif block_type == ContentType.TABLE:
            # Parse table structure
            attributes['rows'] = [line.split('||') for line in lines if '||' in line]
        
        # Detect formatting
        if '**' in content:
            formatting.append('bold')
        if '//' in content:
            formatting.append('italic')
        if '[[footnote]]' in content:
            formatting.append('footnotes')
        
        return ContentBlock(
            type=block_type,
            content=content,
            attributes=attributes,
            formatting=formatting
        )
    
    def _parse_quote_block(self, lines: List[str]) -> ContentBlock:
        """Parse a quote block with special handling for dialogue and structure"""
        
        # Remove '>' prefix and analyze content
        cleaned_lines = [line[1:].strip() if line.startswith('>') else line for line in lines]
        content = '\n'.join(cleaned_lines)
        
        attributes = {}
        formatting = []
        
        # Detect quote block type
        quote_type = self._detect_quote_type(content)
        if quote_type:
            attributes['quote_type'] = quote_type
        
        # Parse dialogue if present
        dialogue_lines = self._parse_dialogue(cleaned_lines)
        if dialogue_lines:
            attributes['dialogue'] = [asdict(d) for d in dialogue_lines]
            formatting.append('dialogue')
        
        # Detect other formatting
        if '**' in content:
            formatting.append('bold')
        if '//' in content:
            formatting.append('italic')
        
        return ContentBlock(
            type=ContentType.QUOTE_BLOCK,
            content=content,
            attributes=attributes,
            formatting=formatting
        )
    
    def _detect_quote_type(self, content: str) -> Optional[str]:
        """Detect the type of quote block"""
        
        content_lower = content.lower()
        
        if any(word in content_lower for word in ['experiment', 'test', 'trial']):
            return 'experiment'
        elif any(word in content_lower for word in ['interview', 'interrogation']):
            return 'interview'
        elif any(word in content_lower for word in ['log', 'transcript', 'recording']):
            return 'log'
        elif any(word in content_lower for word in ['exploration', 'expedition']):
            return 'exploration'
        elif 'incident' in content_lower:
            return 'incident'
        elif any(word in content_lower for word in ['begin log', 'end log', '<begin', '<end']):
            return 'log'
        
        return None
    
    def _parse_dialogue(self, lines: List[str]) -> List[DialogueLine]:
        """Parse dialogue from cleaned quote block lines"""
        
        dialogue_lines = []
        
        for line in lines:
            # Look for dialogue pattern: **SPEAKER:** text
            dialogue_match = re.match(r'\*\*([^*]+):\*\*\s*(.*)', line)
            if dialogue_match:
                speaker = dialogue_match.group(1).strip()
                text = dialogue_match.group(2).strip()
                
                # Extract stage directions
                stage_direction = None
                stage_match = re.search(r'//\(([^)]+)\)//', text)
                if stage_match:
                    stage_direction = stage_match.group(1)
                    text = re.sub(r'//\([^)]+\)//', '', text).strip()
                
                # Track speakers
                self.dialogue_speakers.add(speaker)
                
                dialogue_lines.append(DialogueLine(
                    speaker=speaker,
                    text=text,
                    stage_direction=stage_direction
                ))
        
        return dialogue_lines
    
    def _parse_include_attributes(self, include_content: str) -> Dict[str, Any]:
        """Parse attributes from include statement"""
        attributes = {}
        
        lines = include_content.split('\n')
        if lines:
            # First line is the component name
            attributes['component'] = lines[0].strip()
            
            # Parse key=value pairs
            for line in lines[1:]:
                line = line.strip()
                if '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip().strip('|')
                    value = value.strip().strip('|')
                    attributes[key] = value
        
        return attributes
    
    def to_json(self, doc: EnhancedSCPDocument) -> str:
        """Convert document to JSON"""
        
        def convert_enums(obj):
            """Convert Enums to strings for JSON serialization"""
            if isinstance(obj, dict):
                return {k: convert_enums(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_enums(item) for item in obj]
            elif isinstance(obj, ContentType):
                return obj.value
            else:
                return obj
        
        doc_dict = asdict(doc)
        doc_dict = convert_enums(doc_dict)
        return json.dumps(doc_dict, indent=2, ensure_ascii=False)
    
    def save_json(self, doc: EnhancedSCPDocument, filepath: str):
        """Save document as JSON"""
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(self.to_json(doc))


def main():
    """Test the enhanced parser"""
    import sys
    
    if len(sys.argv) != 2:
        print("Usage: python enhanced_wikidot_parser.py <scp_file.txt>")
        sys.exit(1)
    
    parser = EnhancedWikidotParser()
    try:
        doc = parser.parse_file(sys.argv[1])
        print(parser.to_json(doc))
    except Exception as e:
        print(f"Error parsing file: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
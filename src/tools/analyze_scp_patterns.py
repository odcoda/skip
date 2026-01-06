#!/usr/bin/env python3
"""
SCP Format Pattern Analysis

Analyzes formatting patterns across multiple SCP files to inform
a more robust parser design.
"""

import os
import re
import json
from pathlib import Path
from collections import Counter, defaultdict


def analyze_scp_structure(content):
    """Analyze the structural patterns in an SCP file"""
    
    patterns = {
        'has_item_number': bool(re.search(r'\*\*Item #:\*\*', content)),
        'has_object_class': bool(re.search(r'\*\*Object Class:\*\*', content)),
        'has_containment': bool(re.search(r'\*\*Special Containment Procedures:\*\*', content)),
        'has_description': bool(re.search(r'\*\*Description:\*\*', content)),
        'has_addenda': len(re.findall(r'\*\*Addendum[^:]*:\*\*', content)),
        
        # Formatting elements
        'has_quotes': content.count('>'),  # Quote blocks
        'has_dialogue': len(re.findall(r'\*\*[A-Z-]+[0-9]*:\*\*', content)),  # Dialogue speakers
        'has_footnotes': content.count('[[footnote]]'),
        'has_includes': content.count('[[include'),
        'has_modules': content.count('[[module'),
        'has_dividers': content.count('----'),
        'has_collapsibles': content.count('[[collapsible'),
        'has_tables': content.count('||'),
        
        # Special sections
        'has_experiments': bool(re.search(r'experiment|test|log', content, re.IGNORECASE)),
        'has_interviews': bool(re.search(r'interview|interrogation', content, re.IGNORECASE)),
        'has_exploration': bool(re.search(r'exploration|expedition', content, re.IGNORECASE)),
        'has_incident': bool(re.search(r'incident|breach', content, re.IGNORECASE)),
        
        # Document structure
        'line_count': len(content.split('\n')),
        'char_count': len(content),
        'paragraph_count': len([p for p in content.split('\n\n') if p.strip()]),
    }
    
    return patterns


def analyze_quote_patterns(content):
    """Analyze quote block patterns"""
    
    # Find quote blocks
    quote_blocks = []
    lines = content.split('\n')
    
    current_block = []
    in_quote = False
    
    for line in lines:
        if line.startswith('>'):
            if not in_quote:
                in_quote = True
                current_block = []
            current_block.append(line[1:].strip())  # Remove '>' and whitespace
        else:
            if in_quote and current_block:
                quote_blocks.append('\n'.join(current_block))
                current_block = []
            in_quote = False
    
    # Add final block if needed
    if in_quote and current_block:
        quote_blocks.append('\n'.join(current_block))
    
    return {
        'quote_block_count': len(quote_blocks),
        'quote_total_lines': sum(len(block.split('\n')) for block in quote_blocks),
        'has_nested_formatting': any('**' in block or '//' in block for block in quote_blocks),
        'has_dialogue_in_quotes': any(re.search(r'\*\*[A-Z-]+:', block) for block in quote_blocks),
        'sample_quotes': quote_blocks[:3]  # First 3 for analysis
    }


def analyze_dialogue_patterns(content):
    """Analyze dialogue and speaker patterns"""
    
    # Find dialogue speakers
    speakers = re.findall(r'\*\*([A-Z][A-Z0-9-]*[0-9]*(?:\s+[A-Z]+)*?):\*\*', content)
    
    # Common dialogue indicators
    dialogue_patterns = {
        'speakers': list(set(speakers)),
        'speaker_count': len(set(speakers)),
        'total_dialogue_lines': len(speakers),
        'has_dr_titles': any('DR' in speaker or 'DOCTOR' in speaker for speaker in speakers),
        'has_class_d': any('D-' in speaker for speaker in speakers),
        'has_o5': any('O5-' in speaker for speaker in speakers),
        'has_agent': any('AGENT' in speaker for speaker in speakers),
        'has_researcher': any('RESEARCHER' in speaker for speaker in speakers),
    }
    
    return dialogue_patterns


def analyze_addenda_patterns(content):
    """Analyze addenda structure patterns"""
    
    addenda_matches = list(re.finditer(r'\*\*Addendum ([^:*]+):\*\*(.*?)(?=\*\*Addendum|\[\[footnoteblock\]\]|\[\[include component:license-box\]\]|$)', content, re.DOTALL))
    
    addenda_info = []
    for match in addenda_matches:
        title = match.group(1).strip()
        content_text = match.group(2).strip()
        
        addenda_info.append({
            'title': title,
            'length': len(content_text),
            'has_quotes': '>' in content_text,
            'has_dialogue': bool(re.search(r'\*\*[A-Z-]+:', content_text)),
            'has_experiments': bool(re.search(r'experiment|test', content_text, re.IGNORECASE)),
            'has_logs': bool(re.search(r'log|transcript', content_text, re.IGNORECASE)),
        })
    
    return addenda_info


def analyze_all_scps():
    """Analyze all downloaded SCP files"""
    
    base_dir = Path(__file__).parent.parent.parent
    downloads_dir = base_dir / "output" / "downloads"
    
    results = {
        'total_files': 0,
        'series_distribution': defaultdict(int),
        'structural_patterns': defaultdict(int),
        'formatting_stats': defaultdict(list),
        'dialogue_analysis': defaultdict(int),
        'quote_analysis': defaultdict(int),
        'complex_documents': [],
        'simple_documents': [],
        'sample_analyses': {}
    }
    
    scp_files = sorted(downloads_dir.glob("scp-*.txt"))
    results['total_files'] = len(scp_files)
    
    print(f"Analyzing {len(scp_files)} SCP files...")
    
    for scp_file in scp_files:
        scp_number = scp_file.stem
        
        # Determine series
        number = int(scp_number.split('-')[1])
        series = (number // 1000) + 1
        results['series_distribution'][f'series_{series}'] += 1
        
        # Read and analyze content
        with open(scp_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Structural analysis
        structure = analyze_scp_structure(content)
        for key, value in structure.items():
            if isinstance(value, bool):
                if value:
                    results['structural_patterns'][key] += 1
            elif isinstance(value, (int, float)):
                results['formatting_stats'][key].append(value)
        
        # Quote analysis
        quote_analysis = analyze_quote_patterns(content)
        for key, value in quote_analysis.items():
            if isinstance(value, bool) and value:
                results['quote_analysis'][key] += 1
            elif isinstance(value, int):
                results['formatting_stats'][f'quote_{key}'].append(value)
        
        # Dialogue analysis
        dialogue_analysis = analyze_dialogue_patterns(content)
        for key, value in dialogue_analysis.items():
            if isinstance(value, bool) and value:
                results['dialogue_analysis'][key] += 1
            elif isinstance(value, int):
                results['formatting_stats'][f'dialogue_{key}'].append(value)
        
        # Addenda analysis
        addenda_analysis = analyze_addenda_patterns(content)
        
        # Classify document complexity
        complexity_score = (
            structure['has_addenda'] +
            (1 if structure['has_quotes'] > 10 else 0) +
            (1 if structure['has_dialogue'] > 5 else 0) +
            (1 if structure['has_footnotes'] > 3 else 0) +
            (1 if structure['has_includes'] > 5 else 0) +
            (1 if len(addenda_analysis) > 2 else 0)
        )
        
        doc_info = {
            'file': scp_number,
            'complexity_score': complexity_score,
            'char_count': structure['char_count'],
            'addenda_count': structure['has_addenda'],
            'quote_blocks': quote_analysis['quote_block_count'],
            'dialogue_lines': dialogue_analysis['total_dialogue_lines'],
        }
        
        if complexity_score >= 4:
            results['complex_documents'].append(doc_info)
        elif complexity_score <= 1:
            results['simple_documents'].append(doc_info)
        
        # Save detailed analysis for a few samples
        if len(results['sample_analyses']) < 5:
            results['sample_analyses'][scp_number] = {
                'structure': structure,
                'quotes': quote_analysis,
                'dialogue': dialogue_analysis,
                'addenda': addenda_analysis
            }
    
    return results


def print_analysis_report(results):
    """Print a comprehensive analysis report"""
    
    print("=" * 60)
    print("SCP FORMATTING PATTERN ANALYSIS REPORT")
    print("=" * 60)
    
    print(f"\n📊 OVERVIEW")
    print(f"Total files analyzed: {results['total_files']}")
    print(f"Series distribution:")
    for series, count in sorted(results['series_distribution'].items()):
        print(f"  {series}: {count} files")
    
    print(f"\n🏗️  STRUCTURAL PATTERNS")
    total = results['total_files']
    for pattern, count in sorted(results['structural_patterns'].items()):
        percentage = (count / total) * 100
        print(f"  {pattern}: {count}/{total} ({percentage:.1f}%)")
    
    print(f"\n💬 DIALOGUE ANALYSIS")
    for pattern, count in sorted(results['dialogue_analysis'].items()):
        if pattern != 'speakers':
            percentage = (count / total) * 100
            print(f"  {pattern}: {count}/{total} ({percentage:.1f}%)")
    
    print(f"\n📝 QUOTE BLOCK ANALYSIS")
    for pattern, count in sorted(results['quote_analysis'].items()):
        percentage = (count / total) * 100
        print(f"  {pattern}: {count}/{total} ({percentage:.1f}%)")
    
    print(f"\n📈 FORMATTING STATISTICS")
    for stat, values in results['formatting_stats'].items():
        if values and len(values) > 5:  # Only show stats with enough data
            avg = sum(values) / len(values)
            maximum = max(values)
            print(f"  {stat}: avg={avg:.1f}, max={maximum}")
    
    print(f"\n🔧 COMPLEXITY ANALYSIS")
    print(f"Complex documents (score >= 4): {len(results['complex_documents'])}")
    if results['complex_documents']:
        print("  Most complex:")
        for doc in sorted(results['complex_documents'], key=lambda x: x['complexity_score'], reverse=True)[:5]:
            print(f"    {doc['file']}: score={doc['complexity_score']}, chars={doc['char_count']}")
    
    print(f"\nSimple documents (score <= 1): {len(results['simple_documents'])}")
    if results['simple_documents']:
        print("  Examples:")
        for doc in results['simple_documents'][:5]:
            print(f"    {doc['file']}: score={doc['complexity_score']}, chars={doc['char_count']}")
    
    print(f"\n🔍 SAMPLE DETAILED ANALYSIS")
    for scp_id, analysis in list(results['sample_analyses'].items())[:2]:
        print(f"\n  {scp_id}:")
        print(f"    Character count: {analysis['structure']['char_count']}")
        print(f"    Addenda: {analysis['structure']['has_addenda']}")
        print(f"    Quote blocks: {analysis['quotes']['quote_block_count']}")
        print(f"    Dialogue speakers: {analysis['dialogue']['speaker_count']}")
        if analysis['quotes']['sample_quotes']:
            print(f"    Sample quote: {analysis['quotes']['sample_quotes'][0][:100]}...")


def main():
    """Run the analysis"""
    
    results = analyze_all_scps()
    print_analysis_report(results)
    
    # Save detailed results
    output_file = Path(__file__).parent.parent.parent / "output" / "scp_pattern_analysis.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n💾 Detailed results saved to: {output_file}")


if __name__ == "__main__":
    main()
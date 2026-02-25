#!/usr/bin/env python3
"""
Content Completeness Test

This script compares the original SCP text file with the parsed JSON output
to ensure we're not losing significant amounts of content during parsing.
"""

import json
import re
import sys
import os
from pathlib import Path


def clean_text_for_comparison(text):
    """Clean text for comparison by removing markup and normalizing whitespace"""
    if not text:
        return ""
    
    # Remove wikidot markup
    text = re.sub(r'\[\[[^\]]*\]\]', '', text)  # Remove [[...]] blocks
    text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)  # Remove bold markup
    text = re.sub(r'//([^/]+)//', r'\1', text)  # Remove italic markup
    text = re.sub(r'@@[^@]*@@', '', text)  # Remove @@ blocks
    text = re.sub(r'----+', '', text)  # Remove horizontal rules
    text = re.sub(r'^>', '', text, flags=re.MULTILINE)  # Remove quote markers
    text = re.sub(r'^\+\+\+', '', text, flags=re.MULTILINE)  # Remove +++ headers
    
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text)
    text = text.strip()
    
    return text


def extract_text_from_json(json_data):
    """Extract all meaningful text content from parsed JSON"""
    text_parts = []
    
    # Main sections
    if json_data.get('containment_procedures'):
        text_parts.append(json_data['containment_procedures'])
    
    if json_data.get('description'):
        text_parts.append(json_data['description'])
    
    # Addenda
    for addendum in json_data.get('addenda', []):
        if addendum.get('content'):
            text_parts.append(addendum['content'])
    
    # Combine all text
    combined_text = ' '.join(text_parts)
    return clean_text_for_comparison(combined_text)


def calculate_text_similarity(original, extracted):
    """Calculate rough similarity between original and extracted text"""
    if not original or not extracted:
        return 0.0
    
    # Split into words
    original_words = set(original.lower().split())
    extracted_words = set(extracted.lower().split())
    
    # Calculate overlap
    intersection = original_words & extracted_words
    union = original_words | extracted_words
    
    if not union:
        return 0.0
    
    jaccard_similarity = len(intersection) / len(union)
    
    # Also check length ratio
    length_ratio = min(len(extracted), len(original)) / max(len(extracted), len(original))
    
    return (jaccard_similarity + length_ratio) / 2


def test_content_completeness():
    """Test that parsed content matches original content reasonably well"""
    
    # Paths
    base_dir = Path(__file__).parent.parent
    original_file = base_dir / "output" / "downloads" / "scp-5370.txt"
    json_file = base_dir / "output" / "intermediate" / "scp-5370.json"
    
    print("=== Content Completeness Test ===")
    print(f"Original file: {original_file}")
    print(f"Parsed JSON: {json_file}")
    
    # Check files exist
    if not original_file.exists():
        print(f"❌ Original file not found: {original_file}")
        return False
    
    if not json_file.exists():
        print(f"❌ JSON file not found: {json_file}")
        return False
    
    # Read original text
    with open(original_file, 'r', encoding='utf-8') as f:
        original_text = f.read()
    
    # Read parsed JSON
    with open(json_file, 'r', encoding='utf-8') as f:
        json_data = json.load(f)
    
    # Clean and compare
    original_clean = clean_text_for_comparison(original_text)
    extracted_clean = extract_text_from_json(json_data)
    
    # Calculate statistics
    original_length = len(original_clean)
    extracted_length = len(extracted_clean)
    similarity = calculate_text_similarity(original_clean, extracted_clean)
    
    print(f"\n=== Statistics ===")
    print(f"Original text length: {original_length:,} characters")
    print(f"Extracted text length: {extracted_length:,} characters")
    print(f"Length retention: {extracted_length/original_length*100:.1f}%")
    print(f"Content similarity: {similarity*100:.1f}%")
    
    # Show sample of what's missing
    if similarity < 0.7:  # If less than 70% similar
        print(f"\n=== Sample Original Content ===")
        print(f"First 500 chars: {original_clean[:500]}...")
        print(f"\n=== Sample Extracted Content ===")
        print(f"First 500 chars: {extracted_clean[:500]}...")
    
    # Determine pass/fail
    length_retention = extracted_length / original_length
    
    # Thresholds for passing
    MIN_LENGTH_RETENTION = 0.6  # Should retain at least 60% of content
    MIN_SIMILARITY = 0.5        # Should have at least 50% similarity
    
    if length_retention >= MIN_LENGTH_RETENTION and similarity >= MIN_SIMILARITY:
        print(f"\n✅ PASS: Content completeness acceptable")
        return True
    else:
        print(f"\n❌ FAIL: Content completeness insufficient")
        print(f"   Length retention: {length_retention*100:.1f}% (need {MIN_LENGTH_RETENTION*100:.0f}%)")
        print(f"   Similarity: {similarity*100:.1f}% (need {MIN_SIMILARITY*100:.0f}%)")
        return False


def analyze_parsing_issues():
    """Analyze specific parsing issues to help with debugging"""

    base_dir = Path(__file__).parent.parent
    original_file = base_dir / "output" / "downloads" / "scp-5370.txt"
    
    with open(original_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    print(f"\n=== Parsing Issue Analysis ===")
    
    # Check for common section patterns
    patterns = [
        (r'\*\*Item #:\*\*', 'Item number'),
        (r'\*\*Object Class:\*\*', 'Object class'),
        (r'\*\*Special Containment Procedures:\*\*', 'Containment procedures'),
        (r'\*\*Description:\*\*', 'Description'),
        (r'\*\*Addendum [^:]*:\*\*', 'Addenda'),
    ]
    
    for pattern, name in patterns:
        matches = re.findall(pattern, content)
        print(f"{name}: {len(matches)} instances found")
    
    # Check for section boundaries that might cause issues
    section_breaks = [
        ('@@', '@@ blocks'),
        ('----', 'Horizontal rules'),
        ('[[', 'Include blocks'),
    ]
    
    print(f"\nSection boundary markers:")
    for marker, name in section_breaks:
        count = content.count(marker)
        print(f"{name}: {count} instances")
    
    # Show the structure around key sections
    desc_match = re.search(r'(\*\*Description:\*\*.*?)(?=\*\*|@@|\n\n@@|$)', content, re.DOTALL)
    if desc_match:
        desc_text = desc_match.group(1)
        print(f"\nDescription section preview:")
        print(f"Length: {len(desc_text)} characters")
        print(f"First 200 chars: {desc_text[:200]}...")
        print(f"Last 200 chars: ...{desc_text[-200:]}")


def main():
    """Run the content completeness test"""
    
    # Run the test
    success = test_content_completeness()
    
    # If failed, analyze issues
    if not success:
        analyze_parsing_issues()
    
    return success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

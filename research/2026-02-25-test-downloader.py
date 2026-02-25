#!/usr/bin/env python3
"""
Test script for SCP Foundation Wiki Source Downloader

This script demonstrates the functionality of the SCP downloader
by downloading some example articles.
"""

import os
import sys
from pathlib import Path

# Add src to path to allow running from anywhere
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from scp_downloader import SCPDownloader

OUTPUT_DIR = PROJECT_ROOT / "output"
TEST_DOWNLOADS = OUTPUT_DIR / "test_downloads"


def test_individual_downloads():
    """Test downloading individual SCP articles"""
    print("=== Testing Individual Downloads ===")

    downloader = SCPDownloader(output_dir=str(TEST_DOWNLOADS))
    
    # Test some popular SCP articles
    test_articles = [
        'scp-173',  # The Sculpture
        'scp-096',  # The Shy Guy
        'scp-999',  # The Tickle Monster
    ]
    
    for article in test_articles:
        try:
            print(f"\nDownloading {article}...")
            path = downloader.download_page(article)
            print(f"✓ Successfully downloaded to {path}")
            
            # Check file exists and has content
            if os.path.exists(path) and os.path.getsize(path) > 0:
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    print(f"  File size: {len(content)} characters")
                    # Show first few lines
                    lines = content.split('\n')[:3]
                    print(f"  First few lines: {lines}")
            else:
                print(f"  ⚠️ File appears to be empty or missing")
                
        except Exception as e:
            print(f"✗ Failed to download {article}: {e}")

def test_range_download():
    """Test downloading a small range of articles"""
    print("\n=== Testing Range Download ===")

    downloader = SCPDownloader(output_dir=str(TEST_DOWNLOADS))
    
    try:
        print("Downloading SCP-001 through SCP-003...")
        paths = downloader.download_range(1, 3, delay=1)  # Shorter delay for testing
        
        print(f"✓ Range download completed. Downloaded {len(paths)} files:")
        for path in paths:
            if os.path.exists(path):
                size = os.path.getsize(path)
                print(f"  {path} ({size} bytes)")
            else:
                print(f"  {path} (missing)")
                
    except Exception as e:
        print(f"✗ Range download failed: {e}")

def test_url_download():
    """Test downloading from a full URL"""
    print("\n=== Testing URL Download ===")

    downloader = SCPDownloader(output_dir=str(TEST_DOWNLOADS))
    
    try:
        url = "https://scp-wiki.wikidot.com/scp-5370"
        print(f"Downloading from URL: {url}")
        path = downloader.download_page(url)
        print(f"✓ Successfully downloaded to {path}")
        
        if os.path.exists(path):
            size = os.path.getsize(path)
            print(f"  File size: {size} bytes")
    except Exception as e:
        print(f"✗ URL download failed: {e}")

def main():
    """Run all tests"""
    print("SCP Downloader Test Suite")
    print("=" * 40)
    
    # Create test directory
    TEST_DOWNLOADS.mkdir(parents=True, exist_ok=True)
    
    try:
        # Run tests
        test_individual_downloads()
        test_range_download()
        test_url_download()
        
        print("\n" + "=" * 40)
        print("Test suite completed!")
        
        # Show what was downloaded
        if TEST_DOWNLOADS.exists():
            files = list(TEST_DOWNLOADS.iterdir())
            print(f"\nFiles created in {TEST_DOWNLOADS}:")
            for file in sorted(files):
                size = file.stat().st_size
                print(f"  {file.name} ({size} bytes)")
        
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

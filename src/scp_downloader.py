#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "requests>=2.31",
#     "beautifulsoup4>=4.12",
# ]
# ///
"""
SCP Foundation Wiki Source Downloader

This script downloads the wikidot source for SCP Foundation pages by making
an API request to the wikidot quickmodule endpoint.

Usage:
    uv run src/scp_downloader.py 173
    uv run src/scp_downloader.py 173 --range --end 182
"""

import os
import re
import time
import argparse
import requests
import html
from pathlib import Path
from urllib.parse import urlparse
from bs4 import BeautifulSoup

# Default paths relative to project root
PROJECT_ROOT = Path(__file__).parent.parent
DEFAULT_DOWNLOADS_DIR = PROJECT_ROOT / "output" / "downloads"
DEFAULT_RAW_DOWNLOADS_DIR = PROJECT_ROOT / "output" / "raw_downloads"

class SCPDownloader:
    """Downloads SCP Foundation wiki page sources"""
    
    def __init__(self, output_dir=None, raw_output_dir=None):
        """Initialize the downloader with output directories"""
        self.output_dir = output_dir or str(DEFAULT_DOWNLOADS_DIR)
        self.raw_output_dir = raw_output_dir or str(DEFAULT_RAW_DOWNLOADS_DIR)
        self.session = requests.Session()
        self.wikidot_token7 = None
        self.last_page_html = None
        
        # Set up a realistic user agent
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'Accept-Language': 'en-US,en;q=0.9',
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'X-Requested-With': 'XMLHttpRequest',
            'Origin': 'https://scp-wiki.wikidot.com',
            'Referer': 'https://scp-wiki.wikidot.com/'
        })
        
        # Ensure output directories exist
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(self.raw_output_dir, exist_ok=True)
    
    def initialize_session(self):
        """Initialize session and extract authentication tokens"""
        
        # First, visit the main SCP wiki page to establish session and get cookies
        response = self.session.get('https://scp-wiki.wikidot.com/')
        response.raise_for_status()
        
        # Extract wikidot_token7 from cookies
        for cookie in self.session.cookies:
            if cookie.name == 'wikidot_token7':
                self.wikidot_token7 = cookie.value
                break
        
        if not self.wikidot_token7:
            # If no token in cookies, try to extract from HTML response
            token_match = re.search(r'wikidot_token7["\']?\s*[:=]\s*["\']?([^"\';\s]+)', response.text)
            if token_match:
                self.wikidot_token7 = token_match.group(1)
    
    def get_page_info(self, url_or_id):
        """
        Get page information from a URL or SCP ID.

        Args:
            url_or_id: Either a full URL or an SCP ID (e.g., "scp-5370" or just "5370")

        Returns:
            Tuple of (page_id, page_unix_name)
        """
        # Check if input is a URL or just an SCP ID
        if url_or_id.startswith('http'):
            # Extract page name from URL
            path = urlparse(url_or_id).path
            page_unix_name = path.strip('/').split('/')[-1]
        elif url_or_id.lower().startswith('scp-'):
            page_unix_name = url_or_id.lower()
        elif url_or_id.isdigit():
            # Pure number - assume SCP article
            page_unix_name = f"scp-{url_or_id}"
        else:
            # Non-SCP page name (e.g., "experiment-log-914")
            page_unix_name = url_or_id.lower()

        # Get the page to extract the page_id
        url = f"https://scp-wiki.wikidot.com/{page_unix_name}"
        response = self.session.get(url)
        response.raise_for_status()
        self.last_page_html = response.text

        # Extract wikidot_token7 from cookies (set when visiting any page)
        for cookie in self.session.cookies:
            if cookie.name == 'wikidot_token7':
                self.wikidot_token7 = cookie.value
                break

        # Extract page ID from HTML
        page_id_match = re.search(r'WIKIREQUEST\.info\.pageId\s*=\s*(\d+);', response.text)
        if not page_id_match:
            raise ValueError(f"Could not find page ID for {page_unix_name}")

        page_id = page_id_match.group(1)
        return page_id, page_unix_name

    @staticmethod
    def extract_source_from_viewsource_html(html_content):
        """Extract wikidot source text from the quickmodule HTML body."""
        soup = BeautifulSoup(html_content, 'html.parser')

        # The source code is in a div with class="page-source"
        source_div = soup.find('div', class_='page-source')
        if not source_div:
            raise ValueError("Could not find source code in the response")

        # Get the text content and unescape HTML entities
        source_text = source_div.get_text()
        return html.unescape(source_text)
    
    def get_page_source(self, page_id):
        """
        Get the wikidot source for a page by its ID.
        
        Args:
            page_id: The page ID
            
        Returns:
            Tuple of (parsed_source, raw_html_content)
        """
        # Ensure session is initialized
        if not self.wikidot_token7:
            self.initialize_session()
        
        
        # Prepare the data for the POST request
        data = {
            'moduleName': 'viewsource/ViewSourceModule',
            'page_id': page_id,
            'callbackIndex': '1'  # This is typically included in AJAX requests
        }
        
        # Add the wikidot_token7 if available
        if self.wikidot_token7:
            data['wikidot_token7'] = self.wikidot_token7
        
        # Make the request to the ajax-module-connector.php endpoint
        url = 'https://scp-wiki.wikidot.com/ajax-module-connector.php'
        response = self.session.post(url, data=data)
        response.raise_for_status()
        
        # Parse the JSON response
        json_response = response.json()
        
        
        # Check if the request was successful
        if not json_response.get('status') == 'ok':
            error_message = json_response.get('message', 'Unknown error')
            raise RuntimeError(f"Failed to get page source: {error_message}")
        
        # Extract the HTML content from the response
        html_content = json_response.get('body', '')
        
        parsed_source = self.extract_source_from_viewsource_html(html_content)
        
        return parsed_source, html_content
    
    def download_page(self, url_or_id, output_filename=None):
        """
        Download and save the source of an SCP page.
        
        Args:
            url_or_id: Either a full URL or an SCP ID
            output_filename: Optional filename to save to, defaults to the page name
            
        Returns:
            Path to the saved file
        """
        # Get page info
        page_id, page_unix_name = self.get_page_info(url_or_id)
        
        # Get page source (both parsed and raw)
        parsed_source, raw_html = self.get_page_source(page_id)
        
        # Determine output filenames
        if not output_filename:
            output_filename = f"{page_unix_name}.txt"
            raw_output_filename = f"{page_unix_name}.html"
        else:
            # If custom filename provided, create corresponding raw filename
            base_name = os.path.splitext(output_filename)[0]
            raw_output_filename = f"{base_name}.html"
        
        # Save parsed source to text file
        output_path = os.path.join(self.output_dir, output_filename)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(parsed_source)
        
        # Save raw HTML page to raw downloads directory (full page when available)
        raw_output_path = os.path.join(self.raw_output_dir, raw_output_filename)
        with open(raw_output_path, 'w', encoding='utf-8') as f:
            f.write(self.last_page_html if self.last_page_html else raw_html)
        
        print(f"Saved parsed source to {output_path}")
        print(f"Saved raw HTML to {raw_output_path}")
        return output_path
    
    def download_range(self, start_id, end_id, prefix='scp-', delay=2):
        """
        Download a range of SCP articles.
        
        Args:
            start_id: Starting ID number
            end_id: Ending ID number
            prefix: Prefix for the SCP ID (default: 'scp-')
            delay: Delay between requests in seconds (default: 2)
            
        Returns:
            List of paths to the saved files
        """
        output_paths = []
        
        for i in range(start_id, end_id + 1):
            scp_id = f"{prefix}{i}"
            try:
                path = self.download_page(scp_id)
                output_paths.append(path)
            except Exception as e:
                pass
            
            # Respect the site by adding a delay between requests
            if i < end_id:
                time.sleep(delay)
        
        return output_paths


def main():
    """Command line interface for the script"""
    parser = argparse.ArgumentParser(description='Download SCP Foundation wiki page sources')
    
    # Add arguments
    parser.add_argument('url_or_id', help='URL or SCP ID to download (e.g., "https://scp-wiki.wikidot.com/scp-5370", "scp-5370", or just "5370")')
    parser.add_argument('-o', '--output', help='Output filename (default: [page-name].txt)')
    parser.add_argument('-d', '--directory', default=str(DEFAULT_DOWNLOADS_DIR), help='Output directory for parsed files')
    parser.add_argument('--raw-directory', default=str(DEFAULT_RAW_DOWNLOADS_DIR), help='Output directory for raw HTML files')
    parser.add_argument('-r', '--range', action='store_true', help='Treat the input as a range (requires end argument)')
    parser.add_argument('-e', '--end', type=int, help='End of range (when using --range)')
    parser.add_argument('--delay', type=float, default=2, help='Delay between requests in seconds (default: 2)')
    
    args = parser.parse_args()
    
    # Initialize downloader
    downloader = SCPDownloader(output_dir=args.directory, raw_output_dir=args.raw_directory)
    
    if args.range:
        if not args.end:
            parser.error("--range requires --end argument")
        
        # Determine if the input is a full ID or just a number
        if args.url_or_id.lower().startswith('scp-'):
            start_id = int(args.url_or_id[4:])
            prefix = 'scp-'
        else:
            try:
                start_id = int(args.url_or_id)
                prefix = 'scp-'
            except ValueError:
                parser.error("When using --range, the input must be a valid SCP number or ID")
        
        # Download range
        downloader.download_range(start_id, args.end, prefix=prefix, delay=args.delay)
    else:
        # Download single page
        downloader.download_page(args.url_or_id, args.output)


if __name__ == "__main__":
    main()

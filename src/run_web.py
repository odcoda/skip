#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "flask>=3.0",
#     "pymupdf>=1.24",
#     "requests>=2.31",
#     "beautifulsoup4>=4.12",
# ]
# ///
"""
SCP Foundation Book Generator - Web Interface Launcher

Usage:
    uv run run_web.py [--port PORT] [--debug]
"""

import argparse


def main():
    parser = argparse.ArgumentParser(description='SCP Book Generator Web Interface')
    parser.add_argument('--port', type=int, default=5000, help='Port to run on')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    parser.add_argument('--host', default='127.0.0.1', help='Host to bind to')
    args = parser.parse_args()

    from web.app import app

    print(f"""
╔══════════════════════════════════════════════════════════════╗
║          SCP Foundation Book Generator - Web Interface       ║
╠══════════════════════════════════════════════════════════════╣
║  Server: http://{args.host}:{args.port:<5}                          ║
║  Debug:  {str(args.debug):<5}                                           ║
╚══════════════════════════════════════════════════════════════╝
""")

    app.run(host=args.host, port=args.port, debug=args.debug)


if __name__ == '__main__':
    main()

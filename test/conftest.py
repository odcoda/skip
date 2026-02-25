"""
Pytest configuration and shared fixtures for SCP book generator tests.
"""
import sys
from pathlib import Path

import pytest

# Add src to path for imports
PROJECT_ROOT = Path(__file__).parent.parent
SRC_DIR = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))

# Test directories
TEST_ROOT = Path(__file__).parent
DATA_DIR = TEST_ROOT / "data"
FIXTURES_DIR = DATA_DIR / "input"
EXPECTED_DIR = DATA_DIR / "expected"
OUTPUT_DIR = TEST_ROOT / "output"


@pytest.fixture
def fixtures_dir():
    """Return path to test fixtures directory."""
    return FIXTURES_DIR


@pytest.fixture
def expected_dir():
    """Return path to expected outputs directory."""
    return EXPECTED_DIR


@pytest.fixture
def test_output_dir():
    """Return path to test output directory (for inspecting generated PDFs)."""
    OUTPUT_DIR.mkdir(exist_ok=True)
    return OUTPUT_DIR


@pytest.fixture
def project_root():
    """Return path to project root."""
    return PROJECT_ROOT


@pytest.fixture
def test_scp_files(fixtures_dir):
    """Return list of all test SCP files."""
    return sorted(fixtures_dir.glob("scp-test-*.txt"))


@pytest.fixture
def parser():
    """Return an instance of the enhanced parser."""
    from parsers.enhanced_wikidot_parser import EnhancedWikidotParser
    return EnhancedWikidotParser()


@pytest.fixture
def converter():
    """Return an instance of the enhanced LaTeX converter."""
    from latex.enhanced_converter import EnhancedLaTeXConverter
    from pipeline.builder import PipelineConfig
    config = PipelineConfig()
    return EnhancedLaTeXConverter(config)

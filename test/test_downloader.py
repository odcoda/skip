"""Tests for downloader source extraction behavior."""

from pathlib import Path

import pytest

from scp_downloader import SCPDownloader


def test_extract_source_from_viewsource_html():
    fixture = Path(__file__).parent / "data" / "downloader" / "viewsource-response.html"
    html = fixture.read_text(encoding="utf-8")

    source = SCPDownloader.extract_source_from_viewsource_html(html)

    assert "**Item #:** SCP-999" in source
    assert "[[include component:rate]]" in source
    assert "<script>ignored</script>" in source


def test_extract_source_from_viewsource_html_missing_div_raises():
    with pytest.raises(ValueError):
        SCPDownloader.extract_source_from_viewsource_html("<html><body>no source</body></html>")

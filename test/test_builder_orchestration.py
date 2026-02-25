"""Tests for pipeline orchestration behavior in SCPBookBuilder."""

from pathlib import Path

from pipeline.builder import PipelineConfig, SCPBookBuilder


def make_builder(tmp_path: Path) -> SCPBookBuilder:
    output_dir = tmp_path / "output"
    manual_dir = tmp_path / "manual"
    diffs_dir = tmp_path / "diffs"

    config = PipelineConfig(
        output_dir=str(output_dir),
        manual_dir=str(manual_dir),
        diffs_dir=str(diffs_dir),
        download_missing=False,
        resolve_dependencies=False,
        download_assets=False,
        compile_pdf=False,
    )
    builder = SCPBookBuilder(config)
    builder.ensure_directories()
    return builder


def test_manual_download_override_is_preferred_and_diff_is_written(tmp_path):
    builder = make_builder(tmp_path)

    auto_source = Path(builder.config.input_dir) / "scp-173.txt"
    manual_source = Path(builder.config.manual_dir) / "downloads" / "scp-173.txt"
    auto_source.write_text("auto content\n", encoding="utf-8")
    manual_source.write_text("manual content\n", encoding="utf-8")

    effective, auto = builder._prepare_source("scp-173")

    assert effective == manual_source
    assert auto == auto_source

    diff_file = Path(builder.config.diffs_dir) / "downloads" / "scp-173.txt.diff"
    assert diff_file.exists()
    diff_text = diff_file.read_text(encoding="utf-8")
    assert "-auto content" in diff_text
    assert "+manual content" in diff_text


def test_extract_page_dependencies_keeps_supplements_but_drops_cross_scp_links(tmp_path):
    builder = make_builder(tmp_path)

    source = """
[[include experiment-log-9998]]
[[include scp-173]]
[[[document-9998-a]]]
[[[scp-055|crosslink]]]
https://scp-wiki.wikidot.com/fragment:experiment-log-9998-001
https://scp-wiki.wikidot.com/scp-682
"""

    deps = builder._extract_page_dependencies(source, "scp-9998")

    assert "experiment-log-9998" in deps
    assert "document-9998-a" in deps
    assert "fragment:experiment-log-9998-001" in deps
    assert "scp-173" not in deps
    assert "scp-055" not in deps
    assert "scp-682" not in deps


def test_read_dependency_manifest_parses_pages_and_assets(tmp_path):
    builder = make_builder(tmp_path)

    manifest = Path(builder.config.manual_dir) / "deps" / "scp-9998.yaml"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(
        """
page: scp-9998
depends_on:
  pages:
    - experiment-log-9998
    - fragment:experiment-log-9998-001
  assets:
    - scp-9998/reference.png
    - https://example.com/media/file.jpg
""".strip()
        + "\n",
        encoding="utf-8",
    )

    pages, assets = builder._read_dependency_manifest(manifest)

    assert pages == ["experiment-log-9998", "fragment:experiment-log-9998-001"]
    assert assets == ["https://example.com/media/file.jpg", "scp-9998/reference.png"]


def test_load_image_map_skips_invalid_jpeg_files(tmp_path):
    builder = make_builder(tmp_path)

    builder._image_index = {
        "scp-682": [
            {"filename": "Monster8.jpg", "location": "originals", "url": "https://example.com/one.jpg"},
            {"filename": "monster8editub9-new.jpg", "url": "https://example.com/two.jpg"},
        ]
    }

    bad_jpeg = Path(builder.config.output_dir) / "assets" / "scp-682" / "originals" / "Monster8.jpg"
    good_jpeg = Path(builder.config.output_dir) / "assets" / "scp-682" / "monster8editub9-new.jpg"
    bad_jpeg.parent.mkdir(parents=True, exist_ok=True)
    good_jpeg.parent.mkdir(parents=True, exist_ok=True)

    # WebP header in a .jpg filename -> should be rejected.
    bad_jpeg.write_bytes(b"RIFF\x01\x02\x03\x04WEBPxxxxx")
    # Valid JPEG SOI + marker prefix.
    good_jpeg.write_bytes(b"\xff\xd8\xff\xdbsample")

    image_map = builder.load_image_map()

    assert "SCP-682" in image_map
    filenames = [img["filename"] for img in image_map["SCP-682"]]
    assert filenames == ["monster8editub9-new.jpg"]


def test_download_asset_rejects_mismatched_media_content(tmp_path, monkeypatch):
    builder = make_builder(tmp_path)

    class FakeResponse:
        content = b"<html>not an image</html>"

        def raise_for_status(self):
            return None

    def fake_get(url, timeout=30):
        return FakeResponse()

    monkeypatch.setattr("pipeline.builder.requests.get", fake_get)

    saved = builder._download_asset("https://example.com/bad.jpg", "scp-9998")

    assert saved is None
    expected_file = Path(builder.config.output_dir) / "assets" / "scp-9998" / "bad.jpg"
    assert not expected_file.exists()

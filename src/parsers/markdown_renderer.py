#!/usr/bin/env python3
"""Render parsed SCP documents into readable Markdown previews."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any, Mapping

from parsers.enhanced_wikidot_parser import ContentType, EnhancedSCPDocument


class MarkdownRenderer:
    """Converts parsed document objects or JSON dictionaries to Markdown."""

    def render_document(self, document: EnhancedSCPDocument | Mapping[str, Any]) -> str:
        data = self._to_dict(document)
        lines: list[str] = []

        title = self._clean_inline(str(data.get("title") or "")).strip()
        scp_number = data.get("scp_number") or "Untitled"
        heading = f"# {scp_number}"
        if title:
            heading += f": {title}"
        lines.extend([heading, ""])

        object_class = data.get("object_class")
        if object_class:
            lines.extend([f"**Object Class:** {self._clean_inline(str(object_class))}", ""])

        for section in data.get("sections") or []:
            section_title = section.get("title") or section.get("section_type") or "Section"
            lines.extend([f"## {self._section_title(str(section_title))}", ""])

            for block in section.get("content_blocks") or []:
                rendered = self._render_block(block)
                if rendered:
                    lines.extend([rendered, ""])

        return "\n".join(lines).strip() + "\n"

    def render_json_file(self, path: str | Path) -> str:
        with open(path, "r", encoding="utf-8") as f:
            return self.render_document(json.load(f))

    def _to_dict(self, document: EnhancedSCPDocument | Mapping[str, Any]) -> dict[str, Any]:
        if isinstance(document, Mapping):
            return dict(document)
        if is_dataclass(document):
            return self._convert_enums(asdict(document))
        raise TypeError(f"Unsupported document type: {type(document)!r}")

    def _convert_enums(self, value: Any) -> Any:
        if isinstance(value, dict):
            return {key: self._convert_enums(item) for key, item in value.items()}
        if isinstance(value, list):
            return [self._convert_enums(item) for item in value]
        if isinstance(value, ContentType):
            return value.value
        return value

    def _render_block(self, block: Mapping[str, Any]) -> str:
        block_type = block.get("type")
        content = str(block.get("content") or "")
        attributes = block.get("attributes") or {}

        if block_type == "list":
            items = attributes.get("items") or []
            return "\n".join(f"- {self._clean_inline(str(item))}" for item in items)

        if block_type == "table":
            return self._render_table(attributes.get("rows") or [], content)

        if block_type == "divider":
            return "---"

        if block_type == "quote_block":
            if attributes.get("dialogue"):
                dialogue = []
                for line in attributes["dialogue"]:
                    speaker = self._clean_inline(str(line.get("speaker") or "Speaker"))
                    text = self._clean_inline(str(line.get("text") or ""))
                    dialogue.append(f"> **{speaker}:** {text}")
                return "\n".join(dialogue)
            return "\n".join(f"> {self._clean_inline(line)}" for line in content.splitlines())

        if block_type in {"include", "module"}:
            return f"`{content.strip()}`"

        return self._clean_block(content)

    def _render_table(self, rows: list[Any], fallback: str) -> str:
        clean_rows = [
            [self._clean_inline(str(cell).strip()) for cell in row if str(cell).strip()]
            for row in rows
        ]
        clean_rows = [row for row in clean_rows if row]
        if not clean_rows:
            return self._clean_block(fallback)

        width = max(len(row) for row in clean_rows)
        padded = [row + [""] * (width - len(row)) for row in clean_rows]
        header = padded[0]
        separator = ["---"] * width
        body = padded[1:]
        table_rows = [header, separator, *body]
        return "\n".join("| " + " | ".join(row) + " |" for row in table_rows)

    def _section_title(self, title: str) -> str:
        normalized = title.replace("_", " ").strip()
        if normalized.lower() in {"containment", "description"}:
            return normalized.title()
        if normalized.lower() == "addendum":
            return "Addendum"
        return self._clean_inline(normalized)

    def _clean_block(self, text: str) -> str:
        lines = [self._clean_inline(line).rstrip() for line in text.splitlines()]
        return "\n".join(lines).strip()

    def _clean_inline(self, text: str) -> str:
        text = re.sub(r"\[\[/?[^\]]+\]\]", "", text)
        text = re.sub(r"\[\[footnote\]\](.*?)\[\[/footnote\]\]", r" [^\1]", text, flags=re.DOTALL)
        text = re.sub(r"\[\[span [^\]]+\]\](.*?)\[\[/span\]\]", r"\1", text, flags=re.DOTALL)
        text = re.sub(r"\[\[image\s+([^\]\s]+)[^\]]*\]\]", r"![image](\1)", text)
        text = re.sub(r"\[\[([^\]|\n]+)\|([^\]\n]+)\]\]", r"[\2](\1)", text)
        text = re.sub(r"\[\[([^\]\n]+)\]\]", r"\1", text)
        text = text.replace("//", "*")
        return text.strip()

"""ローカルに置かれたIR資料（PDF/HTML/テキスト）からテキストを抽出する。

Phase3では実サイトへの自動巡回スクレイピングは行わず、ユーザーが手元に
配置したファイルを読み込む方式のみをサポートする。
"""

from __future__ import annotations

import re
from html.parser import HTMLParser
from pathlib import Path

from pypdf import PdfReader

SUPPORTED_SUFFIXES = {".pdf", ".html", ".htm", ".txt"}


class _TextOnlyHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._chunks: list[str] = []

    def handle_data(self, data: str) -> None:
        self._chunks.append(data)

    def get_text(self) -> str:
        return re.sub(r"\n{3,}", "\n\n", "".join(self._chunks)).strip()


def extract_text_from_file(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix not in SUPPORTED_SUFFIXES:
        raise ValueError(
            f"未対応のファイル形式です: {suffix}（対応形式: {sorted(SUPPORTED_SUFFIXES)}）"
        )

    if suffix == ".pdf":
        reader = PdfReader(str(path))
        return "\n".join(page.extract_text() or "" for page in reader.pages)

    raw = path.read_text(encoding="utf-8")
    if suffix in (".html", ".htm"):
        parser = _TextOnlyHTMLParser()
        parser.feed(raw)
        return parser.get_text()

    return raw

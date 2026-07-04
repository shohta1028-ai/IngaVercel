"""LLMの応答からJSON部分を取り出すための共通ヘルパー。

プロンプトで「JSONのみを出力」と指示しても、実際にはLLMが
```json ... ``` のようなMarkdownコードフェンスで囲んで返すことがある
ため、パース前にコードフェンスを取り除く。
"""

from __future__ import annotations

import re

_CODE_FENCE_RE = re.compile(r"^```[a-zA-Z]*\s*\n?|\n?```\s*$")


def extract_json_text(raw: str) -> str:
    text = raw.strip()
    if text.startswith("```"):
        text = _CODE_FENCE_RE.sub("", text).strip()
    return text

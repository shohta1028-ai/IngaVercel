"""LLMクライアントをモックするための汎用フェイクLLMクライアントの雛形。

他プロジェクトへ展開するときは、このファイルをコピーして、対象の外部
クライアントの形状（例: `.messages.create()`, `.chat.completions.create()`
等）に合わせて数行書き換えて使う。PyPI配布パッケージにはしない —
プロジェクトごとに外部クライアントのインターフェースが異なるため、
抽象化しすぎるとかえって使いにくくなる（TESTING_PLAYBOOK.md参照）。

実際の使用例: backend/tests/test_dialogue.py の _ScriptedAnthropicClient。
"""

from __future__ import annotations

import json
from dataclasses import dataclass


@dataclass
class FakeTextBlock:
    text: str
    type: str = "text"


@dataclass
class FakeResponse:
    content: list[FakeTextBlock]


class ScriptedLLMClient:
    """systemプロンプト（または任意のリクエスト内容）に含まれる目印文字列
    に応じて、あらかじめ用意した固定のJSONペイロードを返すフェイクLLM
    クライアント。

    Anthropicの`client.messages.create(system=..., messages=...)`形状を
    想定しているが、対象SDKが`client.chat.completions.create()`等の
    場合は`self.messages = self`の行と`create()`の引数名を書き換えるだけで
    同様に使える。
    """

    def __init__(self, responses_by_marker: dict[str, dict]):
        self._responses_by_marker = responses_by_marker
        self.messages = self

    def create(self, system: str = "", **kwargs) -> FakeResponse:
        haystack = system or json.dumps(kwargs.get("messages", []), ensure_ascii=False)
        for marker, payload in self._responses_by_marker.items():
            if marker in haystack:
                return FakeResponse(
                    content=[FakeTextBlock(text=json.dumps(payload, ensure_ascii=False))]
                )
        raise AssertionError(
            f"未定義のリクエストです（登録済みマーカー: {list(self._responses_by_marker)}）"
        )

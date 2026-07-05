"""Phase 3: IR資料のテキストから財務数値・企業固有KPIをLLMで抽出する。"""

from __future__ import annotations

import json
import os

from anthropic import Anthropic

from app.common.json_utils import extract_json_text
from app.ingestion.models import IRDataPoint, IRDataPointKind, IRDataSource

DEFAULT_MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-5")

# 巨大なIR資料を全文投入するとLLM呼び出しが不安定になるため、先頭のみ使う。
# 決算短信・説明会資料は主要な数値が冒頭にまとまっていることが多い。
MAX_DOCUMENT_TEXT_CHARS = 40_000

SYSTEM_PROMPT = """\
あなたは証券アナリストです。企業のIR資料（決算短信・有価証券報告書・
説明会資料）のテキストから、以下2種類の情報を抽出してください。

1. 直近数期の主要な財務数値（売上高、営業利益など）
2. 中期経営計画等で掲げられている、その企業固有の重要経営指標（KPI）
   （財務指標・非財務指標いずれも含む）

出力は必ず以下のJSONスキーマに従うJSONオブジェクトのみとし、それ以外の
説明文は一切出力しないでください。

{
  "data_points": [
    {
      "label": "指標名（例: 売上高, 工場稼働率）",
      "kind": "financial" | "nonfinancial",
      "value": 数値またはnull（テキスト中に明記されていない場合はnull）,
      "unit": "単位（例: 百万円, %）またはnull",
      "period": "対象期間（例: 2024年3月期）またはnull",
      "excerpt": "この情報の根拠となった原文の一節（30〜80文字程度）"
    }
  ]
}

制約:
- 憶測で数値を作らないこと。テキストに明記されていない値はnullとする
- 同じ指標が複数期にわたって記載されている場合は、期ごとに別のdata_pointとして出力する
"""


def build_user_prompt(document_text: str) -> str:
    return f"以下はIR資料から抽出したテキストです。\n\n---\n{document_text}\n---\n"


def _parse_llm_data_points(raw_json: str, document_name: str) -> list[IRDataPoint]:
    data = json.loads(extract_json_text(raw_json))
    return [
        IRDataPoint(
            label=dp["label"],
            kind=IRDataPointKind(dp["kind"]),
            value=dp.get("value"),
            unit=dp.get("unit"),
            period=dp.get("period"),
            source=IRDataSource(document_name=document_name, excerpt=dp.get("excerpt")),
        )
        for dp in data["data_points"]
    ]


def extract_ir_data_points(
    document_text: str,
    document_name: str,
    client: Anthropic | None = None,
    model: str = DEFAULT_MODEL,
) -> list[IRDataPoint]:
    """IR資料のテキストから財務数値・企業固有KPIを抽出する。

    Anthropic APIを実際に呼び出すため、環境変数 ANTHROPIC_API_KEY が必要。
    """
    client = client or Anthropic()

    truncated_text = document_text[:MAX_DOCUMENT_TEXT_CHARS]

    response = client.messages.create(
        model=model,
        max_tokens=8000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": build_user_prompt(truncated_text)}],
    )
    raw_text = "".join(block.text for block in response.content if block.type == "text")

    if not raw_text.strip():
        raise ValueError(
            "LLMから空の応答が返されました。資料のサイズが大きすぎる可能性があります。"
        )

    if response.stop_reason == "max_tokens":
        raise ValueError(
            "抽出結果が多すぎてLLMの最大出力トークン数に達し、応答が途中で"
            "打ち切られました。資料に含まれる指標数が多い可能性があります。"
        )

    try:
        return _parse_llm_data_points(raw_text, document_name)
    except json.JSONDecodeError as e:
        raise ValueError(
            f"LLMの応答をJSONとして解釈できませんでした（想定外の形式で応答された"
            f"可能性があります）: {e}"
        ) from e

"""Phase 1: 業界標準DAGテンプレートのLLM生成。

会計論理・業界定石KPIに基づき、指定業界のPL/BS/CS標準因果構造をLLMに
生成させ、FinancialCausalDAGとして返す。生成された全エッジは
source="template" / status="ai_proposed" として扱う
（ユーザーによるレビュー前のためPhase5のチューニング対象となる）。
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone

from anthropic import Anthropic

from app.models.dag import (
    Edge,
    EdgeSign,
    EdgeStatus,
    FinancialCausalDAG,
    Node,
    NodeCategory,
    NodeSource,
)

DEFAULT_MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-5")

SYSTEM_PROMPT = """\
あなたは公認会計士であり、財務諸表分析と業界KPIに精通したドメインエキスパートです。
指定された業界について、PL(損益計算書)・BS(貸借対照表)・CS(キャッシュフロー計算書)
の標準的な会計連動ロジックと、その業界で定石とされる財務・非財務KPIの因果関係を
DAG(有向非巡回グラフ)として構造化してください。

出力は必ず以下のJSONスキーマに従うJSONオブジェクトのみとし、それ以外の説明文は
一切出力しないでください。

{
  "nodes": [
    {
      "id": "snake_case_の一意なID",
      "label": "表示名（日本語）",
      "category": "PL" | "BS" | "CS" | "KPI_financial" | "KPI_nonfinancial",
      "statement": "科目区分（例: 売上原価, 流動資産）またはnull",
      "unit": "単位（例: 円, %, 回/月）またはnull",
      "description": "補足説明"
    }
  ],
  "edges": [
    {
      "source_node_id": "原因ノードのid",
      "target_node_id": "結果ノードのid",
      "sign": "positive" | "negative" | "ambiguous",
      "rationale": "会計論理・業界知識に基づくこの因果関係の根拠"
    }
  ]
}

制約:
- ノードは20〜40個程度、エッジはノード間の主要な因果関係を過不足なく含めること
- 循環（サイクル）が生じないようにすること（DAGであること）
- 業界固有の重要KPI（例: 製造業なら稼働率・歩留まり率など）を最低3つはKPI_financial
  またはKPI_nonfinancialとして含めること
"""


def build_user_prompt(industry: str) -> str:
    return f"対象業界: {industry}\n上記の制約に従い、この業界の標準的な因果DAGをJSONで出力してください。"


def _parse_llm_nodes_and_edges(raw_json: str) -> tuple[list[Node], list[Edge]]:
    data = json.loads(raw_json)

    nodes = [
        Node(
            id=n["id"],
            label=n["label"],
            category=NodeCategory(n["category"]),
            statement=n.get("statement"),
            unit=n.get("unit"),
            description=n.get("description"),
            source=NodeSource.TEMPLATE,
        )
        for n in data["nodes"]
    ]

    edges = [
        Edge(
            id=f"e_{uuid.uuid4().hex[:8]}",
            source_node_id=e["source_node_id"],
            target_node_id=e["target_node_id"],
            sign=EdgeSign(e["sign"]),
            rationale=e.get("rationale"),
            status=EdgeStatus.AI_PROPOSED,
            round_added=None,
        )
        for e in data["edges"]
    ]

    return nodes, edges


def generate_industry_template(
    industry: str,
    client: Anthropic | None = None,
    model: str = DEFAULT_MODEL,
) -> FinancialCausalDAG:
    """指定業界の標準DAGテンプレートをLLMで生成する。

    Anthropic APIを実際に呼び出すため、環境変数 ANTHROPIC_API_KEY が必要。
    """
    client = client or Anthropic()

    response = client.messages.create(
        model=model,
        max_tokens=8000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": build_user_prompt(industry)}],
    )
    raw_text = "".join(
        block.text for block in response.content if block.type == "text"
    )

    nodes, edges = _parse_llm_nodes_and_edges(raw_text)

    now = datetime.now(timezone.utc)
    return FinancialCausalDAG(
        id=f"dag_{uuid.uuid4().hex[:8]}",
        name=f"{industry}_標準テンプレート",
        industry=industry,
        company=None,
        goal=None,
        created_at=now,
        updated_at=now,
        nodes=nodes,
        edges=edges,
    )

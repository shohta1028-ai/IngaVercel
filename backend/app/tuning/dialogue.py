"""Phase 5: 5ラウンド対話チューニング（基本5ラウンド固定＋任意追加ラウンド）。

各ラウンドは以下の2ステップからなる:
  1. generate_next_proposal(dag)  — AIが次の確認・提案を1件選び、
     「説明文＋質問」の形でai_messageを生成する
  2. apply_user_response(dag, proposal, user_response)
     — ユーザーの自由記述の回答をAIが解釈し、DAGに変更を適用する

確認対象は優先順位: ①未確認のAI仮説エッジ(ai_proposed) → ②未接続の候補ノード
の順で1件ずつ選ぶ。どちらも無くなった場合はNoneを返す。
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone

from anthropic import Anthropic

from app.common.json_utils import extract_json_text
from app.merge.node_ops import unconnected_node_ids
from app.models.dag import (
    Edge,
    EdgeSign,
    EdgeStatus,
    FinancialCausalDAG,
    Lag,
    TuningRound,
    TuningStatus,
)
from app.tuning.models import ParsedUserResponse, ProposalKind, TuningProposal, UserDecision

DEFAULT_MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-5")
BASE_ROUNDS = 5

CONFIRM_EDGE_SYSTEM_PROMPT = """\
あなたは財務データ分析の専門家として、ユーザーと対話しながら因果DAGを
チューニングしています。以下のエッジ（AIによる仮説）について、ユーザーに
1問だけ確認する短い日本語のメッセージを作成してください。

出力は必ず次のJSON形式のみ: {"message": "説明文＋Yes/No等の質問"}

メッセージには、なぜこの因果関係を仮説として提示しているか（会計論理・
分析ゴールとの関連）を簡潔に含め、最後に確認の質問で締めてください。
"""

CONNECT_NODE_SYSTEM_PROMPT = """\
あなたは財務データ分析の専門家として、ユーザーと対話しながら因果DAGを
チューニングしています。以下の「まだツリーに接続されていないKPI」を、
既存のノードのどれかに因果関係として紐付ける提案をしてください。

出力は必ず次のJSON形式のみ:
{
  "message": "説明文＋Yes/No等の質問",
  "target_node_id": "紐付け先ノードのid（既存ノード一覧から選ぶ）",
  "sign": "positive" | "negative",
  "rationale": "この因果関係を提案する根拠"
}
"""

INTERPRET_RESPONSE_SYSTEM_PROMPT = """\
あなたはユーザーの自由記述の回答を解釈し、構造化データに変換するアシス
タントです。直前にAIが提示した因果関係の提案・確認と、それに対する
ユーザーの回答を読み、以下のJSON形式でユーザーの意図を出力してください。

出力は必ず次のJSON形式のみ:
{
  "decision": "confirm" | "modify" | "reject",
  "sign_override": "positive" | "negative" | "ambiguous" | null,
  "lag_value": 数値またはnull,
  "lag_unit": "day" | "week" | "month" | "quarter" | "year" | null,
  "note": "補足（あれば）またはnull"
}

- 単純な同意（YES等）は decision="confirm"
- 同意しつつ条件・修正を付け加えている場合（タイムラグの指定など）は
  decision="modify" とし、該当するフィールドを埋める
- 明確な拒否（NO等）は decision="reject"
"""


def _call_llm(client: Anthropic, model: str, system: str, user_content: str, max_tokens: int) -> str:
    response = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user_content}],
    )
    return "".join(block.text for block in response.content if block.type == "text")


def generate_next_proposal(
    dag: FinancialCausalDAG,
    client: Anthropic | None = None,
    model: str = DEFAULT_MODEL,
) -> TuningProposal | None:
    client = client or Anthropic()
    round_number = len(dag.tuning_state.rounds) + 1

    pending_edge = next(
        (e for e in dag.edges if e.status == EdgeStatus.AI_PROPOSED), None
    )
    if pending_edge is not None:
        node_by_id = {n.id: n for n in dag.nodes}
        source_label = node_by_id[pending_edge.source_node_id].label
        target_label = node_by_id[pending_edge.target_node_id].label
        user_content = (
            f"分析ゴール: {dag.goal or '(未設定)'}\n"
            f"エッジ: {source_label} → {target_label}\n"
            f"符号: {pending_edge.sign.value}\n"
            f"根拠: {pending_edge.rationale or '(なし)'}"
        )
        raw = _call_llm(
            client, model, CONFIRM_EDGE_SYSTEM_PROMPT, user_content, max_tokens=500
        )
        message = json.loads(extract_json_text(raw))["message"]
        return TuningProposal(
            round_number=round_number,
            kind=ProposalKind.CONFIRM_EDGE,
            ai_message=message,
            candidate_edge=pending_edge,
        )

    candidate_ids = unconnected_node_ids(dag)
    if candidate_ids:
        node_by_id = {n.id: n for n in dag.nodes}
        candidate_node = node_by_id[candidate_ids[0]]
        other_nodes = "\n".join(
            f"- {n.id}: {n.label}" for n in dag.nodes if n.id != candidate_node.id
        )
        user_content = (
            f"分析ゴール: {dag.goal or '(未設定)'}\n"
            f"未接続のKPI: {candidate_node.label} (id={candidate_node.id})\n"
            f"既存ノード一覧:\n{other_nodes}"
        )
        raw = _call_llm(
            client, model, CONNECT_NODE_SYSTEM_PROMPT, user_content, max_tokens=500
        )
        data = json.loads(extract_json_text(raw))
        candidate_edge = Edge(
            id=f"e_proposal_{uuid.uuid4().hex[:8]}",
            source_node_id=candidate_node.id,
            target_node_id=data["target_node_id"],
            sign=EdgeSign(data["sign"]),
            rationale=data["rationale"],
            status=EdgeStatus.AI_PROPOSED,
        )
        return TuningProposal(
            round_number=round_number,
            kind=ProposalKind.CONNECT_NODE,
            ai_message=data["message"],
            candidate_edge=candidate_edge,
        )

    return None


def _interpret_user_response(
    client: Anthropic, model: str, proposal: TuningProposal, user_response: str
) -> ParsedUserResponse:
    user_content = f"AIの提案: {proposal.ai_message}\nユーザーの回答: {user_response}"
    raw = _call_llm(
        client, model, INTERPRET_RESPONSE_SYSTEM_PROMPT, user_content, max_tokens=300
    )
    data = json.loads(extract_json_text(raw))
    return ParsedUserResponse(
        decision=UserDecision(data["decision"]),
        sign_override=data.get("sign_override"),
        lag_value=data.get("lag_value"),
        lag_unit=data.get("lag_unit"),
        note=data.get("note"),
    )


def apply_user_response(
    dag: FinancialCausalDAG,
    proposal: TuningProposal,
    user_response: str,
    client: Anthropic | None = None,
    model: str = DEFAULT_MODEL,
) -> FinancialCausalDAG:
    client = client or Anthropic()
    parsed = _interpret_user_response(client, model, proposal, user_response)

    lag = None
    if parsed.lag_value is not None and parsed.lag_unit is not None:
        lag = Lag(value=parsed.lag_value, unit=parsed.lag_unit)

    final_edge = proposal.candidate_edge.model_copy(
        update={
            "sign": EdgeSign(parsed.sign_override) if parsed.sign_override else proposal.candidate_edge.sign,
            "lag": lag if lag is not None else proposal.candidate_edge.lag,
            "round_added": proposal.round_number,
        }
    )

    edges = list(dag.edges)
    applied_changes: list[str] = []

    if parsed.decision == UserDecision.REJECT:
        if proposal.kind == ProposalKind.CONFIRM_EDGE:
            edges = [
                e if e.id != final_edge.id else e.model_copy(update={"status": EdgeStatus.REJECTED})
                for e in edges
            ]
            applied_changes.append(f"エッジ{final_edge.id}を却下(rejected)")
        else:
            applied_changes.append(f"ノード{final_edge.source_node_id}の紐付け提案を却下（未接続のまま）")
    else:
        status = (
            EdgeStatus.USER_CONFIRMED if parsed.decision == UserDecision.CONFIRM else EdgeStatus.USER_MODIFIED
        )
        final_edge = final_edge.model_copy(update={"status": status})

        if proposal.kind == ProposalKind.CONFIRM_EDGE:
            edges = [e if e.id != final_edge.id else final_edge for e in edges]
            applied_changes.append(f"エッジ{final_edge.id}を{status.value}として確定")
        else:
            edges = [*edges, final_edge]
            applied_changes.append(f"新規エッジ{final_edge.id}を追加し{status.value}として確定")

    new_round_number = len(dag.tuning_state.rounds) + 1
    round_record = TuningRound(
        round_number=new_round_number,
        ai_message=proposal.ai_message,
        user_response=user_response,
        applied_changes=applied_changes,
    )

    new_status = TuningStatus.LOCKED if new_round_number >= BASE_ROUNDS else TuningStatus.IN_PROGRESS
    new_tuning_state = dag.tuning_state.model_copy(
        update={
            "status": new_status,
            "completed_rounds": min(new_round_number, BASE_ROUNDS),
            "rounds": [*dag.tuning_state.rounds, round_record],
        }
    )

    return dag.model_copy(
        update={
            "edges": edges,
            "tuning_state": new_tuning_state,
            "updated_at": datetime.now(timezone.utc),
        }
    )

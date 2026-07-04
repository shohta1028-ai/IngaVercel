"""Phase 5: 5ラウンド対話チューニングで使うLLM向け構造体。"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel

from app.models.dag import Edge


class ProposalKind(str, Enum):
    # 既存のAI仮説エッジ（Phase1テンプレート由来）の確認を依頼する
    CONFIRM_EDGE = "confirm_edge"
    # 未接続の候補ノード（Phase3/4由来）の紐付け先をAIが提案する
    CONNECT_NODE = "connect_node"


class TuningProposal(BaseModel):
    round_number: int
    kind: ProposalKind
    ai_message: str
    # 常にstatus="ai_proposed"のエッジ案。confirm_edgeの場合はdag.edges内の
    # 既存エッジそのもの、connect_nodeの場合はまだdagに追加されていない新規案
    candidate_edge: Edge


class UserDecision(str, Enum):
    CONFIRM = "confirm"
    MODIFY = "modify"
    REJECT = "reject"


class ParsedUserResponse(BaseModel):
    decision: UserDecision
    sign_override: str | None = None
    lag_value: float | None = None
    lag_unit: str | None = None
    note: str | None = None

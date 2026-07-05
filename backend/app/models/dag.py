"""backend/schemas/dag_schema.json に対応するPydanticモデル。"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class NodeCategory(str, Enum):
    PL = "PL"
    BS = "BS"
    CS = "CS"
    KPI_FINANCIAL = "KPI_financial"
    KPI_NONFINANCIAL = "KPI_nonfinancial"


class NodeSource(str, Enum):
    TEMPLATE = "template"
    IR_DATA = "ir_data"
    USER_ADDED = "user_added"


class EdgeSign(str, Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    AMBIGUOUS = "ambiguous"


class EdgeStatus(str, Enum):
    AI_PROPOSED = "ai_proposed"
    USER_CONFIRMED = "user_confirmed"
    USER_MODIFIED = "user_modified"
    REJECTED = "rejected"


class LagUnit(str, Enum):
    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    QUARTER = "quarter"
    YEAR = "year"


class TuningStatus(str, Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    LOCKED = "locked"
    REOPENED = "reopened"


class SourceCitation(BaseModel):
    """ノードの数値・KPIの出典を構造化して保持する（IRデータ取込み・ユーザー
    手動編集の両方で使う）。descriptionの自由記述と異なり、リンク表示等の
    UI表現がしやすいようフィールドを分けている。"""

    document_name: Optional[str] = None
    url: Optional[str] = None
    excerpt: Optional[str] = None


class Node(BaseModel):
    id: str
    label: str
    category: NodeCategory
    statement: Optional[str] = None
    unit: Optional[str] = None
    description: Optional[str] = None
    source: NodeSource
    # 期間ラベル(例: "2025年3月期") -> その期の実測値。実データがある
    # ノードのみ設定する（無いノードはNoneのまま＝構造のみの推定値扱い）
    values_by_period: Optional[dict[str, float]] = None
    source_citation: Optional[SourceCitation] = None


class Lag(BaseModel):
    value: float
    unit: LagUnit


class Edge(BaseModel):
    id: str
    source_node_id: str
    target_node_id: str
    sign: EdgeSign
    strength: Optional[float] = Field(default=None, ge=0, le=1)
    lag: Optional[Lag] = None
    rationale: Optional[str] = None
    status: EdgeStatus
    round_added: Optional[int] = None


class TuningRound(BaseModel):
    round_number: int
    ai_message: str
    user_response: Optional[str] = None
    applied_changes: list[str] = Field(default_factory=list)


class TuningState(BaseModel):
    status: TuningStatus = TuningStatus.NOT_STARTED
    completed_rounds: int = 0
    rounds: list[TuningRound] = Field(default_factory=list)


class FinancialCausalDAG(BaseModel):
    id: str
    name: str
    industry: Optional[str] = None
    company: Optional[str] = None
    goal: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    tuning_state: TuningState = Field(default_factory=TuningState)
    nodes: list[Node]
    edges: list[Edge]
    # 表示・切替可能な会計期間のラベル一覧（末尾が最新期）。
    # Nodeのvalues_by_periodのキーと対応する
    available_periods: list[str] = Field(default_factory=list)

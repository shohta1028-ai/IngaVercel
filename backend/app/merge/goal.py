"""Phase 4: ユーザーが設定する分析ゴールをDAGに反映する。"""

from __future__ import annotations

from datetime import datetime, timezone

from app.models.dag import FinancialCausalDAG


def set_goal(dag: FinancialCausalDAG, goal: str) -> FinancialCausalDAG:
    updated = dag.model_copy(update={"goal": goal, "updated_at": datetime.now(timezone.utc)})
    return updated

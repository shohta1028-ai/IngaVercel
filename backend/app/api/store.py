"""プロトタイプ用の簡易永続化。DBは使わず、1つのDAG状態をJSONファイルに
読み書きする（単一ユーザー・単一セッション前提）。
"""

from __future__ import annotations

from pathlib import Path

from app.api.seed import build_seed_dag
from app.models.dag import FinancialCausalDAG

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
CURRENT_DAG_PATH = DATA_DIR / "current_dag.json"


def load_dag() -> FinancialCausalDAG:
    if CURRENT_DAG_PATH.exists():
        return FinancialCausalDAG.model_validate_json(CURRENT_DAG_PATH.read_text(encoding="utf-8"))
    dag = build_seed_dag()
    save_dag(dag)
    return dag


def save_dag(dag: FinancialCausalDAG) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    CURRENT_DAG_PATH.write_text(dag.model_dump_json(indent=2), encoding="utf-8")


def reset_dag() -> FinancialCausalDAG:
    dag = build_seed_dag()
    save_dag(dag)
    return dag

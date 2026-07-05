"""プロトタイプ用の簡易永続化。DBは使わず、1つのDAG状態をJSONファイルに
読み書きする（単一ユーザー・単一セッション前提）。

Vercel Functions上ではデプロイされたバンドル自体は読み取り専用で、
書き込み可能なのは/tmpのみ（かつリクエスト間・インスタンス間で保持
されない）。VercelはデプロイのFunctionに自動的にVERCEL環境変数を設定
するため、それを検知して保存先を/tmpに切り替える（DAG状態が消えることは
許容する前提）。
"""

from __future__ import annotations

import os
from pathlib import Path

from app.api.seed import build_seed_dag
from app.models.dag import FinancialCausalDAG

_DEFAULT_DATA_DIR = (
    "/tmp/inga_analytics_data"
    if os.environ.get("VERCEL")
    else str(Path(__file__).resolve().parent.parent.parent / "data")
)
DATA_DIR = Path(os.environ.get("DAG_DATA_DIR", _DEFAULT_DATA_DIR))
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

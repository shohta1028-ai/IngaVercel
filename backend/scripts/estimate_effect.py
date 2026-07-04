"""Phase 6: 確定した因果DAGと実測データからDoWhyで因果効果を推定するCLIスクリプト。

LLM API呼び出しを伴わないため、ANTHROPIC_API_KEYなしでそのまま実行できる。

Usage:
    cd backend
    # サンプルDAG・合成データによるデモ実行
    python scripts/estimate_effect.py --demo truck_utilization_rate operating_income

    # 実際のDAG(JSON)・実測データ(CSV、列名はノードidと一致させる)を指定
    python scripts/estimate_effect.py --dag path/to/dag.json --data path/to/data.csv \
        truck_utilization_rate operating_income
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd

from app.causal.effect_estimation import estimate_causal_effect
from app.causal.sample_data import build_sample_manufacturing_dag, generate_synthetic_dataset
from app.models.dag import FinancialCausalDAG


def main() -> None:
    parser = argparse.ArgumentParser(description="確定済みDAGと実測データから因果効果を推定する")
    parser.add_argument("treatment", help="処置変数となるノードid")
    parser.add_argument("outcome", help="結果変数となるノードid")
    parser.add_argument("--dag", type=Path, help="DAGのJSONファイル（省略時はサンプルDAGを使用）")
    parser.add_argument("--data", type=Path, help="時系列データのCSV（省略時は合成データを使用）")
    parser.add_argument("--demo", action="store_true", help="サンプルDAG・合成データで実行する")
    args = parser.parse_args()

    if args.dag:
        dag = FinancialCausalDAG.model_validate_json(args.dag.read_text(encoding="utf-8"))
    else:
        dag = build_sample_manufacturing_dag()

    if args.data:
        data = pd.read_csv(args.data)
    else:
        data = generate_synthetic_dataset()

    result = estimate_causal_effect(dag, data, treatment_node_id=args.treatment, outcome_node_id=args.outcome)

    print(f"処置: {result.treatment_node_id}")
    print(f"結果: {result.outcome_node_id}")
    print(f"手法: {result.method_name}")
    print(f"バックドア調整変数: {result.backdoor_variables}")
    print(f"推定された因果効果: {result.estimated_effect:.4f}")


if __name__ == "__main__":
    main()

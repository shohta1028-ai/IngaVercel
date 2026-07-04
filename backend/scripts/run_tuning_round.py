"""Phase 5: 対話チューニングを1ラウンド分、対話形式で実行するCLIスクリプト。

実行には環境変数 ANTHROPIC_API_KEY が必要（実際にAPI課金が発生する）。

Usage:
    cd backend
    python scripts/run_tuning_round.py path/to/dag.json
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.models.dag import FinancialCausalDAG
from app.tuning.dialogue import apply_user_response, generate_next_proposal


def main() -> None:
    parser = argparse.ArgumentParser(description="対話チューニングを1ラウンド実行する")
    parser.add_argument("dag_file", type=Path, help="DAGのJSONファイル")
    args = parser.parse_args()

    dag = FinancialCausalDAG.model_validate_json(args.dag_file.read_text(encoding="utf-8"))

    proposal = generate_next_proposal(dag)
    if proposal is None:
        print("これ以上確認・提案する項目はありません。")
        return

    print(f"\n[ラウンド{proposal.round_number}] {proposal.ai_message}\n")
    user_response = input("あなたの回答> ")

    updated_dag = apply_user_response(dag, proposal, user_response)
    args.dag_file.write_text(updated_dag.model_dump_json(indent=2), encoding="utf-8")

    print(f"\n更新を保存しました: {args.dag_file}")
    print(
        f"チューニング状態: {updated_dag.tuning_state.status.value} "
        f"({updated_dag.tuning_state.completed_rounds}/5ラウンド完了)"
    )


if __name__ == "__main__":
    main()

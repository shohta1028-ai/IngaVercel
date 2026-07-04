"""業界標準DAGテンプレートを実際にLLM(Anthropic API)を呼び出して生成し、
sample_data/templates/ 配下にJSONとして保存するCLIスクリプト。

実行には環境変数 ANTHROPIC_API_KEY が必要（実際にAPI課金が発生する）。

Usage:
    cd backend
    python scripts/generate_template.py 製造業
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.llm.template_generator import generate_industry_template

OUTPUT_DIR = Path(__file__).resolve().parent.parent.parent / "sample_data" / "templates"


def main() -> None:
    parser = argparse.ArgumentParser(description="業界標準DAGテンプレートを生成する")
    parser.add_argument("industry", help="対象業界名（例: 製造業）")
    args = parser.parse_args()

    dag = generate_industry_template(args.industry)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / f"{args.industry}_template.json"
    output_path.write_text(dag.model_dump_json(indent=2, by_alias=True), encoding="utf-8")

    print(f"生成完了: {output_path}")
    print(f"ノード数: {len(dag.nodes)}, エッジ数: {len(dag.edges)}")


if __name__ == "__main__":
    main()

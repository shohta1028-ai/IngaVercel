"""ローカルのIR資料ファイルからLLMで財務・KPIデータを抽出するCLIスクリプト。

実行には環境変数 ANTHROPIC_API_KEY が必要（実際にAPI課金が発生する）。

Usage:
    cd backend
    python scripts/extract_ir_data.py ../sample_data/ir_pdfs/sample_manufacturing_ir.pdf
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.ingestion.file_loader import extract_text_from_file
from app.ingestion.ir_extractor import extract_ir_data_points


def main() -> None:
    parser = argparse.ArgumentParser(description="IR資料からKPIデータを抽出する")
    parser.add_argument("file", type=Path, help="IR資料ファイル（PDF/HTML/テキスト）")
    args = parser.parse_args()

    text = extract_text_from_file(args.file)
    data_points = extract_ir_data_points(text, document_name=args.file.name)

    print(json.dumps([dp.model_dump() for dp in data_points], ensure_ascii=False, indent=2))
    print(f"\n抽出件数: {len(data_points)}", file=sys.stderr)


if __name__ == "__main__":
    main()

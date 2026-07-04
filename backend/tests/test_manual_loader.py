from pathlib import Path

import pytest
from openpyxl import Workbook

from app.ingestion.manual_loader import load_manual_csv, load_manual_data, load_manual_excel
from app.ingestion.models import IRDataPointKind

SAMPLE_CSV = (
    Path(__file__).resolve().parent.parent.parent
    / "sample_data"
    / "manual"
    / "sample_manual_data.csv"
)


def test_load_manual_csv():
    data_points = load_manual_csv(SAMPLE_CSV)

    assert len(data_points) == 3
    first = data_points[0]
    assert first.label == "競合A社_工場稼働率"
    assert first.kind == IRDataPointKind.NONFINANCIAL
    assert first.value == 79.5
    assert first.unit == "%"
    assert first.source.document_name == "sample_manual_data.csv"


def test_load_manual_csv_missing_column_raises(tmp_path):
    bad_csv = tmp_path / "bad.csv"
    bad_csv.write_text("label,value\nfoo,1\n", encoding="utf-8")
    with pytest.raises(ValueError):
        load_manual_csv(bad_csv)


def test_load_manual_excel(tmp_path):
    xlsx_path = tmp_path / "sample.xlsx"
    wb = Workbook()
    ws = wb.active
    ws.append(["label", "kind", "value", "unit", "period"])
    ws.append(["競合B社_MAU", "nonfinancial", 12000, "千人", "2024年3月期"])
    wb.save(xlsx_path)

    data_points = load_manual_excel(xlsx_path)

    assert len(data_points) == 1
    assert data_points[0].label == "競合B社_MAU"
    assert data_points[0].value == 12000


def test_load_manual_data_dispatches_by_suffix():
    data_points = load_manual_data(SAMPLE_CSV)
    assert len(data_points) == 3

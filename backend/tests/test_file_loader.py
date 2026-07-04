from pathlib import Path

import pytest

from app.ingestion.file_loader import extract_text_from_file

SAMPLE_DIR = Path(__file__).resolve().parent.parent.parent / "sample_data" / "ir_pdfs"


def test_extract_text_from_txt():
    text = extract_text_from_file(SAMPLE_DIR / "sample_manufacturing_ir.txt")
    assert "工場稼働率" in text
    assert "トラック稼働率" in text


def test_extract_text_from_pdf():
    text = extract_text_from_file(SAMPLE_DIR / "sample_manufacturing_ir.pdf")
    assert "工場稼働率" in text
    assert "物流効率化" in text


def test_extract_text_from_html(tmp_path):
    html_path = tmp_path / "sample.html"
    html_path.write_text(
        "<html><body><h1>売上高</h1><p>1,250億円</p></body></html>", encoding="utf-8"
    )
    text = extract_text_from_file(html_path)
    assert "売上高" in text
    assert "1,250億円" in text


def test_unsupported_suffix_raises(tmp_path):
    path = tmp_path / "sample.docx"
    path.write_text("dummy", encoding="utf-8")
    with pytest.raises(ValueError):
        extract_text_from_file(path)

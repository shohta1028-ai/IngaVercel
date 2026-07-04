import json
from dataclasses import dataclass

from app.ingestion.ir_extractor import extract_ir_data_points
from app.ingestion.models import IRDataPointKind

FAKE_LLM_JSON = {
    "data_points": [
        {
            "label": "売上高",
            "kind": "financial",
            "value": 125000,
            "unit": "百万円",
            "period": "2024年3月期",
            "excerpt": "売上高1,250億円（前期比+4.2%）",
        },
        {
            "label": "トラック稼働率",
            "kind": "nonfinancial",
            "value": 72.3,
            "unit": "%",
            "period": "2024年3月期",
            "excerpt": "トラック稼働率は...2024年3月期には72.3%へ上昇",
        },
    ]
}


@dataclass
class _FakeTextBlock:
    text: str
    type: str = "text"


class _FakeMessages:
    def create(self, **kwargs):
        @dataclass
        class _FakeResponse:
            content: list

        return _FakeResponse(
            content=[_FakeTextBlock(text=json.dumps(FAKE_LLM_JSON, ensure_ascii=False))]
        )


class _FakeAnthropicClient:
    def __init__(self):
        self.messages = _FakeMessages()


def test_extract_ir_data_points_parses_llm_output():
    data_points = extract_ir_data_points(
        document_text="(サンプルIRテキスト)",
        document_name="sample_manufacturing_ir.pdf",
        client=_FakeAnthropicClient(),
    )

    assert len(data_points) == 2

    revenue = next(dp for dp in data_points if dp.label == "売上高")
    assert revenue.kind == IRDataPointKind.FINANCIAL
    assert revenue.value == 125000
    assert revenue.source.document_name == "sample_manufacturing_ir.pdf"
    assert revenue.source.excerpt is not None

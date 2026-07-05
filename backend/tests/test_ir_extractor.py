import json
from dataclasses import dataclass

import pytest

from app.ingestion.ir_extractor import MAX_DOCUMENT_TEXT_CHARS, extract_ir_data_points
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
            stop_reason: str = "end_turn"

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


class _EmptyResponseMessages:
    def create(self, **kwargs):
        @dataclass
        class _FakeResponse:
            content: list
            stop_reason: str = "end_turn"

        return _FakeResponse(content=[_FakeTextBlock(text="")])


class _EmptyResponseClient:
    def __init__(self):
        self.messages = _EmptyResponseMessages()


def test_extract_ir_data_points_raises_clear_error_on_empty_llm_response():
    with pytest.raises(ValueError, match="空の応答"):
        extract_ir_data_points(
            document_text="(サンプルIRテキスト)",
            document_name="sample.pdf",
            client=_EmptyResponseClient(),
        )


class _CapturingMessages:
    def __init__(self):
        self.received_prompt: str | None = None

    def create(self, **kwargs):
        @dataclass
        class _FakeResponse:
            content: list
            stop_reason: str = "end_turn"

        self.received_prompt = kwargs["messages"][0]["content"]
        return _FakeResponse(
            content=[_FakeTextBlock(text=json.dumps(FAKE_LLM_JSON, ensure_ascii=False))]
        )


class _CapturingClient:
    def __init__(self):
        self.messages = _CapturingMessages()


def test_extract_ir_data_points_truncates_oversized_document_text():
    client = _CapturingClient()

    extract_ir_data_points(
        document_text="あ" * (MAX_DOCUMENT_TEXT_CHARS * 2),
        document_name="huge.pdf",
        client=client,
    )

    assert client.messages.received_prompt is not None
    assert len(client.messages.received_prompt) < MAX_DOCUMENT_TEXT_CHARS + 100


class _MaxTokensMessages:
    def create(self, **kwargs):
        @dataclass
        class _FakeResponse:
            content: list
            stop_reason: str = "end_turn"

        # 指標が多すぎて出力上限に達し、JSON文字列の途中で応答が切れたケースを再現
        truncated_json = '{"data_points": [{"label": "売上高", "kind": "financial'
        return _FakeResponse(content=[_FakeTextBlock(text=truncated_json)], stop_reason="max_tokens")


class _MaxTokensClient:
    def __init__(self):
        self.messages = _MaxTokensMessages()


def test_extract_ir_data_points_raises_clear_error_when_truncated_by_max_tokens():
    with pytest.raises(ValueError, match="最大出力トークン数"):
        extract_ir_data_points(
            document_text="(サンプルIRテキスト)",
            document_name="huge.pdf",
            client=_MaxTokensClient(),
        )


class _MalformedJsonMessages:
    def create(self, **kwargs):
        @dataclass
        class _FakeResponse:
            content: list
            stop_reason: str = "end_turn"

        return _FakeResponse(content=[_FakeTextBlock(text="これはJSONではありません")])


class _MalformedJsonClient:
    def __init__(self):
        self.messages = _MalformedJsonMessages()


def test_extract_ir_data_points_raises_clear_error_on_malformed_json():
    with pytest.raises(ValueError, match="JSONとして解釈できません"):
        extract_ir_data_points(
            document_text="(サンプルIRテキスト)",
            document_name="sample.pdf",
            client=_MalformedJsonClient(),
        )

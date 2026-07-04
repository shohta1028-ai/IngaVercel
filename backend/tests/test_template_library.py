import json
from dataclasses import dataclass

import pytest

from app.api.template_library import (
    CATALOG,
    get_or_generate_entry,
    list_catalog,
    load_entry,
)

FAKE_LLM_JSON = {
    "summary": "製造業は設備投資と稼働率が原価構造を左右する。",
    "nodes": [
        {
            "id": "revenue",
            "label": "売上高",
            "category": "PL",
            "statement": "売上高",
            "unit": "円",
            "description": "当期の売上高",
        },
    ],
    "edges": [],
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

        return _FakeResponse(content=[_FakeTextBlock(text=json.dumps(FAKE_LLM_JSON, ensure_ascii=False))])


class _FakeAnthropicClient:
    def __init__(self):
        self.messages = _FakeMessages()


@pytest.fixture(autouse=True)
def _isolate_library_dir(tmp_path, monkeypatch):
    import app.api.template_library as template_library_module

    monkeypatch.setattr(template_library_module, "LIBRARY_DIR", tmp_path)


def test_list_catalog_returns_all_industries_uncached_initially():
    items = list_catalog()

    assert len(items) == len(CATALOG)
    assert all(not item.cached for item in items)
    assert all(item.summary is None for item in items)


def test_get_or_generate_entry_generates_and_caches():
    client = _FakeAnthropicClient()

    entry = get_or_generate_entry("manufacturing", client=client)

    assert entry.industry_id == "manufacturing"
    assert entry.industry_label == "製造業"
    assert entry.summary == FAKE_LLM_JSON["summary"]
    assert len(entry.dag.nodes) == 1

    # キャッシュファイルに保存されている
    cached = load_entry("manufacturing")
    assert cached is not None
    assert cached.summary == entry.summary


def test_get_or_generate_entry_uses_cache_without_calling_llm_again():
    first_client = _FakeAnthropicClient()
    get_or_generate_entry("retail", client=first_client)

    class _ExplodingClient:
        @property
        def messages(self):
            raise AssertionError("キャッシュがあるのにLLMを再度呼び出した")

    # 2回目はキャッシュから読むだけで、client引数を渡さなくても
    # (=Anthropic()が実際に呼ばれる状況でも)呼び出しに進まないことを確認
    entry = get_or_generate_entry("retail", client=_ExplodingClient())
    assert entry.industry_id == "retail"


def test_get_or_generate_entry_raises_for_unknown_industry():
    with pytest.raises(ValueError):
        get_or_generate_entry("nonexistent", client=_FakeAnthropicClient())


def test_list_catalog_reflects_cached_entry():
    get_or_generate_entry("saas", client=_FakeAnthropicClient())

    items = list_catalog()
    saas_item = next(i for i in items if i.industry_id == "saas")

    assert saas_item.cached is True
    assert saas_item.summary == FAKE_LLM_JSON["summary"]

"""業界別テンプレートのカタログとファイルキャッシュ。

ユーザーが「この業界のテンプレートで始めたい」を選べるよう、あらかじめ
決めた業界一覧(CATALOG)について、LLM生成結果(DAG＋業界サマリー)を
JSONファイルにキャッシュする。一度生成した業界は再生成せず、
キャッシュから読み込むだけにすることでLLM呼び出しのコストを抑える。
"""

from __future__ import annotations

from pathlib import Path

from anthropic import Anthropic
from pydantic import BaseModel

from app.llm.template_generator import generate_industry_template_with_summary
from app.models.dag import FinancialCausalDAG

CATALOG: list[dict[str, str]] = [
    {"id": "manufacturing", "label": "製造業"},
    {"id": "retail", "label": "小売業"},
    {"id": "saas", "label": "SaaS"},
    {"id": "infrastructure", "label": "インフラ"},
    {"id": "services", "label": "サービス業"},
]

LIBRARY_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "template_library"


class TemplateLibraryEntry(BaseModel):
    industry_id: str
    industry_label: str
    summary: str
    dag: FinancialCausalDAG


class TemplateLibraryListItem(BaseModel):
    industry_id: str
    industry_label: str
    cached: bool
    summary: str | None = None


def _catalog_label(industry_id: str) -> str:
    for entry in CATALOG:
        if entry["id"] == industry_id:
            return entry["label"]
    raise ValueError(f"カタログに存在しない業界idです: {industry_id}")


def _entry_path(industry_id: str) -> Path:
    return LIBRARY_DIR / f"{industry_id}.json"


def load_entry(industry_id: str) -> TemplateLibraryEntry | None:
    path = _entry_path(industry_id)
    if not path.exists():
        return None
    return TemplateLibraryEntry.model_validate_json(path.read_text(encoding="utf-8"))


def save_entry(entry: TemplateLibraryEntry) -> None:
    LIBRARY_DIR.mkdir(parents=True, exist_ok=True)
    _entry_path(entry.industry_id).write_text(
        entry.model_dump_json(indent=2), encoding="utf-8"
    )


def list_catalog() -> list[TemplateLibraryListItem]:
    items = []
    for c in CATALOG:
        cached_entry = load_entry(c["id"])
        items.append(
            TemplateLibraryListItem(
                industry_id=c["id"],
                industry_label=c["label"],
                cached=cached_entry is not None,
                summary=cached_entry.summary if cached_entry else None,
            )
        )
    return items


def get_or_generate_entry(
    industry_id: str, client: Anthropic | None = None
) -> TemplateLibraryEntry:
    """キャッシュがあれば読み込むだけ、無ければLLMで生成しキャッシュする。"""
    cached = load_entry(industry_id)
    if cached is not None:
        return cached

    label = _catalog_label(industry_id)
    dag, summary = generate_industry_template_with_summary(label, client=client)
    entry = TemplateLibraryEntry(
        industry_id=industry_id, industry_label=label, summary=summary, dag=dag
    )
    save_entry(entry)
    return entry

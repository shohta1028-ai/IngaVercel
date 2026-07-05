"""Phase 3: EDINET API（金融庁）による法定開示書類の検索・取得。

EDINETは有価証券報告書・四半期報告書等の法定開示書類を提供する金融庁の
公式API。robots.txt/利用規約の懸念がある個別企業サイトへの自動巡回とは
異なり、公開データとして自動取得されることを前提に金融庁自身が提供して
いるため、Phase3で保留していた「実サイト自動収集」のうち、このAPI経由の
取得のみをオンデマンド（ユーザー操作時のみ）で実装する。

EDINET APIには企業名で直接検索するエンドポイントが無く、日付ごとに
その日提出された全書類のメタデータ一覧を取得してクライアント側で
filerName/secCodeをフィルタする必要がある。日付範囲を広げるほど逐次
リクエスト数が増えるため、検索範囲は最大MAX_SEARCH_DAYS日に制限し、
リクエスト間に短いsleepを挟んで節度を持たせる。
"""

from __future__ import annotations

import os
import time
from datetime import date, timedelta

import httpx
from pydantic import BaseModel

EDINET_API_BASE = "https://api.edinet-fsa.go.jp/api/v2"
MAX_SEARCH_DAYS = 31
REQUEST_INTERVAL_SECONDS = 0.3


class EdinetDocumentSummary(BaseModel):
    doc_id: str
    filer_name: str
    sec_code: str | None = None
    doc_description: str | None = None
    period_end: str | None = None
    submit_date_time: str | None = None


def _get_api_key() -> str:
    api_key = os.environ.get("EDINET_API_KEY")
    if not api_key:
        raise ValueError(
            "EDINET_API_KEYが設定されていません。EDINETサイトで無料のAPIキーを"
            "取得し、backend/.envのEDINET_API_KEYに設定してください。"
        )
    return api_key


def search_documents(
    company_query: str,
    from_date: date,
    to_date: date,
    http_client: httpx.Client | None = None,
) -> list[EdinetDocumentSummary]:
    """指定期間内にfiler_name(部分一致)またはsec_code(完全一致)が一致する
    書類のメタデータを検索する。"""
    if to_date < from_date:
        raise ValueError("to_dateはfrom_date以降の日付にしてください")
    if (to_date - from_date).days > MAX_SEARCH_DAYS:
        raise ValueError(f"検索できる日付範囲は最大{MAX_SEARCH_DAYS}日間です")

    normalized_query = company_query.strip().lower()
    if not normalized_query:
        raise ValueError("company_queryを指定してください")

    api_key = _get_api_key()
    client = http_client or httpx.Client(timeout=15.0)
    owns_client = http_client is None

    matches: list[EdinetDocumentSummary] = []
    try:
        current = from_date
        is_first_request = True
        while current <= to_date:
            if not is_first_request:
                time.sleep(REQUEST_INTERVAL_SECONDS)
            is_first_request = False

            response = client.get(
                f"{EDINET_API_BASE}/documents.json",
                params={"date": current.isoformat(), "type": 2, "Subscription-Key": api_key},
            )
            response.raise_for_status()
            data = response.json()

            for item in data.get("results", []):
                filer_name = item.get("filerName") or ""
                sec_code = item.get("secCode")
                name_match = normalized_query in filer_name.lower()
                sec_code_match = sec_code is not None and normalized_query == sec_code.strip().lower()
                if name_match or sec_code_match:
                    matches.append(
                        EdinetDocumentSummary(
                            doc_id=item["docID"],
                            filer_name=filer_name,
                            sec_code=sec_code,
                            doc_description=item.get("docDescription"),
                            period_end=item.get("periodEnd"),
                            submit_date_time=item.get("submitDateTime"),
                        )
                    )
            current += timedelta(days=1)
    finally:
        if owns_client:
            client.close()

    return matches


def fetch_document_pdf(doc_id: str, http_client: httpx.Client | None = None) -> bytes:
    """指定した書類IDのPDFバイナリを取得する。"""
    api_key = _get_api_key()
    client = http_client or httpx.Client(timeout=30.0)
    owns_client = http_client is None
    try:
        response = client.get(
            f"{EDINET_API_BASE}/documents/{doc_id}",
            params={"type": 2, "Subscription-Key": api_key},
        )
        response.raise_for_status()
        return response.content
    finally:
        if owns_client:
            client.close()

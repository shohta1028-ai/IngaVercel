from datetime import date

import pytest

from app.ingestion.edinet_client import (
    MAX_SEARCH_DAYS,
    fetch_document_pdf,
    search_documents,
)


class _FakeResponse:
    def __init__(self, json_data=None, content=b""):
        self._json_data = json_data
        self.content = content

    def raise_for_status(self):
        pass

    def json(self):
        return self._json_data


class _FakeHttpClient:
    def __init__(self, results_by_date=None, pdf_bytes=b"%PDF-1.4 fake"):
        self.results_by_date = results_by_date or {}
        self.pdf_bytes = pdf_bytes
        self.calls: list[tuple[str, dict]] = []

    def get(self, url, params=None):
        self.calls.append((url, params))
        if url.endswith("documents.json"):
            results = self.results_by_date.get(params["date"], [])
            return _FakeResponse(json_data={"results": results})
        return _FakeResponse(content=self.pdf_bytes)


@pytest.fixture(autouse=True)
def _set_api_key(monkeypatch):
    monkeypatch.setenv("EDINET_API_KEY", "dummy-key")


def test_search_documents_filters_by_filer_name_substring():
    fake_client = _FakeHttpClient(
        results_by_date={
            "2026-06-24": [
                {"docID": "S100ABCD", "filerName": "ファナック株式会社", "secCode": "69540", "docDescription": "有価証券報告書"},
                {"docID": "S100WXYZ", "filerName": "他社株式会社", "secCode": "99990", "docDescription": "有価証券報告書"},
            ]
        }
    )

    results = search_documents(
        "ファナック",
        from_date=date(2026, 6, 24),
        to_date=date(2026, 6, 24),
        http_client=fake_client,
    )

    assert len(results) == 1
    assert results[0].doc_id == "S100ABCD"
    assert results[0].filer_name == "ファナック株式会社"


def test_search_documents_filters_by_sec_code_exact_match():
    fake_client = _FakeHttpClient(
        results_by_date={
            "2026-06-24": [
                {"docID": "S100ABCD", "filerName": "ファナック株式会社", "secCode": "69540", "docDescription": "有価証券報告書"},
            ]
        }
    )

    results = search_documents(
        "69540",
        from_date=date(2026, 6, 24),
        to_date=date(2026, 6, 24),
        http_client=fake_client,
    )

    assert len(results) == 1

    no_match = search_documents(
        "12345",
        from_date=date(2026, 6, 24),
        to_date=date(2026, 6, 24),
        http_client=fake_client,
    )
    assert no_match == []


def test_search_documents_queries_each_date_in_range():
    fake_client = _FakeHttpClient(results_by_date={})

    search_documents(
        "ファナック",
        from_date=date(2026, 6, 1),
        to_date=date(2026, 6, 3),
        http_client=fake_client,
    )

    queried_dates = [call[1]["date"] for call in fake_client.calls]
    assert queried_dates == ["2026-06-01", "2026-06-02", "2026-06-03"]


def test_search_documents_raises_for_range_exceeding_max_days():
    fake_client = _FakeHttpClient()
    with pytest.raises(ValueError, match=f"{MAX_SEARCH_DAYS}日"):
        search_documents(
            "ファナック",
            from_date=date(2026, 1, 1),
            to_date=date(2026, 12, 31),
            http_client=fake_client,
        )


def test_search_documents_raises_for_inverted_range():
    fake_client = _FakeHttpClient()
    with pytest.raises(ValueError):
        search_documents(
            "ファナック",
            from_date=date(2026, 6, 10),
            to_date=date(2026, 6, 1),
            http_client=fake_client,
        )


def test_search_documents_raises_without_api_key(monkeypatch):
    monkeypatch.delenv("EDINET_API_KEY", raising=False)
    fake_client = _FakeHttpClient()
    with pytest.raises(ValueError, match="EDINET_API_KEY"):
        search_documents(
            "ファナック",
            from_date=date(2026, 6, 1),
            to_date=date(2026, 6, 1),
            http_client=fake_client,
        )


def test_fetch_document_pdf_returns_bytes():
    fake_client = _FakeHttpClient(pdf_bytes=b"%PDF-1.4 dummy content")
    result = fetch_document_pdf("S100ABCD", http_client=fake_client)
    assert result == b"%PDF-1.4 dummy content"


def test_fetch_document_pdf_raises_without_api_key(monkeypatch):
    monkeypatch.delenv("EDINET_API_KEY", raising=False)
    fake_client = _FakeHttpClient()
    with pytest.raises(ValueError, match="EDINET_API_KEY"):
        fetch_document_pdf("S100ABCD", http_client=fake_client)

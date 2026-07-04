"""tests/support/fake_llm_client.py がコピー元として正しく機能するかの確認。

他プロジェクトへ展開する雛形なので、ここでは最小限の動作確認のみ行う。
"""

import json

import pytest

from tests.support.fake_llm_client import ScriptedLLMClient


def test_scripted_llm_client_returns_matching_payload():
    client = ScriptedLLMClient({"marker-a": {"message": "hello"}})

    response = client.messages.create(system="this has marker-a in it")

    assert json.loads(response.content[0].text) == {"message": "hello"}


def test_scripted_llm_client_raises_for_unmatched_request():
    client = ScriptedLLMClient({"marker-a": {"message": "hello"}})

    with pytest.raises(AssertionError):
        client.messages.create(system="no matching marker here")

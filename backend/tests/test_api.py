import pytest
from fastapi.testclient import TestClient

from app.api import store as store_module


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(store_module, "DATA_DIR", tmp_path)
    monkeypatch.setattr(store_module, "CURRENT_DAG_PATH", tmp_path / "current_dag.json")

    from app.api.main import app

    return TestClient(app)


def test_get_dag_returns_seed_on_first_call(client):
    response = client.get("/api/dag")
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == "dag_sample_001"
    assert len(body["nodes"]) == 10
    assert body["goal"] == "物流効率化による営業利益改善"


def test_patch_goal_updates_and_persists(client):
    response = client.patch("/api/dag/goal", json={"goal": "新しいゴール"})
    assert response.status_code == 200
    assert response.json()["goal"] == "新しいゴール"

    # 永続化されているか確認
    again = client.get("/api/dag")
    assert again.json()["goal"] == "新しいゴール"


def test_post_edge_adds_edge(client):
    response = client.post(
        "/api/dag/edges",
        json={"source_node_id": "inventory_turnover", "target_node_id": "revenue"},
    )
    assert response.status_code == 200
    edges = response.json()["edges"]
    new_edges = [e for e in edges if e["source_node_id"] == "inventory_turnover"]
    assert len(new_edges) == 1
    assert new_edges[0]["status"] == "user_confirmed"
    assert new_edges[0]["sign"] == "ambiguous"


def test_post_edge_with_unknown_node_returns_400(client):
    response = client.post(
        "/api/dag/edges",
        json={"source_node_id": "nonexistent", "target_node_id": "revenue"},
    )
    assert response.status_code == 400


def test_reset_restores_seed(client):
    client.patch("/api/dag/goal", json={"goal": "変更後"})
    response = client.post("/api/dag/reset")
    assert response.status_code == 200
    assert response.json()["goal"] == "物流効率化による営業利益改善"

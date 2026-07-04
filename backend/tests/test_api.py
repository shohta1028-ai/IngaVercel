import io

import pytest
from fastapi.testclient import TestClient

from app.api import store as store_module
from app.ingestion.models import IRDataPoint, IRDataPointKind, IRDataSource
from app.models.dag import FinancialCausalDAG, Node, NodeCategory, NodeSource


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(store_module, "DATA_DIR", tmp_path)
    monkeypatch.setattr(store_module, "CURRENT_DAG_PATH", tmp_path / "current_dag.json")

    import app.api.template_library as template_library_module

    monkeypatch.setattr(template_library_module, "LIBRARY_DIR", tmp_path / "template_library")

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


def test_generate_template_replaces_current_dag(client, monkeypatch):
    fake_dag = FinancialCausalDAG(
        id="dag_fake",
        name="fake",
        industry="小売",
        nodes=[Node(id="revenue", label="売上高", category=NodeCategory.PL, source=NodeSource.TEMPLATE)],
        edges=[],
    )
    monkeypatch.setattr("app.api.main.generate_industry_template", lambda industry: fake_dag)

    response = client.post("/api/templates/generate", json={"industry": "小売"})
    assert response.status_code == 200
    assert response.json()["id"] == "dag_fake"

    again = client.get("/api/dag")
    assert again.json()["id"] == "dag_fake"


def test_generate_template_llm_failure_returns_502(client, monkeypatch):
    def _raise(industry):
        raise RuntimeError("boom")

    monkeypatch.setattr("app.api.main.generate_industry_template", _raise)

    response = client.post("/api/templates/generate", json={"industry": "小売"})
    assert response.status_code == 502


def test_ir_extract_with_csv_does_not_call_llm(client):
    csv_content = (
        "label,kind,value,unit,period\n"
        "競合A社_工場稼働率,nonfinancial,79.5,%,2024年3月期\n"
    ).encode("utf-8")

    response = client.post(
        "/api/ir/extract",
        files={"file": ("manual.csv", io.BytesIO(csv_content), "text/csv")},
    )
    assert response.status_code == 200
    data_points = response.json()
    assert len(data_points) == 1
    assert data_points[0]["label"] == "競合A社_工場稼働率"


def test_ir_extract_with_text_uses_mocked_llm(client, monkeypatch):
    fake_points = [
        IRDataPoint(
            label="売上高",
            kind=IRDataPointKind.FINANCIAL,
            value=1000,
            unit="百万円",
            source=IRDataSource(document_name="sample.txt"),
        )
    ]
    monkeypatch.setattr(
        "app.api.main.extract_ir_data_points", lambda text, document_name: fake_points
    )

    response = client.post(
        "/api/ir/extract",
        files={"file": ("sample.txt", io.BytesIO("ダミーIRテキスト".encode("utf-8")), "text/plain")},
    )
    assert response.status_code == 200
    assert response.json()[0]["label"] == "売上高"


def test_ir_merge_adds_unconnected_candidate_node(client):
    data_points = [
        {
            "label": "アプリMAU",
            "kind": "nonfinancial",
            "value": 5000,
            "unit": "千人",
            "period": "2024年3月期",
            "source": {"document_name": "sample.pdf", "excerpt": "抜粋"},
        }
    ]
    response = client.post(
        "/api/ir/merge", json={"data_points": data_points, "source": "ir_data"}
    )
    assert response.status_code == 200
    body = response.json()
    new_nodes = [n for n in body["nodes"] if n["label"] == "アプリMAU"]
    assert len(new_nodes) == 1
    assert new_nodes[0]["source"] == "ir_data"


def test_causal_available_nodes_includes_seed_nodes(client):
    response = client.get("/api/causal/available-nodes")
    assert response.status_code == 200
    assert "operating_income" in response.json()


def test_causal_estimate_returns_effect_for_confirmed_edge(client):
    response = client.post(
        "/api/causal/estimate",
        json={"treatment_node_id": "plant_utilization_rate", "outcome_node_id": "cogs"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["treatment_node_id"] == "plant_utilization_rate"
    assert isinstance(body["estimated_effect"], float)


def test_causal_estimate_unknown_node_returns_400(client):
    response = client.post(
        "/api/causal/estimate",
        json={"treatment_node_id": "nonexistent", "outcome_node_id": "cogs"},
    )
    assert response.status_code == 400


def test_causal_edge_effects_returns_value_for_each_confirmed_edge(client):
    dag = client.get("/api/dag").json()
    confirmed_edge_ids = {
        e["id"] for e in dag["edges"] if e["status"] in ("user_confirmed", "user_modified")
    }

    response = client.post("/api/causal/edge-effects")

    assert response.status_code == 200
    body = response.json()
    assert set(body.keys()) == confirmed_edge_ids
    assert all(isinstance(v, float) for v in body.values())


def test_causal_whatif_projects_downstream_nodes(client):
    response = client.post(
        "/api/causal/whatif",
        json={"source_node_id": "plant_utilization_rate", "delta_percent": 10},
    )
    assert response.status_code == 200
    body = response.json()
    node_ids = {p["node_id"] for p in body}
    assert "cogs" in node_ids
    first = body[0]
    assert first["projected"] == pytest.approx(first["baseline"] + first["delta_absolute"])


def test_causal_whatif_unknown_node_returns_400(client):
    response = client.post(
        "/api/causal/whatif",
        json={"source_node_id": "nonexistent", "delta_percent": 10},
    )
    assert response.status_code == 400


def test_template_library_list_returns_catalog(client):
    response = client.get("/api/template-library")
    assert response.status_code == 200
    body = response.json()
    assert {"manufacturing", "retail", "saas", "infrastructure", "services"} == {
        item["industry_id"] for item in body
    }
    assert all(not item["cached"] for item in body)


def test_template_library_entry_generates_and_caches(client, monkeypatch):
    fake_dag = FinancialCausalDAG(
        id="dag_fake",
        name="fake",
        industry="製造業",
        nodes=[Node(id="revenue", label="売上高", category=NodeCategory.PL, source=NodeSource.TEMPLATE)],
        edges=[],
    )
    monkeypatch.setattr(
        "app.api.template_library.generate_industry_template_with_summary",
        lambda industry, client=None: (fake_dag, "製造業のサマリー"),
    )

    response = client.get("/api/template-library/manufacturing")
    assert response.status_code == 200
    body = response.json()
    assert body["industry_label"] == "製造業"
    assert body["summary"] == "製造業のサマリー"

    # 2回目はキャッシュから返るのでlist側もcached=trueになる
    list_response = client.get("/api/template-library")
    manufacturing_item = next(
        i for i in list_response.json() if i["industry_id"] == "manufacturing"
    )
    assert manufacturing_item["cached"] is True


def test_template_library_entry_unknown_industry_returns_404(client):
    response = client.get("/api/template-library/nonexistent")
    assert response.status_code == 404


def test_template_library_apply_replaces_current_dag(client, monkeypatch):
    fake_dag = FinancialCausalDAG(
        id="dag_fake_retail",
        name="fake",
        industry="小売業",
        nodes=[Node(id="revenue", label="売上高", category=NodeCategory.PL, source=NodeSource.TEMPLATE)],
        edges=[],
    )
    monkeypatch.setattr(
        "app.api.template_library.generate_industry_template_with_summary",
        lambda industry, client=None: (fake_dag, "小売業のサマリー"),
    )

    response = client.post("/api/template-library/retail/apply")
    assert response.status_code == 200
    assert response.json()["id"] == "dag_fake_retail"

    current = client.get("/api/dag").json()
    assert current["id"] == "dag_fake_retail"

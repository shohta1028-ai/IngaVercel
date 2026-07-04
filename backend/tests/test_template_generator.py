import json
from dataclasses import dataclass

from app.llm.template_generator import generate_industry_template
from app.models.dag import EdgeSign, EdgeStatus, NodeCategory, NodeSource

FAKE_LLM_JSON = {
    "nodes": [
        {
            "id": "revenue",
            "label": "売上高",
            "category": "PL",
            "statement": "売上高",
            "unit": "円",
            "description": "当期の売上高",
        },
        {
            "id": "operating_income",
            "label": "営業利益",
            "category": "PL",
            "statement": "営業利益",
            "unit": "円",
            "description": "売上高から売上原価・販管費を控除した利益",
        },
        {
            "id": "plant_utilization_rate",
            "label": "工場稼働率",
            "category": "KPI_nonfinancial",
            "statement": None,
            "unit": "%",
            "description": "製造ラインの稼働率",
        },
    ],
    "edges": [
        {
            "source_node_id": "revenue",
            "target_node_id": "operating_income",
            "sign": "positive",
            "rationale": "売上高の増加は営業利益を押し上げる",
        },
        {
            "source_node_id": "plant_utilization_rate",
            "target_node_id": "operating_income",
            "sign": "positive",
            "rationale": "稼働率上昇は固定費配賦効率を改善し利益を押し上げる",
        },
    ],
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


def test_generate_industry_template_parses_llm_output_into_dag():
    dag = generate_industry_template("製造業", client=_FakeAnthropicClient())

    assert dag.industry == "製造業"
    assert len(dag.nodes) == 3
    assert len(dag.edges) == 2

    node_ids = {n.id for n in dag.nodes}
    assert node_ids == {"revenue", "operating_income", "plant_utilization_rate"}

    revenue_node = next(n for n in dag.nodes if n.id == "revenue")
    assert revenue_node.category == NodeCategory.PL
    assert revenue_node.source == NodeSource.TEMPLATE

    for edge in dag.edges:
        assert edge.status == EdgeStatus.AI_PROPOSED
        assert edge.sign in (EdgeSign.POSITIVE, EdgeSign.NEGATIVE, EdgeSign.AMBIGUOUS)

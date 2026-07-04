import json
from dataclasses import dataclass

from app.merge.node_ops import add_node
from app.models.dag import (
    Edge,
    EdgeSign,
    EdgeStatus,
    FinancialCausalDAG,
    Node,
    NodeCategory,
    NodeSource,
    TuningRound,
    TuningStatus,
)
from app.tuning.dialogue import apply_user_response, generate_next_proposal
from app.tuning.models import ProposalKind


def _base_dag(edges=None, nodes_extra=None) -> FinancialCausalDAG:
    revenue = Node(id="revenue", label="売上高", category=NodeCategory.PL, source=NodeSource.TEMPLATE)
    operating_income = Node(
        id="operating_income", label="営業利益", category=NodeCategory.PL, source=NodeSource.TEMPLATE
    )
    nodes = [revenue, operating_income] + (nodes_extra or [])
    return FinancialCausalDAG(
        id="dag_test",
        name="テストDAG",
        goal="在庫削減による営業CSの改善",
        nodes=nodes,
        edges=edges if edges is not None else [],
    )


@dataclass
class _FakeTextBlock:
    text: str
    type: str = "text"


@dataclass
class _FakeResponse:
    content: list


class _ScriptedAnthropicClient:
    """systemプロンプトの内容に応じて異なる固定JSONを返すフェイクLLMクライアント"""

    def __init__(self, responses_by_marker: dict[str, dict]):
        self._responses_by_marker = responses_by_marker
        self.messages = self

    def create(self, system: str, **kwargs):
        for marker, payload in self._responses_by_marker.items():
            if marker in system:
                return _FakeResponse(
                    content=[_FakeTextBlock(text=json.dumps(payload, ensure_ascii=False))]
                )
        raise AssertionError("未定義のsystemプロンプトが呼ばれました")


def test_generate_next_proposal_prioritizes_pending_ai_edge():
    edge = Edge(
        id="e1",
        source_node_id="revenue",
        target_node_id="operating_income",
        sign=EdgeSign.POSITIVE,
        status=EdgeStatus.AI_PROPOSED,
        rationale="売上高増加は営業利益を押し上げる",
    )
    dag = _base_dag(edges=[edge])
    client = _ScriptedAnthropicClient(
        {"1問だけ確認する短い日本語のメッセージ": {"message": "この因果関係でよろしいですか？"}}
    )

    proposal = generate_next_proposal(dag, client=client)

    assert proposal is not None
    assert proposal.kind == ProposalKind.CONFIRM_EDGE
    assert proposal.candidate_edge.id == "e1"
    assert proposal.round_number == 1


def test_generate_next_proposal_falls_back_to_unconnected_node():
    truck = Node(
        id="truck_utilization_rate",
        label="トラック稼働率",
        category=NodeCategory.KPI_NONFINANCIAL,
        source=NodeSource.USER_ADDED,
    )
    confirmed_edge = Edge(
        id="e1",
        source_node_id="revenue",
        target_node_id="operating_income",
        sign=EdgeSign.POSITIVE,
        status=EdgeStatus.USER_CONFIRMED,
    )
    dag = _base_dag(edges=[confirmed_edge], nodes_extra=[truck])
    client = _ScriptedAnthropicClient(
        {
            "紐付ける提案": {
                "message": "配送費との因果関係を追加してよろしいですか？",
                "target_node_id": "operating_income",
                "sign": "negative",
                "rationale": "トラック稼働率の改善は配送費を下げ営業利益を押し上げる",
            }
        }
    )

    proposal = generate_next_proposal(dag, client=client)

    assert proposal is not None
    assert proposal.kind == ProposalKind.CONNECT_NODE
    assert proposal.candidate_edge.source_node_id == "truck_utilization_rate"
    assert proposal.candidate_edge.target_node_id == "operating_income"
    assert proposal.candidate_edge.status == EdgeStatus.AI_PROPOSED


def test_generate_next_proposal_returns_none_when_nothing_to_review():
    dag = _base_dag(
        edges=[
            Edge(
                id="e1",
                source_node_id="revenue",
                target_node_id="operating_income",
                sign=EdgeSign.POSITIVE,
                status=EdgeStatus.USER_CONFIRMED,
            )
        ]
    )
    assert generate_next_proposal(dag, client=_ScriptedAnthropicClient({})) is None


def test_apply_user_response_confirm_marks_edge_confirmed():
    edge = Edge(
        id="e1",
        source_node_id="revenue",
        target_node_id="operating_income",
        sign=EdgeSign.POSITIVE,
        status=EdgeStatus.AI_PROPOSED,
    )
    dag = _base_dag(edges=[edge])
    from app.tuning.models import TuningProposal

    proposal = TuningProposal(
        round_number=1, kind=ProposalKind.CONFIRM_EDGE, ai_message="よろしいですか？", candidate_edge=edge
    )
    client = _ScriptedAnthropicClient(
        {"回答を解釈": {"decision": "confirm", "sign_override": None, "lag_value": None, "lag_unit": None, "note": None}}
    )

    updated = apply_user_response(dag, proposal, "YES", client=client)

    updated_edge = next(e for e in updated.edges if e.id == "e1")
    assert updated_edge.status == EdgeStatus.USER_CONFIRMED
    assert updated.tuning_state.completed_rounds == 1
    assert updated.tuning_state.status == TuningStatus.IN_PROGRESS
    assert len(updated.tuning_state.rounds) == 1


def test_apply_user_response_modify_adds_lag_and_new_edge_for_connect_node():
    truck = Node(
        id="truck_utilization_rate",
        label="トラック稼働率",
        category=NodeCategory.KPI_NONFINANCIAL,
        source=NodeSource.USER_ADDED,
    )
    dag = _base_dag(edges=[], nodes_extra=[truck])
    from app.tuning.models import TuningProposal

    candidate_edge = Edge(
        id="e_proposal_1",
        source_node_id="truck_utilization_rate",
        target_node_id="operating_income",
        sign=EdgeSign.NEGATIVE,
        status=EdgeStatus.AI_PROPOSED,
        rationale="トラック稼働率改善は営業利益を押し上げる",
    )
    proposal = TuningProposal(
        round_number=1,
        kind=ProposalKind.CONNECT_NODE,
        ai_message="この因果関係を追加してよろしいですか？",
        candidate_edge=candidate_edge,
    )
    client = _ScriptedAnthropicClient(
        {
            "回答を解釈": {
                "decision": "modify",
                "sign_override": None,
                "lag_value": 3,
                "lag_unit": "month",
                "note": "3ヶ月のタイムラグ",
            }
        }
    )

    updated = apply_user_response(
        dag, proposal, "YES。ただし3カ月後に効果が出るのでタイムラグを設定してほしい", client=client
    )

    assert len(updated.edges) == 1
    new_edge = updated.edges[0]
    assert new_edge.status == EdgeStatus.USER_MODIFIED
    assert new_edge.lag is not None
    assert new_edge.lag.value == 3
    assert new_edge.lag.unit == "month"


def test_apply_user_response_reject_marks_edge_rejected():
    edge = Edge(
        id="e1",
        source_node_id="revenue",
        target_node_id="operating_income",
        sign=EdgeSign.POSITIVE,
        status=EdgeStatus.AI_PROPOSED,
    )
    dag = _base_dag(edges=[edge])
    from app.tuning.models import TuningProposal

    proposal = TuningProposal(
        round_number=1, kind=ProposalKind.CONFIRM_EDGE, ai_message="よろしいですか？", candidate_edge=edge
    )
    client = _ScriptedAnthropicClient(
        {"回答を解釈": {"decision": "reject", "sign_override": None, "lag_value": None, "lag_unit": None, "note": None}}
    )

    updated = apply_user_response(dag, proposal, "NO、この因果関係は違うと思います", client=client)

    updated_edge = next(e for e in updated.edges if e.id == "e1")
    assert updated_edge.status == EdgeStatus.REJECTED


def test_fifth_round_locks_tuning_state():
    edge = Edge(
        id="e1",
        source_node_id="revenue",
        target_node_id="operating_income",
        sign=EdgeSign.POSITIVE,
        status=EdgeStatus.AI_PROPOSED,
    )
    dag = _base_dag(edges=[edge])
    existing_rounds = [
        TuningRound(round_number=i, ai_message="m", user_response="r") for i in range(1, 5)
    ]
    dag = dag.model_copy(
        update={
            "tuning_state": dag.tuning_state.model_copy(
                update={"rounds": existing_rounds, "completed_rounds": 4, "status": TuningStatus.IN_PROGRESS}
            )
        }
    )
    from app.tuning.models import TuningProposal

    proposal = TuningProposal(
        round_number=5, kind=ProposalKind.CONFIRM_EDGE, ai_message="よろしいですか？", candidate_edge=edge
    )
    client = _ScriptedAnthropicClient(
        {"回答を解釈": {"decision": "confirm", "sign_override": None, "lag_value": None, "lag_unit": None, "note": None}}
    )

    updated = apply_user_response(dag, proposal, "YES", client=client)

    assert updated.tuning_state.completed_rounds == 5
    assert updated.tuning_state.status == TuningStatus.LOCKED
    assert len(updated.tuning_state.rounds) == 5

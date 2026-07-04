import pytest

from app.ingestion.models import IRDataPoint, IRDataPointKind, IRDataSource
from app.merge.goal import set_goal
from app.merge.ir_merge import merge_ir_data_points
from app.merge.node_ops import add_edge, add_node, unconnected_node_ids
from app.models.dag import (
    Edge,
    EdgeSign,
    EdgeStatus,
    FinancialCausalDAG,
    Node,
    NodeCategory,
    NodeSource,
)


def _base_dag() -> FinancialCausalDAG:
    revenue = Node(
        id="revenue", label="売上高", category=NodeCategory.PL, source=NodeSource.TEMPLATE
    )
    operating_income = Node(
        id="operating_income",
        label="営業利益",
        category=NodeCategory.PL,
        source=NodeSource.TEMPLATE,
    )
    edge = Edge(
        id="e1",
        source_node_id="revenue",
        target_node_id="operating_income",
        sign=EdgeSign.POSITIVE,
        status=EdgeStatus.USER_CONFIRMED,
    )
    return FinancialCausalDAG(
        id="dag_test",
        name="テストDAG",
        nodes=[revenue, operating_income],
        edges=[edge],
    )


def test_set_goal_updates_goal_field():
    dag = _base_dag()
    updated = set_goal(dag, "在庫削減による営業CSの改善")
    assert updated.goal == "在庫削減による営業CSの改善"
    assert dag.goal is None  # 元のDAGは不変


def test_add_node_success():
    dag = _base_dag()
    new_node = Node(
        id="truck_utilization_rate",
        label="トラック稼働率",
        category=NodeCategory.KPI_NONFINANCIAL,
        source=NodeSource.USER_ADDED,
    )
    updated = add_node(dag, new_node)
    assert len(updated.nodes) == 3
    assert len(dag.nodes) == 2  # 元のDAGは不変


def test_add_node_duplicate_id_raises():
    dag = _base_dag()
    duplicate = Node(
        id="revenue", label="売上高2", category=NodeCategory.PL, source=NodeSource.USER_ADDED
    )
    with pytest.raises(ValueError):
        add_node(dag, duplicate)


def test_add_edge_success():
    dag = _base_dag()
    new_node = Node(
        id="logistics_cost",
        label="配送費",
        category=NodeCategory.PL,
        source=NodeSource.IR_DATA,
    )
    dag = add_node(dag, new_node)
    edge = Edge(
        id="e2",
        source_node_id="logistics_cost",
        target_node_id="operating_income",
        sign=EdgeSign.NEGATIVE,
        status=EdgeStatus.USER_CONFIRMED,
    )
    updated = add_edge(dag, edge)
    assert len(updated.edges) == 2


def test_add_edge_missing_node_raises():
    dag = _base_dag()
    edge = Edge(
        id="e2",
        source_node_id="nonexistent",
        target_node_id="operating_income",
        sign=EdgeSign.NEGATIVE,
        status=EdgeStatus.USER_CONFIRMED,
    )
    with pytest.raises(ValueError):
        add_edge(dag, edge)


def test_unconnected_node_ids():
    dag = _base_dag()
    isolated = Node(
        id="truck_utilization_rate",
        label="トラック稼働率",
        category=NodeCategory.KPI_NONFINANCIAL,
        source=NodeSource.USER_ADDED,
    )
    dag = add_node(dag, isolated)
    assert unconnected_node_ids(dag) == ["truck_utilization_rate"]


def test_merge_ir_data_points_updates_matching_node_source():
    dag = _base_dag()
    data_points = [
        IRDataPoint(
            label="売上高",
            kind=IRDataPointKind.FINANCIAL,
            value=125000,
            unit="百万円",
            source=IRDataSource(document_name="ir.pdf"),
        )
    ]
    updated = merge_ir_data_points(dag, data_points, source=NodeSource.IR_DATA)

    revenue_node = next(n for n in updated.nodes if n.id == "revenue")
    assert revenue_node.source == NodeSource.IR_DATA
    assert len(updated.nodes) == 2  # 新規ノードは追加されない


def test_merge_ir_data_points_adds_unconnected_node_for_unmatched_kpi():
    dag = _base_dag()
    data_points = [
        IRDataPoint(
            label="トラック稼働率",
            kind=IRDataPointKind.NONFINANCIAL,
            value=72.3,
            unit="%",
            source=IRDataSource(document_name="ir.pdf"),
        )
    ]
    updated = merge_ir_data_points(dag, data_points, source=NodeSource.IR_DATA)

    assert len(updated.nodes) == 3
    new_node = next(n for n in updated.nodes if n.label == "トラック稼働率")
    assert new_node.category == NodeCategory.KPI_NONFINANCIAL
    assert new_node.source == NodeSource.IR_DATA
    assert new_node.id in unconnected_node_ids(updated)

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


def test_merge_ir_data_points_sets_values_by_period_for_new_node():
    dag = _base_dag()
    data_points = [
        IRDataPoint(
            label="経常利益",
            kind=IRDataPointKind.FINANCIAL,
            value=227485.0,
            unit="百万円",
            period="2026年3月期",
            source=IRDataSource(document_name="yuho.pdf"),
        )
    ]
    updated = merge_ir_data_points(dag, data_points, source=NodeSource.IR_DATA)

    new_node = next(n for n in updated.nodes if n.label == "経常利益")
    assert new_node.values_by_period == {"2026年3月期": 227485.0}


def test_merge_ir_data_points_accumulates_multiple_periods_into_single_node():
    """EDINETの有価証券報告書は同一labelについて期ごとに別のdata_pointを
    返す（実際に5期分の経常利益を確認済み）。これらは新規ノードを複数
    作らず、1つのノードのvalues_by_periodに集約されるべき。"""
    dag = _base_dag()
    data_points = [
        IRDataPoint(
            label="経常利益",
            kind=IRDataPointKind.FINANCIAL,
            value=value,
            unit="百万円",
            period=period,
            source=IRDataSource(document_name="yuho.pdf", excerpt="経常利益 213,395 231,327 ..."),
        )
        for value, period in [
            (213395.0, "2021年度(2022年3月期)"),
            (231327.0, "2022年度(2023年3月期)"),
            (181755.0, "2023年度(2024年3月期)"),
            (196738.0, "2024年度(2025年3月期)"),
            (227485.0, "2025年度(2026年3月期)"),
        ]
    ]

    updated = merge_ir_data_points(dag, data_points, source=NodeSource.IR_DATA)

    matching_nodes = [n for n in updated.nodes if n.label == "経常利益"]
    assert len(matching_nodes) == 1
    assert matching_nodes[0].values_by_period == {
        "2022年3月期": 213395.0,
        "2023年3月期": 231327.0,
        "2024年3月期": 181755.0,
        "2025年3月期": 196738.0,
        "2026年3月期": 227485.0,
    }


def test_merge_ir_data_points_updates_existing_values_by_period_without_dropping_others():
    dag = _base_dag()
    dag = dag.model_copy(
        update={
            "nodes": [
                n if n.id != "revenue" else n.model_copy(update={"values_by_period": {"2025年3月期": 797129.0}})
                for n in dag.nodes
            ],
            "available_periods": ["2025年3月期"],
        }
    )
    data_points = [
        IRDataPoint(
            label="売上高",
            kind=IRDataPointKind.FINANCIAL,
            value=857831.0,
            unit="百万円",
            period="2026年3月期",
            source=IRDataSource(document_name="yuho.pdf"),
        )
    ]

    updated = merge_ir_data_points(dag, data_points, source=NodeSource.IR_DATA)

    revenue_node = next(n for n in updated.nodes if n.id == "revenue")
    assert revenue_node.values_by_period == {
        "2025年3月期": 797129.0,
        "2026年3月期": 857831.0,
    }
    assert updated.available_periods == ["2025年3月期", "2026年3月期"]


def test_merge_ir_data_points_normalizes_edinet_style_period():
    dag = _base_dag()
    data_points = [
        IRDataPoint(
            label="経常利益",
            kind=IRDataPointKind.FINANCIAL,
            value=227485.0,
            unit="百万円",
            period="2025年度(2026年3月期)",
            source=IRDataSource(document_name="yuho.pdf"),
        )
    ]

    updated = merge_ir_data_points(dag, data_points, source=NodeSource.IR_DATA)

    new_node = next(n for n in updated.nodes if n.label == "経常利益")
    assert new_node.values_by_period == {"2026年3月期": 227485.0}


def test_merge_ir_data_points_does_not_pollute_available_periods_with_non_fiscal_labels():
    """経営方針・非財務目標等、periodが会計期間の形式でないdata_pointは
    ノード自身のvalues_by_periodには残るが、全体のavailable_periods
    ドロップダウンには追加されない。"""
    dag = _base_dag()
    data_points = [
        IRDataPoint(
            label="連結配当性向",
            kind=IRDataPointKind.FINANCIAL,
            value=60.0,
            unit="%",
            period="方針",
            source=IRDataSource(document_name="yuho.pdf"),
        ),
        IRDataPoint(
            label="女性幹部社員比率",
            kind=IRDataPointKind.NONFINANCIAL,
            value=2.8,
            unit="%",
            period="2026年3月末",
            source=IRDataSource(document_name="yuho.pdf"),
        ),
    ]

    updated = merge_ir_data_points(dag, data_points, source=NodeSource.IR_DATA)

    haitou = next(n for n in updated.nodes if n.label == "連結配当性向")
    assert haitou.values_by_period == {"方針": 60.0}
    joseikanbu = next(n for n in updated.nodes if n.label == "女性幹部社員比率")
    assert joseikanbu.values_by_period == {"2026年3月末": 2.8}
    assert updated.available_periods == []


def test_merge_ir_data_points_with_none_value_does_not_crash_or_set_values():
    dag = _base_dag()
    data_points = [
        IRDataPoint(
            label="経常利益",
            kind=IRDataPointKind.FINANCIAL,
            value=None,
            period="2026年3月期",
            source=IRDataSource(document_name="yuho.pdf"),
        )
    ]

    updated = merge_ir_data_points(dag, data_points, source=NodeSource.IR_DATA)

    new_node = next(n for n in updated.nodes if n.label == "経常利益")
    assert new_node.values_by_period is None
    assert updated.available_periods == []

from app.causal.effect_estimation import (
    compute_edge_effects,
    compute_whatif,
    estimate_causal_effect,
)
from app.causal.graph_builder import build_confirmed_graph
from app.causal.sample_data import (
    build_sample_manufacturing_dag,
    generate_synthetic_dataset,
    generate_synthetic_dataset_for_dag,
)
from app.models.dag import EdgeStatus


def test_build_confirmed_graph_includes_all_nodes_and_confirmed_edges_only():
    dag = build_sample_manufacturing_dag()
    graph = build_confirmed_graph(dag)

    assert set(graph.nodes) == {n.id for n in dag.nodes}
    assert graph.number_of_edges() == len(
        [e for e in dag.edges if e.status == EdgeStatus.USER_CONFIRMED]
    )
    assert ("plant_utilization_rate", "cogs") in graph.edges


def test_estimate_causal_effect_recovers_expected_sign_for_direct_chain():
    dag = build_sample_manufacturing_dag()
    data = generate_synthetic_dataset(n=500, seed=0)

    # plant_utilization_rate -(-4)-> cogs -(-0.4)-> operating_income
    # 合成データの理論上の総効果 = (-4) * (-0.4) = +1.6
    result = estimate_causal_effect(
        dag, data, treatment_node_id="plant_utilization_rate", outcome_node_id="operating_income"
    )

    assert result.estimated_effect > 0
    assert 1.0 < result.estimated_effect < 2.2


def test_estimate_causal_effect_recovers_expected_sign_for_mediated_chain():
    dag = build_sample_manufacturing_dag()
    data = generate_synthetic_dataset(n=500, seed=1)

    # truck_utilization_rate -(-0.6)-> logistics_cost -(-0.8)-> operating_income
    # 合成データの理論上の総効果 = (-0.6) * (-0.8) = +0.48
    result = estimate_causal_effect(
        dag, data, treatment_node_id="truck_utilization_rate", outcome_node_id="operating_income"
    )

    assert result.estimated_effect > 0
    assert 0.2 < result.estimated_effect < 0.8


def test_estimate_causal_effect_raises_for_unknown_node():
    dag = build_sample_manufacturing_dag()
    data = generate_synthetic_dataset(n=50, seed=0)

    import pytest

    with pytest.raises(ValueError):
        estimate_causal_effect(dag, data, treatment_node_id="nonexistent", outcome_node_id="operating_income")


def test_estimate_causal_effect_raises_clear_error_for_disconnected_nodes():
    """テンプレート適用直後などエッジが全てai_proposedで確定エッジが無い場合、
    DoWhy内部の例外ではなく分かりやすいValueErrorになることを確認する。"""
    from app.models.dag import Edge, EdgeSign, EdgeStatus, FinancialCausalDAG, Node, NodeCategory, NodeSource

    dag = FinancialCausalDAG(
        id="dag_disconnected",
        name="disconnected",
        nodes=[
            Node(id="a", label="A", category=NodeCategory.KPI_FINANCIAL, source=NodeSource.TEMPLATE),
            Node(id="b", label="B", category=NodeCategory.KPI_FINANCIAL, source=NodeSource.TEMPLATE),
        ],
        edges=[
            Edge(
                id="e1", source_node_id="a", target_node_id="b",
                sign=EdgeSign.POSITIVE, status=EdgeStatus.AI_PROPOSED,
            )
        ],
    )
    data = generate_synthetic_dataset_for_dag(dag, n=50, seed=0)

    import pytest

    with pytest.raises(ValueError, match="つながっていません"):
        estimate_causal_effect(dag, data, treatment_node_id="a", outcome_node_id="b")


def test_compute_edge_effects_covers_every_confirmed_edge():
    dag = build_sample_manufacturing_dag()
    data = generate_synthetic_dataset(n=500, seed=0)
    confirmed_edge_ids = {e.id for e in dag.edges if e.status == EdgeStatus.USER_CONFIRMED}

    effects = compute_edge_effects(dag, data)

    assert set(effects.keys()) == confirmed_edge_ids
    # plant_utilization_rate -> cogs は理論上 -4 の直接効果
    assert effects["e3"] < 0
    # operating_income -> operating_cf は理論上 +0.9 の直接効果
    assert effects["e6"] > 0


def test_compute_whatif_projects_downstream_nodes():
    dag = build_sample_manufacturing_dag()
    data = generate_synthetic_dataset(n=500, seed=0)

    projections = compute_whatif(dag, data, source_node_id="plant_utilization_rate", delta_percent=10)

    node_ids = {p.node_id for p in projections}
    # plant_utilization_rate -> cogs -> operating_income -> operating_cf
    assert node_ids == {"cogs", "operating_income", "operating_cf"}

    by_node = {p.node_id: p for p in projections}
    # 稼働率が上がる(delta_percent>0)と原価は下がる(係数が負)
    assert by_node["cogs"].delta_absolute < 0
    assert by_node["cogs"].projected == by_node["cogs"].baseline + by_node["cogs"].delta_absolute
    # 稼働率上昇→原価低下→営業利益は増加
    assert by_node["operating_income"].delta_absolute > 0


def test_compute_whatif_raises_for_unknown_node():
    dag = build_sample_manufacturing_dag()
    data = generate_synthetic_dataset(n=50, seed=0)

    import pytest

    with pytest.raises(ValueError):
        compute_whatif(dag, data, source_node_id="nonexistent", delta_percent=10)


def test_generate_synthetic_dataset_for_dag_covers_every_node():
    dag = build_sample_manufacturing_dag()

    data = generate_synthetic_dataset_for_dag(dag, n=200, seed=0)

    assert set(data.columns) == {n.id for n in dag.nodes}
    assert len(data) == 200


def test_generate_synthetic_dataset_for_dag_recovers_edge_sign():
    dag = build_sample_manufacturing_dag()
    data = generate_synthetic_dataset_for_dag(dag, n=800, seed=0)

    # plant_utilization_rate -> cogs は負の符号
    result = estimate_causal_effect(
        dag, data, treatment_node_id="plant_utilization_rate", outcome_node_id="cogs"
    )
    assert result.estimated_effect < 0


def test_generate_synthetic_dataset_for_dag_works_with_arbitrary_dag():
    """製造業サンプル以外の(9ノードに決め打ちでない)DAGでも動くことを確認する。"""
    from app.models.dag import Edge, EdgeSign, FinancialCausalDAG, Node, NodeCategory, NodeSource

    dag = FinancialCausalDAG(
        id="dag_other",
        name="other",
        nodes=[
            Node(id="mrr", label="MRR", category=NodeCategory.KPI_FINANCIAL, source=NodeSource.TEMPLATE),
            Node(id="churn", label="解約率", category=NodeCategory.KPI_NONFINANCIAL, source=NodeSource.TEMPLATE),
            Node(id="isolated", label="孤立ノード", category=NodeCategory.KPI_FINANCIAL, source=NodeSource.TEMPLATE),
        ],
        edges=[
            Edge(
                id="e1",
                source_node_id="churn",
                target_node_id="mrr",
                sign=EdgeSign.NEGATIVE,
                status=EdgeStatus.USER_CONFIRMED,
            )
        ],
    )

    data = generate_synthetic_dataset_for_dag(dag, n=100, seed=0)

    assert set(data.columns) == {"mrr", "churn", "isolated"}

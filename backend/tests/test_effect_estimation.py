from app.causal.effect_estimation import estimate_causal_effect
from app.causal.graph_builder import build_confirmed_graph
from app.causal.sample_data import build_sample_manufacturing_dag, generate_synthetic_dataset
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

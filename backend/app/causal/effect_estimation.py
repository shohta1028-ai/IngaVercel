"""Phase 6: 確定した因果DAG構造と実数値データから、DoWhyを用いて因果効果を推定する。"""

from __future__ import annotations

import pandas as pd
from dowhy import CausalModel
from pydantic import BaseModel

from app.causal._dowhy_compat import apply_dowhy_pandas_compat_patch
from app.causal.graph_builder import build_confirmed_graph, to_gml
from app.models.dag import FinancialCausalDAG

apply_dowhy_pandas_compat_patch()


class CausalEffectResult(BaseModel):
    treatment_node_id: str
    outcome_node_id: str
    method_name: str
    backdoor_variables: list[str]
    estimated_effect: float


def estimate_causal_effect(
    dag: FinancialCausalDAG,
    data: pd.DataFrame,
    treatment_node_id: str,
    outcome_node_id: str,
    method_name: str = "backdoor.linear_regression",
) -> CausalEffectResult:
    """DAGの確定済みエッジ構造と実測データから、treatmentがoutcomeに与える
    因果効果（平均処置効果）を推定する。

    dataの列名はdagのノードidと一致している必要がある。
    """
    graph = build_confirmed_graph(dag)
    if treatment_node_id not in graph.nodes:
        raise ValueError(f"存在しないノードIDです: {treatment_node_id}")
    if outcome_node_id not in graph.nodes:
        raise ValueError(f"存在しないノードIDです: {outcome_node_id}")

    model = CausalModel(
        data=data,
        treatment=treatment_node_id,
        outcome=outcome_node_id,
        graph=to_gml(graph),
    )
    identified_estimand = model.identify_effect(proceed_when_unidentifiable=True)
    estimate = model.estimate_effect(identified_estimand, method_name=method_name)

    return CausalEffectResult(
        treatment_node_id=treatment_node_id,
        outcome_node_id=outcome_node_id,
        method_name=method_name,
        backdoor_variables=identified_estimand.get_backdoor_variables(),
        estimated_effect=float(estimate.value),
    )

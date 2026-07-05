"""Phase 6: 確定した因果DAG構造と実数値データから、DoWhyを用いて因果効果を推定する。"""

from __future__ import annotations

import networkx as nx
import pandas as pd
from dowhy import CausalModel
from pydantic import BaseModel

from app.causal._dowhy_compat import apply_dowhy_pandas_compat_patch
from app.causal.graph_builder import CONFIRMED_STATUSES, build_confirmed_graph, to_gml
from app.models.dag import FinancialCausalDAG

apply_dowhy_pandas_compat_patch()


class CausalEffectResult(BaseModel):
    treatment_node_id: str
    outcome_node_id: str
    method_name: str
    backdoor_variables: list[str]
    estimated_effect: float


class WhatIfProjection(BaseModel):
    node_id: str
    baseline: float
    projected: float
    delta_absolute: float
    delta_percent: float


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
    if treatment_node_id not in data.columns:
        raise ValueError(f"データに数値列がないノードです: {treatment_node_id}")
    if outcome_node_id not in data.columns:
        raise ValueError(f"データに数値列がないノードです: {outcome_node_id}")
    if not nx.has_path(graph.to_undirected(), treatment_node_id, outcome_node_id):
        raise ValueError(
            "確定済みのエッジでこの2つのノードがつながっていません。"
            "対話チューニングで因果構造を確定してから推論してください。"
        )

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


def compute_edge_effects(dag: FinancialCausalDAG, data: pd.DataFrame) -> dict[str, float]:
    """確定済み(user_confirmed/user_modified)の全エッジについて、
    そのエッジ1本の直接効果(source→target)をDoWhyで推定する。

    推論モードに入った際、ツリー上の各エッジに数値を刻印するために使う。
    データ列が無いノードを含むエッジは静かにスキップする（ユーザー起因の
    データ不足であり、UI側は該当エッジに数値を表示しないだけでよい）。
    """
    effects: dict[str, float] = {}
    for edge in dag.edges:
        if edge.status not in CONFIRMED_STATUSES:
            continue
        if edge.source_node_id not in data.columns or edge.target_node_id not in data.columns:
            continue
        try:
            result = estimate_causal_effect(
                dag, data, edge.source_node_id, edge.target_node_id
            )
        except Exception:
            continue
        effects[edge.id] = result.estimated_effect
    return effects


def compute_whatif(
    dag: FinancialCausalDAG,
    data: pd.DataFrame,
    source_node_id: str,
    delta_percent: float,
) -> list[WhatIfProjection]:
    """起点ノード(source_node_id)がdelta_percent(%)だけ変化した場合の、
    確定済みグラフ上で到達可能な下流ノードそれぞれの予測値を計算する。

    各下流ノードへの効果はestimate_causal_effect(source_node_id, node)を
    個別に呼んで求める（DoWhyのバックドア調整により、途中の経路を経由する
    総合効果として推定される）。
    """
    graph = build_confirmed_graph(dag)
    if source_node_id not in graph.nodes:
        raise ValueError(f"存在しないノードIDです: {source_node_id}")
    if source_node_id not in data.columns:
        raise ValueError(f"データに数値列がないノードです: {source_node_id}")

    source_baseline = float(data[source_node_id].mean())
    source_delta_absolute = source_baseline * (delta_percent / 100)

    projections: list[WhatIfProjection] = []
    for node_id in nx.descendants(graph, source_node_id):
        if node_id not in data.columns:
            continue
        try:
            result = estimate_causal_effect(dag, data, source_node_id, node_id)
        except Exception:
            continue

        node_baseline = float(data[node_id].mean())
        delta_absolute = result.estimated_effect * source_delta_absolute
        projected = node_baseline + delta_absolute
        delta_percent_at_node = (
            (delta_absolute / node_baseline * 100) if node_baseline != 0 else 0.0
        )

        projections.append(
            WhatIfProjection(
                node_id=node_id,
                baseline=node_baseline,
                projected=projected,
                delta_absolute=delta_absolute,
                delta_percent=delta_percent_at_node,
            )
        )

    return projections

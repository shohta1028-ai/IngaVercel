"""Phase 6の動作確認・デモ用: サンプル製造業DAGと、それに整合する合成時系列データ。

実際の運用では、確定したDAG構造と紐づく実測の財務・KPI時系列データ
（Phase3のIRデータ取り込み結果を期間ごとに集計したもの等）を用いる。
ここでは因果推論パイプライン自体の動作を確認するため、DAGのエッジが
示す符号と整合するように意図的に生成した合成データを提供する。
"""

from __future__ import annotations

import networkx as nx
import numpy as np
import pandas as pd

from app.causal.graph_builder import build_confirmed_graph
from app.models.dag import (
    Edge,
    EdgeSign,
    EdgeStatus,
    FinancialCausalDAG,
    Node,
    NodeCategory,
    NodeSource,
)


def build_sample_manufacturing_dag() -> FinancialCausalDAG:
    """フロントエンドのsample_dag.jsonと同じ構造を、確定済みエッジのみで再現する。"""
    nodes = [
        Node(id="revenue", label="売上高", category=NodeCategory.PL, source=NodeSource.TEMPLATE),
        Node(id="cogs", label="売上原価", category=NodeCategory.PL, source=NodeSource.TEMPLATE),
        Node(
            id="logistics_cost", label="配送費", category=NodeCategory.PL, source=NodeSource.IR_DATA
        ),
        Node(
            id="operating_income",
            label="営業利益",
            category=NodeCategory.PL,
            source=NodeSource.TEMPLATE,
        ),
        Node(id="inventory", label="棚卸資産", category=NodeCategory.BS, source=NodeSource.TEMPLATE),
        Node(
            id="operating_cf",
            label="営業キャッシュフロー",
            category=NodeCategory.CS,
            source=NodeSource.TEMPLATE,
        ),
        Node(
            id="plant_utilization_rate",
            label="工場稼働率",
            category=NodeCategory.KPI_NONFINANCIAL,
            source=NodeSource.TEMPLATE,
        ),
        Node(
            id="defect_rate",
            label="不良率",
            category=NodeCategory.KPI_NONFINANCIAL,
            source=NodeSource.TEMPLATE,
        ),
        Node(
            id="truck_utilization_rate",
            label="トラック稼働率",
            category=NodeCategory.KPI_NONFINANCIAL,
            source=NodeSource.USER_ADDED,
        ),
    ]

    def edge(id_, src, tgt, sign):
        return Edge(
            id=id_, source_node_id=src, target_node_id=tgt, sign=sign, status=EdgeStatus.USER_CONFIRMED
        )

    edges = [
        edge("e1", "revenue", "operating_income", EdgeSign.POSITIVE),
        edge("e2", "cogs", "operating_income", EdgeSign.NEGATIVE),
        edge("e3", "plant_utilization_rate", "cogs", EdgeSign.NEGATIVE),
        edge("e4", "defect_rate", "cogs", EdgeSign.POSITIVE),
        edge("e5", "inventory", "operating_cf", EdgeSign.NEGATIVE),
        edge("e6", "operating_income", "operating_cf", EdgeSign.POSITIVE),
        edge("e7", "logistics_cost", "operating_income", EdgeSign.NEGATIVE),
        edge("e8", "truck_utilization_rate", "logistics_cost", EdgeSign.NEGATIVE),
    ]

    return FinancialCausalDAG(
        id="dag_sample_manufacturing",
        name="製造業_サンプルDAG",
        industry="製造業",
        goal="物流効率化による営業利益改善",
        nodes=nodes,
        edges=edges,
    )


def generate_synthetic_dataset(n: int = 300, seed: int = 0) -> pd.DataFrame:
    """DAGのエッジが示す符号と整合する合成時系列データをn期分生成する。"""
    rng = np.random.default_rng(seed)

    plant_utilization_rate = rng.normal(80, 5, n)
    defect_rate = rng.normal(3, 1, n)
    truck_utilization_rate = rng.normal(70, 8, n)
    revenue = rng.normal(1200, 50, n)
    inventory = rng.normal(300, 30, n)

    cogs = 900 - 4 * plant_utilization_rate + 15 * defect_rate + rng.normal(0, 10, n)
    logistics_cost = 100 - 0.6 * truck_utilization_rate + rng.normal(0, 5, n)
    operating_income = (
        0.5 * revenue - 0.4 * cogs - 0.8 * logistics_cost + rng.normal(0, 15, n)
    )
    operating_cf = 0.9 * operating_income - 0.3 * inventory + rng.normal(0, 10, n)

    return pd.DataFrame(
        {
            "revenue": revenue,
            "cogs": cogs,
            "logistics_cost": logistics_cost,
            "operating_income": operating_income,
            "inventory": inventory,
            "operating_cf": operating_cf,
            "plant_utilization_rate": plant_utilization_rate,
            "defect_rate": defect_rate,
            "truck_utilization_rate": truck_utilization_rate,
        }
    )


def generate_synthetic_dataset_for_dag(
    dag: FinancialCausalDAG, n: int = 300, seed: int = 0
) -> pd.DataFrame:
    """任意のDAGについて、確定済みエッジの符号と整合する合成時系列データを
    ノードごとに生成する。

    特定の9ノードに決め打ちだった generate_synthetic_dataset() と異なり、
    どのDAG（テンプレートライブラリの業界テンプレート、IR取込み後の構造、
    対話チューニングで変化した構造等）に対しても、現在のノード全件に対応する
    列を持つデータフレームを返す。これにより因果効果推定・エッジ効果一括
    推定・What-ifシミュレーターが「データ不足」で止まらないようにする。

    親ノードを持たないノードはベースライン分布のみ、親を持つノードは各親を
    z-score標準化した値をエッジの符号に応じた係数で線形結合し、ノイズを
    加えて生成する（単位・スケールの整合性よりも、符号の向きが正しく
    再現されることを優先した簡易モデル）。
    """
    rng = np.random.default_rng(seed)
    graph = build_confirmed_graph(dag)
    order = list(nx.topological_sort(graph))

    values: dict[str, np.ndarray] = {}
    for node_id in order:
        baseline = rng.normal(100, 15, n)
        parent_ids = list(graph.predecessors(node_id))
        if not parent_ids:
            values[node_id] = baseline
            continue

        total_effect = np.zeros(n)
        for parent_id in parent_ids:
            edge = next(
                e
                for e in dag.edges
                if e.source_node_id == parent_id
                and e.target_node_id == node_id
                and e.status in {EdgeStatus.USER_CONFIRMED, EdgeStatus.USER_MODIFIED}
            )
            parent_values = values[parent_id]
            std = parent_values.std()
            z = (parent_values - parent_values.mean()) / (std if std > 1e-9 else 1.0)

            magnitude = rng.uniform(8, 20)
            if edge.sign == EdgeSign.NEGATIVE:
                coef = -magnitude
            elif edge.sign == EdgeSign.POSITIVE:
                coef = magnitude
            else:  # ambiguous: 方向をランダムに決める
                coef = magnitude * rng.choice([-1, 1])
            total_effect += coef * z

        noise = rng.normal(0, 5, n)
        values[node_id] = baseline + total_effect + noise

    return pd.DataFrame(values)

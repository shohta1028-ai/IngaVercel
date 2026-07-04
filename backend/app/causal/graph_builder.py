"""Phase 6: 確定した因果DAGをDoWhyに引き渡すためのグラフ表現に変換する。

ユーザーが対話チューニングで確定させたエッジ（user_confirmed/user_modified）
のみを因果構造として採用する。ai_proposed（未確認の仮説）やrejected
（却下済み）のエッジは、実データでの効果検証には含めない。
"""

from __future__ import annotations

import networkx as nx

from app.models.dag import EdgeStatus, FinancialCausalDAG

CONFIRMED_STATUSES = {EdgeStatus.USER_CONFIRMED, EdgeStatus.USER_MODIFIED}


def build_confirmed_graph(dag: FinancialCausalDAG) -> nx.DiGraph:
    graph = nx.DiGraph()
    graph.add_nodes_from(n.id for n in dag.nodes)
    graph.add_edges_from(
        (e.source_node_id, e.target_node_id)
        for e in dag.edges
        if e.status in CONFIRMED_STATUSES
    )
    return graph


def to_gml(graph: nx.DiGraph) -> str:
    return "\n".join(nx.generate_gml(graph))

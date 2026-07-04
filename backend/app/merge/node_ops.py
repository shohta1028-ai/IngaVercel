"""Phase 4: 企業固有の非財務データをドラッグ&ドロップ等でツリーに
ノード追加・紐付け（エッジ追加）するための基本操作。

フロントエンドの操作（ノードのドロップ、ハンドル間のドラッグ接続）は
最終的にこのモジュールの add_node / add_edge を呼び出す想定。
"""

from __future__ import annotations

from datetime import datetime, timezone

from app.models.dag import Edge, FinancialCausalDAG, Node


def add_node(dag: FinancialCausalDAG, node: Node) -> FinancialCausalDAG:
    if any(n.id == node.id for n in dag.nodes):
        raise ValueError(f"ノードIDが重複しています: {node.id}")

    return dag.model_copy(
        update={
            "nodes": [*dag.nodes, node],
            "updated_at": datetime.now(timezone.utc),
        }
    )


def add_edge(dag: FinancialCausalDAG, edge: Edge) -> FinancialCausalDAG:
    node_ids = {n.id for n in dag.nodes}
    if edge.source_node_id not in node_ids:
        raise ValueError(f"存在しないノードIDです: {edge.source_node_id}")
    if edge.target_node_id not in node_ids:
        raise ValueError(f"存在しないノードIDです: {edge.target_node_id}")
    if any(e.id == edge.id for e in dag.edges):
        raise ValueError(f"エッジIDが重複しています: {edge.id}")

    return dag.model_copy(
        update={
            "edges": [*dag.edges, edge],
            "updated_at": datetime.now(timezone.utc),
        }
    )


def unconnected_node_ids(dag: FinancialCausalDAG) -> list[str]:
    """どのエッジにも接続されていないノードのIDを返す（紐付け候補の抽出用）"""
    connected = {e.source_node_id for e in dag.edges} | {e.target_node_id for e in dag.edges}
    return [n.id for n in dag.nodes if n.id not in connected]

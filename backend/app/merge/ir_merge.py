"""Phase 4: 企業ライブラリ（IRデータ・手動登録データ）を標準テンプレートに
マージする。

一致する科目/KPIが既にテンプレート内にあれば当該ノードの由来を更新し、
一致しないものは「未接続の候補ノード」として追加する。未接続ノードは
node_ops.unconnected_node_ids() で検出でき、フロントエンドのドラッグ&
ドロップUIでツリーへの紐付け（エッジ追加）を促す対象となる。
"""

from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone

from app.ingestion.models import IRDataPoint, IRDataPointKind
from app.models.dag import FinancialCausalDAG, Node, NodeCategory, NodeSource, SourceCitation


def _normalize_label(label: str) -> str:
    return re.sub(r"\s+", "", label).lower()


def _find_matching_node(data_point: IRDataPoint, nodes: list[Node]) -> Node | None:
    normalized = _normalize_label(data_point.label)
    for node in nodes:
        node_label = _normalize_label(node.label)
        if node_label == normalized or node_label in normalized or normalized in node_label:
            return node
    return None


def _category_for(kind: IRDataPointKind) -> NodeCategory:
    return (
        NodeCategory.KPI_FINANCIAL
        if kind == IRDataPointKind.FINANCIAL
        else NodeCategory.KPI_NONFINANCIAL
    )


def merge_ir_data_points(
    dag: FinancialCausalDAG,
    data_points: list[IRDataPoint],
    source: NodeSource = NodeSource.IR_DATA,
) -> FinancialCausalDAG:
    """IRデータ/手動登録データをテンプレートDAGにマージする。

    一致する既存ノードが見つかった場合はそのノードのsourceのみ更新し、
    見つからなかった場合は新規の未接続ノードとして追加する。
    """
    nodes = list(dag.nodes)

    for dp in data_points:
        matched = _find_matching_node(dp, nodes)
        if matched is not None:
            nodes = [
                n if n.id != matched.id else n.model_copy(update={"source": source})
                for n in nodes
            ]
            continue

        new_node = Node(
            id=f"{source.value}_{uuid.uuid4().hex[:8]}",
            label=dp.label,
            category=_category_for(dp.kind),
            unit=dp.unit,
            source=source,
            source_citation=SourceCitation(
                document_name=dp.source.document_name, excerpt=dp.source.excerpt
            ),
        )
        nodes.append(new_node)

    return dag.model_copy(
        update={"nodes": nodes, "updated_at": datetime.now(timezone.utc)}
    )

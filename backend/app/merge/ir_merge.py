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


_PERIOD_INNER_RE = re.compile(r"\(([^()]*年[^()]*期[^()]*)\)\s*$")


def _normalize_period(period: str | None) -> str | None:
    """EDINET等が返す"2022年度(2023年3月期)"のような表記から、シードDAGと
    同じ"2023年3月期"形式を取り出す。該当パターンが無ければ元の文字列を
    そのまま使う（ベストエフォートの正規化）。"""
    if period is None:
        return None
    period = period.strip()
    match = _PERIOD_INNER_RE.search(period)
    return match.group(1) if match else period


def _period_sort_key(period: str) -> tuple[int, str]:
    match = re.match(r"(\d{4})", period)
    return (int(match.group(1)) if match else 0, period)


_FISCAL_PERIOD_RE = re.compile(r"^\d{4}年\d{1,2}月期$")


def _is_valid_fiscal_period(period: str) -> bool:
    """"2026年3月期"のような会計期間の形式かどうかを判定する。

    IR資料からは「方針」「2030年までの目標」「2026年3月末」のような、
    会計期間とは呼べない値がperiodとして抽出されることがある
    （経営方針・非財務目標・スナップショット時点等）。これらは各ノードの
    values_by_periodには保持する（データを失わない）が、全ノード共通の
    期間切替ドロップダウン(available_periods)には追加しない。
    """
    return bool(_FISCAL_PERIOD_RE.fullmatch(period))


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

    一致する既存ノードが見つかった場合はそのノードのsource・実測値
    （values_by_period）・出典を更新し、見つからなかった場合は実測値付きの
    新規未接続ノードとして追加する。同一labelの複数期のdata_point（例:
    経常利益の5期分）は、1つのノードのvalues_by_periodに累積される。
    """
    nodes = list(dag.nodes)
    known_periods = set(dag.available_periods or [])
    new_periods: list[str] = []

    for dp in data_points:
        normalized_period = _normalize_period(dp.period)
        period_update: dict[str, float] = {}
        if dp.value is not None and normalized_period is not None:
            period_update[normalized_period] = dp.value
            if (
                _is_valid_fiscal_period(normalized_period)
                and normalized_period not in known_periods
                and normalized_period not in new_periods
            ):
                new_periods.append(normalized_period)

        citation = SourceCitation(
            document_name=dp.source.document_name, excerpt=dp.source.excerpt
        )

        matched = _find_matching_node(dp, nodes)
        if matched is not None:
            def _apply_update(n: Node, matched_id: str = matched.id) -> Node:
                if n.id != matched_id:
                    return n
                merged_values = {**(n.values_by_period or {}), **period_update}
                return n.model_copy(
                    update={
                        "source": source,
                        "values_by_period": merged_values or None,
                        "source_citation": citation,
                    }
                )

            nodes = [_apply_update(n) for n in nodes]
            continue

        new_node = Node(
            id=f"{source.value}_{uuid.uuid4().hex[:8]}",
            label=dp.label,
            category=_category_for(dp.kind),
            unit=dp.unit,
            source=source,
            values_by_period=period_update or None,
            source_citation=citation,
        )
        nodes.append(new_node)

    updates: dict = {"nodes": nodes, "updated_at": datetime.now(timezone.utc)}
    if new_periods:
        updates["available_periods"] = sorted(
            known_periods | set(new_periods), key=_period_sort_key
        )

    return dag.model_copy(update=updates)

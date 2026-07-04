"""APIサーバーの初期状態として使うシードDAG。

frontend/src/fixtures/sample_dag.json と同じ構造（AI仮説エッジや
未接続の候補ノードを含む）をPython側でも再現し、実LLM呼び出しに
よる対話チューニングのデモをフロントエンドと同じシナリオで試せる
ようにする。
"""

from __future__ import annotations

from app.models.dag import (
    Edge,
    EdgeSign,
    EdgeStatus,
    FinancialCausalDAG,
    Lag,
    LagUnit,
    Node,
    NodeCategory,
    NodeSource,
)


def build_seed_dag() -> FinancialCausalDAG:
    nodes = [
        Node(id="revenue", label="売上高", category=NodeCategory.PL, statement="売上高", unit="円", source=NodeSource.TEMPLATE),
        Node(id="cogs", label="売上原価", category=NodeCategory.PL, statement="売上原価", unit="円", source=NodeSource.TEMPLATE),
        Node(id="logistics_cost", label="配送費", category=NodeCategory.PL, statement="販管費", unit="円", source=NodeSource.IR_DATA),
        Node(id="operating_income", label="営業利益", category=NodeCategory.PL, statement="営業利益", unit="円", source=NodeSource.TEMPLATE),
        Node(id="inventory", label="棚卸資産", category=NodeCategory.BS, statement="流動資産", unit="円", source=NodeSource.TEMPLATE),
        Node(id="operating_cf", label="営業キャッシュフロー", category=NodeCategory.CS, statement="営業活動によるCF", unit="円", source=NodeSource.TEMPLATE),
        Node(id="plant_utilization_rate", label="工場稼働率", category=NodeCategory.KPI_NONFINANCIAL, unit="%", source=NodeSource.TEMPLATE),
        Node(id="defect_rate", label="不良率", category=NodeCategory.KPI_NONFINANCIAL, unit="%", source=NodeSource.TEMPLATE),
        Node(id="truck_utilization_rate", label="トラック稼働率", category=NodeCategory.KPI_NONFINANCIAL, unit="%", source=NodeSource.USER_ADDED),
        Node(
            id="inventory_turnover",
            label="在庫回転率",
            category=NodeCategory.KPI_FINANCIAL,
            unit="回/年",
            source=NodeSource.IR_DATA,
            description="Phase3のIRデータ取り込みで検出。まだツリーに未接続（分析ゴール「在庫削減」に関連する候補）",
        ),
    ]

    edges = [
        Edge(id="e1", source_node_id="revenue", target_node_id="operating_income", sign=EdgeSign.POSITIVE, status=EdgeStatus.USER_CONFIRMED),
        Edge(id="e2", source_node_id="cogs", target_node_id="operating_income", sign=EdgeSign.NEGATIVE, status=EdgeStatus.USER_CONFIRMED),
        Edge(
            id="e3",
            source_node_id="plant_utilization_rate",
            target_node_id="cogs",
            sign=EdgeSign.NEGATIVE,
            status=EdgeStatus.USER_CONFIRMED,
            rationale="稼働率上昇は固定費配賦効率を改善し単位原価を下げる",
        ),
        Edge(
            id="e4",
            source_node_id="defect_rate",
            target_node_id="cogs",
            sign=EdgeSign.POSITIVE,
            status=EdgeStatus.AI_PROPOSED,
            rationale="不良率上昇は手直し・廃棄コストを増加させる（AI仮説・要確認）",
        ),
        Edge(
            id="e5",
            source_node_id="inventory",
            target_node_id="operating_cf",
            sign=EdgeSign.NEGATIVE,
            status=EdgeStatus.AI_PROPOSED,
            rationale="棚卸資産の増加は運転資本を圧迫し営業CFを悪化させる（AI仮説・要確認）",
        ),
        Edge(id="e6", source_node_id="operating_income", target_node_id="operating_cf", sign=EdgeSign.POSITIVE, status=EdgeStatus.USER_CONFIRMED),
        Edge(
            id="e7",
            source_node_id="logistics_cost",
            target_node_id="operating_income",
            sign=EdgeSign.NEGATIVE,
            status=EdgeStatus.USER_CONFIRMED,
            rationale="IRより「物流効率化」が今年度の重点KPIとして掲げられているため因果パスを強化",
        ),
        Edge(
            id="e8",
            source_node_id="truck_utilization_rate",
            target_node_id="logistics_cost",
            sign=EdgeSign.NEGATIVE,
            status=EdgeStatus.USER_MODIFIED,
            rationale="YES。ただしトラック稼働率の影響が出るのは3カ月後なのでタイムラグを設定",
            lag=Lag(value=3, unit=LagUnit.MONTH),
            round_added=2,
        ),
    ]

    return FinancialCausalDAG(
        id="dag_sample_001",
        name="製造業_サンプルDAG",
        industry="製造業",
        company="サンプル株式会社",
        goal="物流効率化による営業利益改善",
        nodes=nodes,
        edges=edges,
    )

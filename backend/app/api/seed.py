"""APIサーバーの初期状態として使うシードDAG。

ファナック株式会社（FANUC CORPORATION, 証券コード6954）の実際の決算短信
（2025年4月23日・2026年4月24日公表分）に基づく、売上高・営業利益の実測値を
反映している。複数の独立した引用元で数値が一致することを確認済み。

売上原価・棚卸資産・工場稼働率等は、同社が定期開示していない社内指標
（あるいは公開情報からは期別の内訳を確認できなかった項目）のため、実数値を
記載せず、あくまでイラストレーション目的の推定値として扱う（Nodeの
description欄にその旨を明記し、values_by_periodは設定しない）。
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
    SourceCitation,
)

AVAILABLE_PERIODS = ["2023年3月期", "2024年3月期", "2025年3月期", "2026年3月期"]

# 出所: ファナック決算短信（2025年4月23日・2026年4月24日公表分）。
# 2025年3月期・2026年3月期は決算短信原文を複数の引用元で直接確認済み。
# 2023年3月期・2024年3月期は、翌期決算短信に記載の前期比(%)から算出。
REVENUE_BY_PERIOD = {
    "2023年3月期": 851956.0,
    "2024年3月期": 795538.0,
    "2025年3月期": 797129.0,
    "2026年3月期": 857831.0,
}
OPERATING_INCOME_BY_PERIOD = {
    "2023年3月期": 191359.0,
    "2024年3月期": 141953.0,
    "2025年3月期": 158846.0,
    "2026年3月期": 183763.0,
}

_ILLUSTRATIVE_NOTE = "イラストレーション目的の推定値（同社の実際の開示数値ではありません）"

_TANSHIN_CITATION = SourceCitation(
    document_name="ファナック株式会社 決算短信（2025年4月23日・2026年4月24日公表分）"
)


def build_seed_dag() -> FinancialCausalDAG:
    nodes = [
        Node(
            id="revenue",
            label="売上高",
            category=NodeCategory.PL,
            statement="売上高",
            unit="百万円",
            source=NodeSource.IR_DATA,
            description="ファナック決算短信の実績値（複数ソースで確認済み）。",
            values_by_period=REVENUE_BY_PERIOD,
            source_citation=_TANSHIN_CITATION,
        ),
        Node(
            id="cogs",
            label="売上原価",
            category=NodeCategory.PL,
            statement="売上原価",
            unit="百万円",
            source=NodeSource.TEMPLATE,
            description=_ILLUSTRATIVE_NOTE,
        ),
        Node(
            id="logistics_cost",
            label="配送費",
            category=NodeCategory.PL,
            statement="販管費",
            unit="百万円",
            source=NodeSource.IR_DATA,
            description=_ILLUSTRATIVE_NOTE,
        ),
        Node(
            id="operating_income",
            label="営業利益",
            category=NodeCategory.PL,
            statement="営業利益",
            unit="百万円",
            source=NodeSource.IR_DATA,
            description="ファナック決算短信の実績値（複数ソースで確認済み）。",
            values_by_period=OPERATING_INCOME_BY_PERIOD,
            source_citation=_TANSHIN_CITATION,
        ),
        Node(
            id="inventory",
            label="棚卸資産",
            category=NodeCategory.BS,
            statement="流動資産",
            unit="百万円",
            source=NodeSource.TEMPLATE,
            description=_ILLUSTRATIVE_NOTE,
        ),
        Node(
            id="operating_cf",
            label="営業キャッシュフロー",
            category=NodeCategory.CS,
            statement="営業活動によるCF",
            unit="百万円",
            source=NodeSource.TEMPLATE,
            description=_ILLUSTRATIVE_NOTE,
        ),
        Node(
            id="plant_utilization_rate",
            label="工場稼働率",
            category=NodeCategory.KPI_NONFINANCIAL,
            unit="%",
            source=NodeSource.TEMPLATE,
            description=_ILLUSTRATIVE_NOTE,
        ),
        Node(
            id="defect_rate",
            label="不良率",
            category=NodeCategory.KPI_NONFINANCIAL,
            unit="%",
            source=NodeSource.TEMPLATE,
            description=_ILLUSTRATIVE_NOTE,
        ),
        Node(
            id="truck_utilization_rate",
            label="トラック稼働率",
            category=NodeCategory.KPI_NONFINANCIAL,
            unit="%",
            source=NodeSource.USER_ADDED,
            description=_ILLUSTRATIVE_NOTE,
        ),
        Node(
            id="inventory_turnover",
            label="在庫回転率",
            category=NodeCategory.KPI_FINANCIAL,
            unit="回/年",
            source=NodeSource.IR_DATA,
            description=f"Phase3のIRデータ取り込みで検出。まだツリーに未接続（分析ゴール「在庫削減」に関連する候補）。{_ILLUSTRATIVE_NOTE}",
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
        name="ファナック_サンプルDAG",
        industry="ファクトリーオートメーション（工作機械・産業用ロボット）",
        company="ファナック株式会社",
        goal="ロボット部門の増収を起点とした収益性改善",
        nodes=nodes,
        edges=edges,
        available_periods=AVAILABLE_PERIODS,
    )

"""Phase 3: IRデータ取り込みで抽出される、企業固有の財務・経営指標の実測値。

DAGの構造（Node/Edge）とは別に、「どの指標が・いつ・どの値だったか」という
時系列の実測値を表す。Phase4のマージでNodeに対応付けられ、Phase6のDoWhy
検証で使われる。
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel


class IRDataSource(BaseModel):
    document_name: str
    excerpt: str | None = None


class IRDataPointKind(str, Enum):
    FINANCIAL = "financial"
    NONFINANCIAL = "nonfinancial"


class IRDataPoint(BaseModel):
    label: str
    kind: IRDataPointKind
    value: float | None = None
    unit: str | None = None
    period: str | None = None
    source: IRDataSource

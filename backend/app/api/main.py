"""Phase 6.5: フロントエンド↔バックエンドを結線するFastAPIサーバー。

プロトタイプのため単一ユーザー・単一DAG状態(app.api.store)を前提とする。
起動方法:
    cd backend
    uvicorn app.api.main:app --reload --port 8000
"""

from __future__ import annotations

import tempfile
import time
import uuid
from datetime import date
from pathlib import Path

import httpx
from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.api.store import load_dag, reset_dag, save_dag
from app.causal.effect_estimation import (
    CausalEffectResult,
    WhatIfProjection,
    compute_edge_effects,
    compute_whatif,
    estimate_causal_effect,
)
from app.causal.sample_data import generate_synthetic_dataset_for_dag
from app.ingestion.edinet_client import (
    EdinetDocumentSummary,
    fetch_document_pdf,
    search_documents,
)
from app.ingestion.file_loader import extract_text_from_file
from app.ingestion.ir_extractor import extract_ir_data_points
from app.ingestion.manual_loader import load_manual_data
from app.ingestion.models import IRDataPoint
from app.api.template_library import (
    TemplateLibraryEntry,
    TemplateLibraryListItem,
    get_or_generate_entry,
    list_catalog,
)
from app.llm.template_generator import generate_industry_template
from app.merge.goal import set_goal
from app.merge.ir_merge import merge_ir_data_points
from app.models.dag import (
    Edge,
    EdgeSign,
    EdgeStatus,
    FinancialCausalDAG,
    NodeSource,
    SourceCitation,
)
from app.tuning.dialogue import apply_user_response, generate_next_proposal
from app.tuning.models import TuningProposal

MANUAL_DATA_SUFFIXES = {".csv", ".xlsx", ".xlsm"}

app = FastAPI(title="IngaAnalytics API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class GoalUpdateRequest(BaseModel):
    goal: str


class EdgeCreateRequest(BaseModel):
    source_node_id: str
    target_node_id: str


class TuningRespondRequest(BaseModel):
    proposal: TuningProposal
    user_response: str


class TemplateGenerateRequest(BaseModel):
    industry: str


class IrMergeRequest(BaseModel):
    data_points: list[IRDataPoint]
    source: NodeSource = NodeSource.IR_DATA


class CausalEstimateRequest(BaseModel):
    treatment_node_id: str
    outcome_node_id: str


class WhatIfRequest(BaseModel):
    source_node_id: str
    delta_percent: float


class EdinetFetchRequest(BaseModel):
    doc_id: str
    filer_name: str | None = None
    doc_description: str | None = None


class NodeUpdateRequest(BaseModel):
    values_by_period: dict[str, float] | None = None
    unit: str | None = None
    description: str | None = None
    source_citation: SourceCitation | None = None


@app.get("/api/dag", response_model=FinancialCausalDAG)
def get_dag() -> FinancialCausalDAG:
    return load_dag()


@app.post("/api/dag/reset", response_model=FinancialCausalDAG)
def post_reset_dag() -> FinancialCausalDAG:
    return reset_dag()


@app.patch("/api/dag/goal", response_model=FinancialCausalDAG)
def patch_goal(body: GoalUpdateRequest) -> FinancialCausalDAG:
    dag = load_dag()
    updated = set_goal(dag, body.goal)
    save_dag(updated)
    return updated


@app.post("/api/dag/edges", response_model=FinancialCausalDAG)
def post_edge(body: EdgeCreateRequest) -> FinancialCausalDAG:
    dag = load_dag()
    node_ids = {n.id for n in dag.nodes}
    if body.source_node_id not in node_ids or body.target_node_id not in node_ids:
        raise HTTPException(status_code=400, detail="存在しないノードIDです")

    new_edge = Edge(
        id=f"e_user_{uuid.uuid4().hex[:8]}",
        source_node_id=body.source_node_id,
        target_node_id=body.target_node_id,
        sign=EdgeSign.AMBIGUOUS,
        status=EdgeStatus.USER_CONFIRMED,
        rationale="ユーザーがドラッグ操作で紐付け（影響の方向は要確認）",
    )
    updated = dag.model_copy(update={"edges": [*dag.edges, new_edge]})
    save_dag(updated)
    return updated


@app.patch("/api/dag/nodes/{node_id}", response_model=FinancialCausalDAG)
def patch_node(node_id: str, body: NodeUpdateRequest) -> FinancialCausalDAG:
    """ユーザーがノードの実績値・単位・説明・出典をマニュアルで編集する。

    送られたフィールドのみを更新する（未送信のフィールドは既存値を維持）。
    """
    dag = load_dag()
    if node_id not in {n.id for n in dag.nodes}:
        raise HTTPException(status_code=400, detail="存在しないノードIDです")

    # model_dump()だとネストしたSourceCitationがdictに変換されてしまい、
    # model_copyでそのままNode.source_citationへ生dictが入ってしまう
    # (Pydanticインスタンスとして検証されない)ため、set済みフィールドの
    # 値をモデルインスタンスのまま取り出す
    updates = {field: getattr(body, field) for field in body.model_fields_set}
    nodes = [
        n.model_copy(update=updates) if n.id == node_id else n for n in dag.nodes
    ]
    updated = dag.model_copy(update={"nodes": nodes})
    save_dag(updated)
    return updated


@app.post("/api/tuning/proposal", response_model=TuningProposal | None)
def post_tuning_proposal() -> TuningProposal | None:
    dag = load_dag()
    started = time.monotonic()
    try:
        proposal = generate_next_proposal(dag)
    except Exception as e:  # LLM呼び出し失敗(APIキー未設定等)を502として返しCORSヘッダーを確実に付与する
        raise HTTPException(status_code=502, detail=f"LLM呼び出しに失敗しました: {e}") from e
    print(f"[tuning] generate_next_proposal took {time.monotonic() - started:.2f}s")
    return proposal


@app.post("/api/tuning/respond", response_model=FinancialCausalDAG)
def post_tuning_respond(body: TuningRespondRequest) -> FinancialCausalDAG:
    dag = load_dag()
    started = time.monotonic()
    try:
        updated = apply_user_response(dag, body.proposal, body.user_response)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"LLM呼び出しに失敗しました: {e}") from e
    print(f"[tuning] apply_user_response took {time.monotonic() - started:.2f}s")
    save_dag(updated)
    return updated


@app.post("/api/templates/generate", response_model=FinancialCausalDAG)
def post_generate_template(body: TemplateGenerateRequest) -> FinancialCausalDAG:
    """指定業界の標準DAGテンプレートをLLMで生成し、現在のDAGを置き換える。"""
    try:
        dag = generate_industry_template(body.industry)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"LLM呼び出しに失敗しました: {e}") from e
    save_dag(dag)
    return dag


@app.get("/api/template-library", response_model=list[TemplateLibraryListItem])
def get_template_library() -> list[TemplateLibraryListItem]:
    """業界カタログの一覧。生成済み(cached=true)のものはsummaryを含む。"""
    return list_catalog()


@app.get("/api/template-library/{industry_id}", response_model=TemplateLibraryEntry)
def get_template_library_entry(industry_id: str) -> TemplateLibraryEntry:
    """カタログの1業界の詳細(DAG＋サマリー)。未生成なら初回アクセス時に
    LLMで生成しキャッシュする。
    """
    try:
        return get_or_generate_entry(industry_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"LLM呼び出しに失敗しました: {e}") from e


@app.post("/api/template-library/{industry_id}/apply", response_model=FinancialCausalDAG)
def post_apply_template_library_entry(industry_id: str) -> FinancialCausalDAG:
    """カタログのテンプレートを現在の作業DAGとして採用する。"""
    try:
        entry = get_or_generate_entry(industry_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"LLM呼び出しに失敗しました: {e}") from e
    save_dag(entry.dag)
    return entry.dag


@app.post("/api/ir/extract", response_model=list[IRDataPoint])
async def post_ir_extract(file: UploadFile = File(...)) -> list[IRDataPoint]:
    """アップロードされたIR資料(PDF/HTML/テキスト)または手動データ(CSV/Excel)から
    財務・KPIデータを抽出する（まだDAGへのマージは行わない）。
    """
    suffix = Path(file.filename or "").suffix.lower()
    content = await file.read()

    with tempfile.NamedTemporaryFile(suffix=suffix) as tmp:
        tmp.write(content)
        tmp.flush()
        tmp_path = Path(tmp.name)

        if suffix in MANUAL_DATA_SUFFIXES:
            try:
                return load_manual_data(tmp_path)
            except ValueError as e:
                raise HTTPException(status_code=400, detail=str(e)) from e

        try:
            text = extract_text_from_file(tmp_path)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e

        try:
            return extract_ir_data_points(text, document_name=file.filename or "uploaded")
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"LLM呼び出しに失敗しました: {e}") from e


@app.get("/api/edinet/search", response_model=list[EdinetDocumentSummary])
def get_edinet_search(company: str, from_date: date, to_date: date) -> list[EdinetDocumentSummary]:
    """EDINET（金融庁）に提出された書類を企業名・証券コードで検索する
    （ユーザー操作時のみ実行するオンデマンド検索。日付範囲は最大31日）。
    """
    try:
        return search_documents(company, from_date, to_date)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"EDINET APIへの接続に失敗しました: {e}") from e


@app.post("/api/edinet/fetch", response_model=list[IRDataPoint])
def post_edinet_fetch(body: EdinetFetchRequest) -> list[IRDataPoint]:
    """EDINETから指定書類のPDFを取得し、既存のIR資料抽出パイプライン
    （テキスト抽出→LLMによるKPI抽出）にそのまま流し込む。
    """
    try:
        pdf_bytes = fetch_document_pdf(body.doc_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"EDINET APIへの接続に失敗しました: {e}") from e

    document_name = f"EDINET: {body.filer_name or ''} {body.doc_description or body.doc_id}".strip()

    with tempfile.NamedTemporaryFile(suffix=".pdf") as tmp:
        tmp.write(pdf_bytes)
        tmp.flush()
        tmp_path = Path(tmp.name)

        try:
            text = extract_text_from_file(tmp_path)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e

        try:
            return extract_ir_data_points(text, document_name=document_name)
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"LLM呼び出しに失敗しました: {e}") from e


@app.post("/api/ir/merge", response_model=FinancialCausalDAG)
def post_ir_merge(body: IrMergeRequest) -> FinancialCausalDAG:
    """抽出済みのデータポイントを現在のDAGにマージする（一致する既存ノードの
    由来を更新し、一致しないものは未接続の候補ノードとして追加する）。
    """
    dag = load_dag()
    updated = merge_ir_data_points(dag, body.data_points, source=body.source)
    save_dag(updated)
    return updated


@app.get("/api/causal/available-nodes", response_model=list[str])
def get_causal_available_nodes() -> list[str]:
    """因果効果推定のデモ用合成データが値を持つノードidの一覧。

    このプロトタイプでは実測の時系列データを収集していないため、
    現在のDAG構造から生成した合成データの列（＝現在のDAGの全ノード）を
    処置・結果として選択可能にする。
    """
    dag = load_dag()
    return list(generate_synthetic_dataset_for_dag(dag).columns)


@app.post("/api/causal/estimate", response_model=CausalEffectResult)
def post_causal_estimate(body: CausalEstimateRequest) -> CausalEffectResult:
    """確定済み(user_confirmed/user_modified)のエッジ構造とサンプル合成データを
    用いてDoWhyで因果効果を推定する。

    注: このプロトタイプでは実測の時系列データをまだ収集していないため、
    現在のDAG構造から生成した合成データ(app.causal.sample_data)を用いた
    デモ推定となる。
    """
    dag = load_dag()
    data = generate_synthetic_dataset_for_dag(dag)
    try:
        return estimate_causal_effect(
            dag, data, treatment_node_id=body.treatment_node_id, outcome_node_id=body.outcome_node_id
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@app.post("/api/causal/edge-effects", response_model=dict[str, float])
def post_causal_edge_effects() -> dict[str, float]:
    """確定済みの全エッジについて、それぞれの直接効果(source→target)を
    一括推定する。推論モードへの遷移時にツリーの各エッジへ数値を
    刻印するために使う（デモ用合成データによる推定）。
    """
    dag = load_dag()
    data = generate_synthetic_dataset_for_dag(dag)
    return compute_edge_effects(dag, data)


@app.post("/api/causal/whatif", response_model=list[WhatIfProjection])
def post_causal_whatif(body: WhatIfRequest) -> list[WhatIfProjection]:
    """起点ノードがdelta_percent(%)だけ変化した場合の、下流ノードの
    予測値をWhat-ifシミュレーターのスライダー操作から呼び出す。
    """
    dag = load_dag()
    data = generate_synthetic_dataset_for_dag(dag)
    try:
        return compute_whatif(dag, data, body.source_node_id, body.delta_percent)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

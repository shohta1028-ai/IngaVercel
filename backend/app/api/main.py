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
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.api.store import load_dag, reset_dag, save_dag
from app.causal.effect_estimation import CausalEffectResult, estimate_causal_effect
from app.causal.sample_data import generate_synthetic_dataset
from app.ingestion.file_loader import extract_text_from_file
from app.ingestion.ir_extractor import extract_ir_data_points
from app.ingestion.manual_loader import load_manual_data
from app.ingestion.models import IRDataPoint
from app.llm.template_generator import generate_industry_template
from app.merge.goal import set_goal
from app.merge.ir_merge import merge_ir_data_points
from app.models.dag import Edge, EdgeSign, EdgeStatus, FinancialCausalDAG, NodeSource
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
    サンプルDAG向けに用意した合成データの列に含まれるノードのみ
    処置・結果として選択可能にする。
    """
    return list(generate_synthetic_dataset().columns)


@app.post("/api/causal/estimate", response_model=CausalEffectResult)
def post_causal_estimate(body: CausalEstimateRequest) -> CausalEffectResult:
    """確定済み(user_confirmed/user_modified)のエッジ構造とサンプル合成データを
    用いてDoWhyで因果効果を推定する。

    注: このプロトタイプでは実測の時系列データをまだ収集していないため、
    符号が既知の合成データ(app.causal.sample_data)を用いたデモ推定となる。
    """
    dag = load_dag()
    data = generate_synthetic_dataset()
    try:
        return estimate_causal_effect(
            dag, data, treatment_node_id=body.treatment_node_id, outcome_node_id=body.outcome_node_id
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

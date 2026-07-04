"""Phase 6.5: フロントエンド↔バックエンドを結線するFastAPIサーバー。

プロトタイプのため単一ユーザー・単一DAG状態(app.api.store)を前提とする。
起動方法:
    cd backend
    uvicorn app.api.main:app --reload --port 8000
"""

from __future__ import annotations

import time
import uuid

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.api.store import load_dag, reset_dag, save_dag
from app.merge.goal import set_goal
from app.models.dag import Edge, EdgeSign, EdgeStatus, FinancialCausalDAG
from app.tuning.dialogue import apply_user_response, generate_next_proposal
from app.tuning.models import TuningProposal

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

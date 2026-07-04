import type { FinancialCausalDAG, NodeSource } from "../types/dag";
import type { TuningProposal } from "./tuningTypes";
import type { IRDataPoint } from "./irTypes";
import type { CausalEffectResult, WhatIfProjection } from "./causalTypes";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

async function handleResponse<T>(response: Response, path: string): Promise<T> {
  if (!response.ok) {
    const body = await response.text();
    throw new Error(`API error ${response.status} on ${path}: ${body}`);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  return handleResponse<T>(response, path);
}

// multipart/form-dataはブラウザにboundary付きのContent-Typeを設定させる必要があるため、
// 独自ヘッダーは付与しない
async function requestForm<T>(path: string, formData: FormData): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "POST",
    body: formData,
  });
  return handleResponse<T>(response, path);
}

export function fetchDag(): Promise<FinancialCausalDAG> {
  return request<FinancialCausalDAG>("/api/dag");
}

export function resetDag(): Promise<FinancialCausalDAG> {
  return request<FinancialCausalDAG>("/api/dag/reset", { method: "POST" });
}

export function updateGoal(goal: string): Promise<FinancialCausalDAG> {
  return request<FinancialCausalDAG>("/api/dag/goal", {
    method: "PATCH",
    body: JSON.stringify({ goal }),
  });
}

export function createEdge(sourceNodeId: string, targetNodeId: string): Promise<FinancialCausalDAG> {
  return request<FinancialCausalDAG>("/api/dag/edges", {
    method: "POST",
    body: JSON.stringify({ source_node_id: sourceNodeId, target_node_id: targetNodeId }),
  });
}

export function fetchTuningProposal(): Promise<TuningProposal | null> {
  return request<TuningProposal | null>("/api/tuning/proposal", { method: "POST" });
}

export function respondToTuningProposal(
  proposal: TuningProposal,
  userResponse: string
): Promise<FinancialCausalDAG> {
  return request<FinancialCausalDAG>("/api/tuning/respond", {
    method: "POST",
    body: JSON.stringify({ proposal, user_response: userResponse }),
  });
}

export function generateTemplate(industry: string): Promise<FinancialCausalDAG> {
  return request<FinancialCausalDAG>("/api/templates/generate", {
    method: "POST",
    body: JSON.stringify({ industry }),
  });
}

export function extractIrData(file: File): Promise<IRDataPoint[]> {
  const formData = new FormData();
  formData.append("file", file);
  return requestForm<IRDataPoint[]>("/api/ir/extract", formData);
}

export function mergeIrData(
  dataPoints: IRDataPoint[],
  source: NodeSource
): Promise<FinancialCausalDAG> {
  return request<FinancialCausalDAG>("/api/ir/merge", {
    method: "POST",
    body: JSON.stringify({ data_points: dataPoints, source }),
  });
}

export function fetchCausalAvailableNodes(): Promise<string[]> {
  return request<string[]>("/api/causal/available-nodes");
}

export function estimateCausalEffect(
  treatmentNodeId: string,
  outcomeNodeId: string
): Promise<CausalEffectResult> {
  return request<CausalEffectResult>("/api/causal/estimate", {
    method: "POST",
    body: JSON.stringify({ treatment_node_id: treatmentNodeId, outcome_node_id: outcomeNodeId }),
  });
}

export function fetchEdgeEffects(): Promise<Record<string, number>> {
  return request<Record<string, number>>("/api/causal/edge-effects", { method: "POST" });
}

export function fetchWhatIf(
  sourceNodeId: string,
  deltaPercent: number
): Promise<WhatIfProjection[]> {
  return request<WhatIfProjection[]>("/api/causal/whatif", {
    method: "POST",
    body: JSON.stringify({ source_node_id: sourceNodeId, delta_percent: deltaPercent }),
  });
}

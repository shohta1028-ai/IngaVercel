import type { FinancialCausalDAG } from "../types/dag";
import type { TuningProposal } from "./tuningTypes";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!response.ok) {
    const body = await response.text();
    throw new Error(`API error ${response.status} on ${path}: ${body}`);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
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

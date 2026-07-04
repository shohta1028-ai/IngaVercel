// backend/app/tuning/models.py の TuningProposal に対応するTS型定義

import type { DagEdge } from "../types/dag";

export type ProposalKind = "confirm_edge" | "connect_node";

export interface TuningProposal {
  round_number: number;
  kind: ProposalKind;
  ai_message: string;
  candidate_edge: DagEdge;
}

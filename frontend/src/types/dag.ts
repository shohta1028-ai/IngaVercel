// backend/schemas/dag_schema.json に対応するTS型定義

export type NodeCategory =
  | "PL"
  | "BS"
  | "CS"
  | "KPI_financial"
  | "KPI_nonfinancial";

export type NodeSource = "template" | "ir_data" | "user_added";

export type EdgeSign = "positive" | "negative" | "ambiguous";

export type EdgeStatus =
  | "ai_proposed"
  | "user_confirmed"
  | "user_modified"
  | "rejected";

export type LagUnit = "day" | "week" | "month" | "quarter" | "year";

export interface DagNode {
  id: string;
  label: string;
  category: NodeCategory;
  statement?: string | null;
  unit?: string | null;
  description?: string | null;
  source: NodeSource;
}

export interface DagLag {
  value: number;
  unit: LagUnit;
}

export interface DagEdge {
  id: string;
  source_node_id: string;
  target_node_id: string;
  sign: EdgeSign;
  strength?: number | null;
  lag?: DagLag | null;
  rationale?: string | null;
  status: EdgeStatus;
  round_added?: number | null;
}

export type TuningStatus = "not_started" | "in_progress" | "locked" | "reopened";

export interface TuningRound {
  round_number: number;
  ai_message: string;
  user_response?: string | null;
  applied_changes: string[];
}

export interface TuningState {
  status: TuningStatus;
  completed_rounds: number;
  rounds: TuningRound[];
}

export interface FinancialCausalDAG {
  id: string;
  name: string;
  industry?: string | null;
  company?: string | null;
  goal?: string | null;
  nodes: DagNode[];
  edges: DagEdge[];
  tuning_state?: TuningState;
}

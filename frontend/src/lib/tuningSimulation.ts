// Phase 5: 5ラウンド対話チューニングのUIデモ用シミュレーション。
//
// 実際の説明文生成・回答解釈はLLM(Anthropic API)が担う
// (backend/app/tuning/dialogue.py、モックLLMでテスト済み)。
// バックエンドAPIサーバーがまだ立ち上がっていないこのプロトタイプ段階では、
// 同じ優先順位ロジック（①未確認のAI仮説エッジ → ②未接続の候補ノード）を
// クライアント側で再現し、対話フローのUI/UXを確認できるようにしている。

import { unconnectedNodeIds } from "./layout";
import type { DagEdge, DagNode, FinancialCausalDAG } from "../types/dag";

export type ProposalKind = "confirm_edge" | "connect_node";

export interface TuningProposal {
  roundNumber: number;
  kind: ProposalKind;
  aiMessage: string;
  candidateEdge: DagEdge;
}

function nodeLabel(nodes: DagNode[], id: string): string {
  return nodes.find((n) => n.id === id)?.label ?? id;
}

export function pickNextProposal(dag: FinancialCausalDAG): TuningProposal | null {
  const roundNumber = (dag.tuning_state?.rounds.length ?? 0) + 1;

  const pendingEdge = dag.edges.find((e) => e.status === "ai_proposed");
  if (pendingEdge) {
    const source = nodeLabel(dag.nodes, pendingEdge.source_node_id);
    const target = nodeLabel(dag.nodes, pendingEdge.target_node_id);
    const signText = pendingEdge.sign === "positive" ? "プラス" : pendingEdge.sign === "negative" ? "マイナス" : "不明確な";
    return {
      roundNumber,
      kind: "confirm_edge",
      aiMessage:
        `「${source}」から「${target}」への${signText}の影響を仮説として提示しています。` +
        `${pendingEdge.rationale ? `（理由: ${pendingEdge.rationale}）` : ""}` +
        `このままツリーに確定してよろしいですか？`,
      candidateEdge: pendingEdge,
    };
  }

  const candidateIds = unconnectedNodeIds(dag.nodes, dag.edges);
  if (candidateIds.length > 0) {
    const candidateNode = dag.nodes.find((n) => n.id === candidateIds[0])!;
    // デモ用の単純なヒューリスティック: 既に接続済みの最初のノードを紐付け先候補とする
    const connectedTarget = dag.nodes.find(
      (n) => n.id !== candidateNode.id && !candidateIds.includes(n.id)
    );
    const targetId = connectedTarget?.id ?? dag.nodes[0].id;
    const targetLabel = nodeLabel(dag.nodes, targetId);

    const proposedEdge: DagEdge = {
      id: `e_proposal_${Date.now()}`,
      source_node_id: candidateNode.id,
      target_node_id: targetId,
      sign: "negative",
      status: "ai_proposed",
      rationale: `${candidateNode.label}は分析ゴール「${dag.goal ?? "(未設定)"}」に関連するKPIのため、${targetLabel}への影響を仮説として提案`,
    };

    return {
      roundNumber,
      kind: "connect_node",
      aiMessage:
        `まだツリーに接続されていないKPI「${candidateNode.label}」を見つけました。` +
        `「${targetLabel}」への因果パスとして追加してよろしいですか？` +
        `（理由: ${proposedEdge.rationale}）`,
      candidateEdge: proposedEdge,
    };
  }

  return null;
}

export interface ParsedResponse {
  decision: "confirm" | "modify" | "reject";
  lagValue?: number;
  lagUnit?: "day" | "week" | "month" | "quarter" | "year";
  signOverride?: DagEdge["sign"];
}

const LAG_PATTERN = /(\d+)\s*(日|週|ヶ?月|四半期|年)/;
const UNIT_MAP: Record<string, ParsedResponse["lagUnit"]> = {
  日: "day",
  週: "week",
  月: "month",
  ヶ月: "month",
  四半期: "quarter",
  年: "year",
};

// デモ用の単純な自由記述解釈（実際のLLM解釈はbackend/app/tuning/dialogue.pyが担う）
export function interpretUserText(text: string): ParsedResponse {
  const isReject = /(NO|いいえ|却下|違うと思|不要)/i.test(text);
  if (isReject) {
    return { decision: "reject" };
  }

  const lagMatch = text.match(LAG_PATTERN);
  if (lagMatch) {
    const unit = UNIT_MAP[lagMatch[2]] ?? "month";
    return { decision: "modify", lagValue: Number(lagMatch[1]), lagUnit: unit };
  }

  return { decision: "confirm" };
}

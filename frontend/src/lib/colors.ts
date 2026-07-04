import type { EdgeSign, EdgeStatus, NodeCategory } from "../types/dag";

export const CATEGORY_COLOR_VAR: Record<NodeCategory, string> = {
  PL: "var(--cat-pl)",
  BS: "var(--cat-bs)",
  CS: "var(--cat-cs)",
  KPI_financial: "var(--cat-kpi-financial)",
  KPI_nonfinancial: "var(--cat-kpi-nonfinancial)",
};

export const CATEGORY_LABEL: Record<NodeCategory, string> = {
  PL: "PL（損益計算書）",
  BS: "BS（貸借対照表）",
  CS: "CS（キャッシュフロー計算書）",
  KPI_financial: "財務KPI",
  KPI_nonfinancial: "非財務KPI",
};

export function edgeColorVar(sign: EdgeSign): string {
  switch (sign) {
    case "positive":
      return "var(--status-good)";
    case "negative":
      return "var(--status-critical)";
    case "ambiguous":
      return "var(--status-ambiguous)";
  }
}

export function edgeDashArray(status: EdgeStatus): string | undefined {
  // AIの仮説（未確認）は点線、ユーザーが確認・修正済みのものは実線
  return status === "ai_proposed" ? "6 4" : undefined;
}

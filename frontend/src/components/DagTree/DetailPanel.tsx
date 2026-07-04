import { CATEGORY_LABEL } from "../../lib/colors";
import type { DagEdge, DagNode } from "../../types/dag";

const SIGN_LABEL: Record<DagEdge["sign"], string> = {
  positive: "プラスの影響",
  negative: "マイナスの影響",
  ambiguous: "影響の方向は不明確",
};

const STATUS_LABEL: Record<DagEdge["status"], string> = {
  ai_proposed: "AI仮説（未確認）",
  user_confirmed: "ユーザー確認済み",
  user_modified: "ユーザーが修正済み",
  rejected: "却下済み",
};

export function DetailPanel({
  node,
  edge,
  nodeById,
  onClose,
}: {
  node?: DagNode;
  edge?: DagEdge;
  nodeById: Record<string, DagNode>;
  onClose: () => void;
}) {
  if (!node && !edge) return null;

  return (
    <div
      style={{
        boxSizing: "border-box",
        background: "var(--surface-1)",
        borderBottom: "1px solid var(--border-hairline)",
        padding: "16px 16px",
        fontSize: 13,
        color: "var(--text-primary)",
        overflowY: "auto",
        maxHeight: "45%",
        flexShrink: 0,
      }}
    >
      <button
        onClick={onClose}
        style={{
          float: "right",
          border: "none",
          background: "none",
          color: "var(--text-muted)",
          cursor: "pointer",
          fontSize: 14,
        }}
        aria-label="閉じる"
      >
        ×
      </button>

      {node && (
        <>
          <div style={{ fontWeight: 600, marginBottom: 6 }}>{node.label}</div>
          <div style={{ color: "var(--text-secondary)" }}>
            {CATEGORY_LABEL[node.category]}
          </div>
          {node.unit && (
            <div style={{ color: "var(--text-muted)" }}>単位: {node.unit}</div>
          )}
          {node.description && <div style={{ marginTop: 8 }}>{node.description}</div>}
        </>
      )}

      {edge && (
        <>
          <div style={{ fontWeight: 600, marginBottom: 6 }}>
            {nodeById[edge.source_node_id]?.label} → {nodeById[edge.target_node_id]?.label}
          </div>
          <div style={{ color: "var(--text-secondary)" }}>{SIGN_LABEL[edge.sign]}</div>
          <div style={{ color: "var(--text-muted)" }}>{STATUS_LABEL[edge.status]}</div>
          {edge.lag && (
            <div style={{ marginTop: 6 }}>
              タイムラグ: {edge.lag.value} {edge.lag.unit}
            </div>
          )}
          {edge.rationale && (
            <div style={{ marginTop: 8, color: "var(--text-secondary)" }}>
              {edge.rationale}
            </div>
          )}
        </>
      )}
    </div>
  );
}

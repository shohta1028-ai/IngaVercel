import { CATEGORY_COLOR_VAR, CATEGORY_LABEL } from "../../lib/colors";
import type { NodeCategory } from "../../types/dag";

const CATEGORIES: NodeCategory[] = [
  "PL",
  "BS",
  "CS",
  "KPI_financial",
  "KPI_nonfinancial",
];

export function Legend() {
  return (
    <div
      style={{
        width: 200,
        flexShrink: 0,
        boxSizing: "border-box",
        background: "var(--surface-1)",
        borderRight: "1px solid var(--border-hairline)",
        padding: "16px 14px",
        fontSize: 12,
        color: "var(--text-primary)",
        lineHeight: 1.6,
        overflowY: "auto",
      }}
    >
      <div style={{ fontWeight: 600, marginBottom: 4 }}>ノード種別</div>
      {CATEGORIES.map((c) => (
        <div key={c} style={{ display: "flex", alignItems: "center", gap: 6 }}>
          <span
            style={{
              width: 10,
              height: 10,
              borderRadius: 2,
              background: CATEGORY_COLOR_VAR[c],
              display: "inline-block",
            }}
          />
          <span>{CATEGORY_LABEL[c]}</span>
        </div>
      ))}
      <div style={{ fontWeight: 600, margin: "8px 0 4px" }}>因果関係の線</div>
      <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
        <span style={{ width: 18, borderTop: "2px solid var(--status-good)" }} />
        <span>プラスの影響</span>
      </div>
      <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
        <span style={{ width: 18, borderTop: "2px solid var(--status-critical)" }} />
        <span>マイナスの影響</span>
      </div>
      <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
        <span
          style={{
            width: 18,
            borderTop: "2px dashed var(--text-muted)",
          }}
        />
        <span>AI仮説（未確認）</span>
      </div>
      <div style={{ fontWeight: 600, margin: "8px 0 4px" }}>ノードの枠線</div>
      <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
        <span
          style={{
            width: 14,
            height: 10,
            border: "1px dashed var(--text-muted)",
            borderRadius: 2,
            display: "inline-block",
          }}
        />
        <span>未接続の候補（ドラッグで紐付け）</span>
      </div>
    </div>
  );
}

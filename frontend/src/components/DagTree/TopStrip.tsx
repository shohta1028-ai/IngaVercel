import type { Mode } from "../../lib/mode";
import { MODE_DESCRIPTION, MODE_LABEL } from "../../lib/mode";

export function TopStrip({
  goal,
  onGoalChange,
  mode,
}: {
  goal: string;
  onGoalChange: (goal: string) => void;
  mode: Mode;
}) {
  const accent =
    mode === "discovery" ? "var(--mode-discovery-accent)" : "var(--mode-inference-accent)";
  const accentSoft =
    mode === "discovery" ? "var(--mode-discovery-accent-soft)" : "var(--mode-inference-accent-soft)";

  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: 10,
        padding: "10px 16px",
        borderBottom: "1px solid var(--border-hairline)",
        background: "var(--surface-1)",
      }}
    >
      <span
        title={MODE_DESCRIPTION[mode]}
        style={{
          fontSize: 11,
          fontWeight: 600,
          padding: "4px 10px",
          borderRadius: 999,
          background: accentSoft,
          color: accent,
          flexShrink: 0,
          whiteSpace: "nowrap",
        }}
      >
        {MODE_LABEL[mode]}モード
      </span>
      <label
        htmlFor="analysis-goal"
        style={{ fontSize: 12, color: "var(--text-secondary)", flexShrink: 0 }}
      >
        分析ゴール
      </label>
      <input
        id="analysis-goal"
        type="text"
        value={goal}
        onChange={(e) => onGoalChange(e.target.value)}
        placeholder="例: 在庫削減による営業CSの改善"
        style={{
          flex: 1,
          minWidth: 160,
          fontSize: 13,
          padding: "6px 10px",
          borderRadius: 6,
          border: "1px solid var(--border-hairline)",
          background: "var(--page-plane)",
          color: "var(--text-primary)",
        }}
      />
    </div>
  );
}

export function GoalBar({
  goal,
  onChange,
}: {
  goal: string;
  onChange: (goal: string) => void;
}) {
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: 8,
        padding: "10px 16px",
        borderBottom: "1px solid var(--border-hairline)",
        background: "var(--surface-1)",
      }}
    >
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
        onChange={(e) => onChange(e.target.value)}
        placeholder="例: 在庫削減による営業CSの改善"
        style={{
          flex: 1,
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

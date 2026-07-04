function ToolbarButton({
  label,
  active,
  onClick,
}: {
  label: string;
  active?: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      style={{
        fontSize: 12,
        padding: "6px 12px",
        borderRadius: 6,
        border: "1px solid var(--border-hairline)",
        background: active ? "var(--cat-pl)" : "var(--page-plane)",
        color: active ? "#ffffff" : "var(--text-primary)",
        cursor: "pointer",
        flexShrink: 0,
        whiteSpace: "nowrap",
      }}
    >
      {label}
    </button>
  );
}

export function Toolbar({
  goal,
  onGoalChange,
  isChatOpen,
  onToggleChat,
  onOpenTemplateGenerator,
  onOpenIrData,
  onOpenEffectEstimation,
}: {
  goal: string;
  onGoalChange: (goal: string) => void;
  isChatOpen: boolean;
  onToggleChat: () => void;
  onOpenTemplateGenerator: () => void;
  onOpenIrData: () => void;
  onOpenEffectEstimation: () => void;
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
        flexWrap: "wrap",
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
      <ToolbarButton label="テンプレート生成" onClick={onOpenTemplateGenerator} />
      <ToolbarButton label="IRデータ取込み" onClick={onOpenIrData} />
      <ToolbarButton label="因果効果推定" onClick={onOpenEffectEstimation} />
      <ToolbarButton label="対話チューニング" active={isChatOpen} onClick={onToggleChat} />
    </div>
  );
}

import type { ReactNode } from "react";
import type { Mode } from "../../lib/mode";

export type RightPanelTab = "detail" | "log";

export function RightPanel({
  activeTab,
  onTabChange,
  mode,
  detail,
  log,
}: {
  activeTab: RightPanelTab;
  onTabChange: (tab: RightPanelTab) => void;
  mode: Mode;
  detail: ReactNode;
  log: ReactNode;
}) {
  const accent = mode === "discovery" ? "var(--mode-discovery-accent)" : "var(--mode-inference-accent)";

  return (
    <div
      style={{
        width: 280,
        flexShrink: 0,
        display: "flex",
        flexDirection: "column",
        borderLeft: "1px solid var(--border-hairline)",
        background: "var(--surface-1)",
        minHeight: 0,
      }}
    >
      <div style={{ display: "flex", flexShrink: 0, borderBottom: "1px solid var(--border-hairline)" }}>
        <TabButton label="詳細" active={activeTab === "detail"} accent={accent} onClick={() => onTabChange("detail")} />
        <TabButton label="AIの脳内ログ" active={activeTab === "log"} accent={accent} onClick={() => onTabChange("log")} />
      </div>
      <div style={{ flex: 1, minHeight: 0, display: "flex", flexDirection: "column" }}>
        <div style={{ display: activeTab === "detail" ? "flex" : "none", flexDirection: "column", flex: 1, minHeight: 0 }}>
          {detail}
        </div>
        <div style={{ display: activeTab === "log" ? "flex" : "none", flexDirection: "column", flex: 1, minHeight: 0 }}>
          {log}
        </div>
      </div>
    </div>
  );
}

function TabButton({
  label,
  active,
  accent,
  onClick,
}: {
  label: string;
  active: boolean;
  accent: string;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      style={{
        flex: 1,
        padding: "10px 8px",
        fontSize: 12,
        fontWeight: 600,
        border: "none",
        borderBottom: active ? `2px solid ${accent}` : "2px solid transparent",
        background: "none",
        color: active ? accent : "var(--text-secondary)",
        cursor: "pointer",
      }}
    >
      {label}
    </button>
  );
}

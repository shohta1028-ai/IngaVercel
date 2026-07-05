import { Tooltip } from "../Tooltip";
import type { Mode } from "../../lib/mode";
import {
  ChatIcon,
  EffectIcon,
  IrDataIcon,
  ModeSwapIcon,
  SliderIcon,
  TemplateIcon,
} from "./icons";

function SidebarButton({
  label,
  icon,
  active,
  accent,
  onClick,
}: {
  label: string;
  icon: React.ReactNode;
  active?: boolean;
  accent?: string;
  onClick: () => void;
}) {
  return (
    <Tooltip content={label} placement="right">
      <button
        onClick={onClick}
        aria-label={label}
        style={{
          width: 40,
          height: 40,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          borderRadius: 8,
          border: "1px solid",
          borderColor: active ? accent : "transparent",
          background: active ? `color-mix(in srgb, ${accent} 14%, transparent)` : "transparent",
          color: active ? accent : "var(--text-secondary)",
          cursor: "pointer",
        }}
      >
        {icon}
      </button>
    </Tooltip>
  );
}

function SidebarDivider() {
  return <div style={{ width: 28, height: 1, background: "var(--border-hairline)", margin: "6px 0" }} />;
}

export function Sidebar({
  mode,
  isChatOpen,
  isTuningLocked,
  onToggleChat,
  onOpenTemplateLibrary,
  onOpenIrData,
  onOpenEffectEstimation,
  onOpenWhatIf,
  onToggleMode,
}: {
  mode: Mode;
  isChatOpen: boolean;
  isTuningLocked: boolean;
  onToggleChat: () => void;
  onOpenTemplateLibrary: () => void;
  onOpenIrData: () => void;
  onOpenEffectEstimation: () => void;
  onOpenWhatIf: () => void;
  onToggleMode: () => void;
}) {
  const discoveryAccent = "var(--mode-discovery-accent)";
  const inferenceAccent = "var(--mode-inference-accent)";
  const isDiscovery = mode === "discovery";

  const modeToggleLabel = isDiscovery
    ? isTuningLocked
      ? "この因果構造を確定し、推論へ進む"
      : "推論モードへ切り替える（対話チューニングが完了するとおすすめ表示されます）"
    : "探索モードに戻って構造を調整する";

  return (
    <div
      style={{
        width: 64,
        flexShrink: 0,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        gap: 6,
        padding: "14px 0",
        background: "var(--surface-1)",
        borderRight: "1px solid var(--border-hairline)",
      }}
    >
      <div
        style={{
          fontSize: 9,
          letterSpacing: "0.06em",
          color: "var(--text-muted)",
          textTransform: "uppercase",
          marginBottom: 2,
        }}
      >
        セットアップ
      </div>
      <SidebarButton
        label="業界テンプレートライブラリ（DAGを置き換える）"
        icon={<TemplateIcon />}
        accent={discoveryAccent}
        onClick={onOpenTemplateLibrary}
      />
      <SidebarButton
        label="IRデータ取込み（データを追加・拡充する）"
        icon={<IrDataIcon />}
        accent={discoveryAccent}
        onClick={onOpenIrData}
      />

      <SidebarDivider />

      <div
        style={{
          fontSize: 9,
          letterSpacing: "0.06em",
          color: "var(--text-muted)",
          textTransform: "uppercase",
          marginBottom: 2,
        }}
      >
        分析ツール
      </div>
      <SidebarButton
        label="対話チューニング"
        icon={<ChatIcon />}
        active={isChatOpen}
        accent={discoveryAccent}
        onClick={onToggleChat}
      />
      <SidebarButton
        label="因果効果を推論する"
        icon={<EffectIcon />}
        accent={inferenceAccent}
        onClick={onOpenEffectEstimation}
      />
      <SidebarButton
        label="What-ifシミュレーター"
        icon={<SliderIcon />}
        accent={inferenceAccent}
        onClick={onOpenWhatIf}
      />

      <div style={{ flex: 1 }} />

      <Tooltip content={modeToggleLabel} placement="right">
        <button
          onClick={onToggleMode}
          aria-label={modeToggleLabel}
          style={{
            width: 44,
            height: 44,
            borderRadius: 10,
            border: "none",
            background: isDiscovery && isTuningLocked ? inferenceAccent : "var(--page-plane)",
            color: isDiscovery && isTuningLocked ? "#ffffff" : "var(--text-secondary)",
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          <ModeSwapIcon />
        </button>
      </Tooltip>
    </div>
  );
}

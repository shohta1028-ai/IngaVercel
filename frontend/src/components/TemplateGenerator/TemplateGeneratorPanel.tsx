import { useState } from "react";
import { Modal } from "../Modal";
import { generateTemplate } from "../../api/client";
import type { FinancialCausalDAG } from "../../types/dag";

export function TemplateGeneratorPanel({
  onGenerated,
  onClose,
}: {
  onGenerated: (dag: FinancialCausalDAG) => void;
  onClose: () => void;
}) {
  const [industry, setIndustry] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleGenerate() {
    if (!industry.trim() || isLoading) return;
    setIsLoading(true);
    setError(null);
    try {
      const dag = await generateTemplate(industry.trim());
      onGenerated(dag);
      onClose();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <Modal title="業界標準テンプレートを生成" onClose={onClose}>
      <p style={{ fontSize: 13, color: "var(--text-secondary)", marginTop: 0 }}>
        業界名をLLMに渡し、会計論理と業界定石KPIに基づく標準的なPL/BS/CS因果構造を
        新規に生成します。<strong>現在のツリーは置き換えられます。</strong>
      </p>
      <input
        value={industry}
        onChange={(e) => setIndustry(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter") handleGenerate();
        }}
        placeholder="例: 製造業、SaaS、小売、インフラ"
        disabled={isLoading}
        style={{
          width: "100%",
          boxSizing: "border-box",
          fontSize: 13,
          padding: "8px 10px",
          borderRadius: 6,
          border: "1px solid var(--border-hairline)",
          background: "var(--page-plane)",
          color: "var(--text-primary)",
        }}
      />
      {error && (
        <div style={{ color: "var(--status-critical)", fontSize: 12, marginTop: 8 }}>
          エラー: {error}
        </div>
      )}
      <div style={{ display: "flex", justifyContent: "flex-end", marginTop: 14 }}>
        <button
          onClick={handleGenerate}
          disabled={isLoading || !industry.trim()}
          style={{
            fontSize: 13,
            padding: "8px 16px",
            borderRadius: 6,
            border: "none",
            background: "var(--cat-pl)",
            color: "#ffffff",
            cursor: isLoading ? "default" : "pointer",
            opacity: isLoading || !industry.trim() ? 0.6 : 1,
          }}
        >
          {isLoading ? "生成中…（1分程度かかる場合があります）" : "生成する"}
        </button>
      </div>
    </Modal>
  );
}

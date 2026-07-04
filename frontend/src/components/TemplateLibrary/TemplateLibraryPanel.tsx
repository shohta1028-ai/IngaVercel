import { useEffect, useState } from "react";
import { Modal } from "../Modal";
import {
  applyTemplateLibraryEntry,
  fetchTemplateLibrary,
  fetchTemplateLibraryEntry,
  generateTemplate,
} from "../../api/client";
import type { TemplateLibraryEntry, TemplateLibraryListItem } from "../../api/templateLibraryTypes";
import { CATEGORY_COLOR_VAR, CATEGORY_LABEL, edgeColorVar } from "../../lib/colors";
import type { FinancialCausalDAG, NodeCategory } from "../../types/dag";

const CATEGORY_ORDER: NodeCategory[] = ["PL", "BS", "CS", "KPI_financial", "KPI_nonfinancial"];

const SIGN_LABEL: Record<string, string> = {
  positive: "プラスの影響",
  negative: "マイナスの影響",
  ambiguous: "影響の方向は不明確",
};

const buttonStyle: React.CSSProperties = {
  fontSize: 13,
  padding: "8px 16px",
  borderRadius: 6,
  border: "none",
  background: "var(--mode-discovery-accent)",
  color: "#ffffff",
  cursor: "pointer",
};

const secondaryButtonStyle: React.CSSProperties = {
  fontSize: 13,
  padding: "8px 14px",
  borderRadius: 6,
  border: "1px solid var(--border-hairline)",
  background: "var(--page-plane)",
  color: "var(--text-primary)",
  cursor: "pointer",
};

export function TemplateLibraryPanel({
  onApplied,
  onRequestUpload,
  onClose,
}: {
  onApplied: (dag: FinancialCausalDAG) => void;
  onRequestUpload: () => void;
  onClose: () => void;
}) {
  const [items, setItems] = useState<TemplateLibraryListItem[] | null>(null);
  const [detail, setDetail] = useState<TemplateLibraryEntry | null>(null);
  const [isLoadingDetail, setIsLoadingDetail] = useState(false);
  const [isApplying, setIsApplying] = useState(false);
  const [customIndustry, setCustomIndustry] = useState("");
  const [isGeneratingCustom, setIsGeneratingCustom] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchTemplateLibrary()
      .then(setItems)
      .catch((e) => setError(e instanceof Error ? e.message : String(e)));
  }, []);

  async function openDetail(industryId: string) {
    setError(null);
    setIsLoadingDetail(true);
    try {
      const entry = await fetchTemplateLibraryEntry(industryId);
      setDetail(entry);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setIsLoadingDetail(false);
    }
  }

  async function handleApply(industryId: string) {
    setIsApplying(true);
    setError(null);
    try {
      const dag = await applyTemplateLibraryEntry(industryId);
      onApplied(dag);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
      setIsApplying(false);
    }
  }

  async function handleGenerateCustom() {
    if (!customIndustry.trim() || isGeneratingCustom) return;
    setIsGeneratingCustom(true);
    setError(null);
    try {
      const dag = await generateTemplate(customIndustry.trim());
      onApplied(dag);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
      setIsGeneratingCustom(false);
    }
  }

  if (detail) {
    const nodesByCategory = CATEGORY_ORDER.map((category) => ({
      category,
      nodes: detail.dag.nodes.filter((n) => n.category === category),
    })).filter((g) => g.nodes.length > 0);

    return (
      <Modal title={`${detail.industry_label}のテンプレート`} onClose={onClose} width={640}>
        <button onClick={() => setDetail(null)} style={{ ...secondaryButtonStyle, marginBottom: 14 }}>
          ← 一覧に戻る
        </button>

        <p style={{ fontSize: 13, color: "var(--text-secondary)" }}>{detail.summary}</p>

        <div style={{ fontSize: 12, fontWeight: 600, color: "var(--text-muted)", margin: "14px 0 6px" }}>
          会計項目（{detail.dag.nodes.length}件）
        </div>
        <div
          style={{
            maxHeight: 200,
            overflowY: "auto",
            border: "1px solid var(--border-hairline)",
            borderRadius: 6,
          }}
        >
          {nodesByCategory.map(({ category, nodes }) => (
            <div key={category} style={{ padding: "8px 12px", borderBottom: "1px solid var(--border-hairline)" }}>
              <div style={{ fontSize: 11, fontWeight: 600, color: CATEGORY_COLOR_VAR[category], marginBottom: 4 }}>
                {CATEGORY_LABEL[category]}
              </div>
              <div style={{ fontSize: 12, lineHeight: 1.8 }}>
                {nodes.map((n) => n.label).join(" / ")}
              </div>
            </div>
          ))}
        </div>

        <div style={{ fontSize: 12, fontWeight: 600, color: "var(--text-muted)", margin: "14px 0 6px" }}>
          主要な因果関係（{detail.dag.edges.length}件）
        </div>
        <div
          style={{
            maxHeight: 220,
            overflowY: "auto",
            border: "1px solid var(--border-hairline)",
            borderRadius: 6,
          }}
        >
          {detail.dag.edges.map((e, i) => {
            const source = detail.dag.nodes.find((n) => n.id === e.source_node_id);
            const target = detail.dag.nodes.find((n) => n.id === e.target_node_id);
            return (
              <div
                key={e.id}
                style={{
                  padding: "8px 12px",
                  fontSize: 12,
                  borderBottom: i < detail.dag.edges.length - 1 ? "1px solid var(--border-hairline)" : undefined,
                }}
              >
                <div>
                  <strong>{source?.label ?? e.source_node_id}</strong> →{" "}
                  <strong>{target?.label ?? e.target_node_id}</strong>{" "}
                  <span style={{ color: edgeColorVar(e.sign) }}>({SIGN_LABEL[e.sign]})</span>
                </div>
                {e.rationale && <div style={{ color: "var(--text-secondary)", marginTop: 2 }}>{e.rationale}</div>}
              </div>
            );
          })}
        </div>

        {error && (
          <div style={{ color: "var(--status-critical)", fontSize: 12, marginTop: 10 }}>エラー: {error}</div>
        )}

        <div style={{ display: "flex", justifyContent: "flex-end", marginTop: 14 }}>
          <button
            onClick={() => handleApply(detail.industry_id)}
            disabled={isApplying}
            style={{ ...buttonStyle, opacity: isApplying ? 0.6 : 1 }}
          >
            {isApplying ? "適用中…" : "このテンプレートを使って対話チューニングへ進む"}
          </button>
        </div>
      </Modal>
    );
  }

  return (
    <Modal title="業界テンプレートライブラリ" onClose={onClose} width={640}>
      <p style={{ fontSize: 13, color: "var(--text-secondary)", marginTop: 0 }}>
        業界標準のPL/BS/CF因果構造と会計的特徴をあらかじめ用意しています。自社に近い業界を選ぶと、
        そこから5ラウンドの対話チューニングで自社の運用に合わせて調整できます。
      </p>

      {error && <div style={{ color: "var(--status-critical)", fontSize: 12, marginBottom: 10 }}>エラー: {error}</div>}

      {items === null ? (
        <div style={{ fontSize: 12, color: "var(--text-muted)" }}>読み込み中…</div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 8, marginBottom: 18 }}>
          {items.map((item) => (
            <button
              key={item.industry_id}
              onClick={() => openDetail(item.industry_id)}
              disabled={isLoadingDetail}
              style={{
                textAlign: "left",
                border: "1px solid var(--border-hairline)",
                borderRadius: 8,
                padding: "10px 14px",
                background: "var(--page-plane)",
                cursor: isLoadingDetail ? "default" : "pointer",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                <span style={{ fontWeight: 600, fontSize: 13 }}>{item.industry_label}</span>
                {!item.cached && (
                  <span style={{ fontSize: 10, color: "var(--text-muted)" }}>未生成（開くと生成されます）</span>
                )}
              </div>
              {item.summary && (
                <div style={{ fontSize: 12, color: "var(--text-secondary)", marginTop: 4 }}>{item.summary}</div>
              )}
            </button>
          ))}
        </div>
      )}

      <div style={{ borderTop: "1px solid var(--border-hairline)", paddingTop: 14 }}>
        <div style={{ fontSize: 12, fontWeight: 600, marginBottom: 8 }}>求めている業種が無い場合</div>

        <div style={{ display: "flex", gap: 8, marginBottom: 10 }}>
          <input
            value={customIndustry}
            onChange={(e) => setCustomIndustry(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") handleGenerateCustom();
            }}
            placeholder="欲しい業界名を入力（例: 物流業）"
            disabled={isGeneratingCustom}
            style={{
              flex: 1,
              fontSize: 13,
              padding: "8px 10px",
              borderRadius: 6,
              border: "1px solid var(--border-hairline)",
              background: "var(--page-plane)",
              color: "var(--text-primary)",
            }}
          />
          <button
            onClick={handleGenerateCustom}
            disabled={isGeneratingCustom || !customIndustry.trim()}
            style={{ ...secondaryButtonStyle, opacity: isGeneratingCustom || !customIndustry.trim() ? 0.6 : 1 }}
          >
            {isGeneratingCustom ? "生成中…（1分程度）" : "この業界で生成する"}
          </button>
        </div>

        <button onClick={onRequestUpload} style={{ ...secondaryButtonStyle, width: "100%" }}>
          サンプルデータ（IR資料等）をアップロードして始める
        </button>
      </div>
    </Modal>
  );
}

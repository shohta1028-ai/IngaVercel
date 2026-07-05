import { useEffect, useState } from "react";
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

const sectionTitleStyle: React.CSSProperties = {
  fontSize: 11,
  fontWeight: 600,
  color: "var(--text-muted)",
  textTransform: "uppercase",
  letterSpacing: "0.04em",
  marginTop: 14,
  marginBottom: 6,
};

const inputStyle: React.CSSProperties = {
  width: "100%",
  boxSizing: "border-box",
  fontSize: 12,
  padding: "5px 8px",
  borderRadius: 5,
  border: "1px solid var(--border-hairline)",
  background: "var(--page-plane)",
  color: "var(--text-primary)",
};

type NodeUpdatePatch = Partial<
  Pick<DagNode, "values_by_period" | "unit" | "description" | "source_citation">
>;

export function DetailPanel({
  node,
  edge,
  nodeById,
  edges,
  edgeEffects,
  availablePeriods,
  onClose,
  onUpdateNode,
}: {
  node?: DagNode;
  edge?: DagEdge;
  nodeById: Record<string, DagNode>;
  edges: DagEdge[];
  edgeEffects: Record<string, number>;
  availablePeriods: string[];
  onClose: () => void;
  onUpdateNode: (nodeId: string, patch: NodeUpdatePatch) => Promise<void>;
}) {
  const [isEditing, setIsEditing] = useState(false);
  const [draftValues, setDraftValues] = useState<Record<string, string>>({});
  const [draftUnit, setDraftUnit] = useState("");
  const [draftDescription, setDraftDescription] = useState("");
  const [draftDocName, setDraftDocName] = useState("");
  const [draftUrl, setDraftUrl] = useState("");
  const [isSaving, setIsSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  // ノードの選択が切り替わったら編集状態をリセットする
  useEffect(() => {
    setIsEditing(false);
    setSaveError(null);
  }, [node?.id]);

  if (!node && !edge) {
    return (
      <div style={{ padding: 16, fontSize: 12, color: "var(--text-muted)" }}>
        ツリー上のノードやエッジをクリックすると詳細が表示されます。
      </div>
    );
  }

  function startEditing() {
    if (!node) return;
    const values: Record<string, string> = {};
    for (const period of availablePeriods) {
      const v = node.values_by_period?.[period];
      values[period] = v === undefined || v === null ? "" : String(v);
    }
    setDraftValues(values);
    setDraftUnit(node.unit ?? "");
    setDraftDescription(node.description ?? "");
    setDraftDocName(node.source_citation?.document_name ?? "");
    setDraftUrl(node.source_citation?.url ?? "");
    setSaveError(null);
    setIsEditing(true);
  }

  async function handleSave() {
    if (!node) return;
    setIsSaving(true);
    setSaveError(null);
    try {
      const values_by_period: Record<string, number> = {};
      for (const [period, raw] of Object.entries(draftValues)) {
        const trimmed = raw.trim();
        if (trimmed === "") continue;
        const parsed = Number(trimmed);
        if (!Number.isNaN(parsed)) values_by_period[period] = parsed;
      }
      const hasDocName = draftDocName.trim() !== "";
      const hasUrl = draftUrl.trim() !== "";
      await onUpdateNode(node.id, {
        values_by_period,
        unit: draftUnit.trim() === "" ? null : draftUnit.trim(),
        description: draftDescription.trim() === "" ? null : draftDescription.trim(),
        source_citation:
          hasDocName || hasUrl
            ? { document_name: hasDocName ? draftDocName.trim() : null, url: hasUrl ? draftUrl.trim() : null }
            : null,
      });
      setIsEditing(false);
    } catch (e) {
      setSaveError(e instanceof Error ? e.message : String(e));
    } finally {
      setIsSaving(false);
    }
  }

  const connectedEdges = node
    ? edges.filter((e) => e.source_node_id === node.id || e.target_node_id === node.id)
    : [];
  const outgoing = connectedEdges.filter((e) => e.source_node_id === node?.id);
  const incoming = connectedEdges.filter((e) => e.target_node_id === node?.id);

  return (
    <div
      style={{
        boxSizing: "border-box",
        background: "var(--surface-1)",
        padding: "16px 16px 20px",
        fontSize: 13,
        color: "var(--text-primary)",
        overflowY: "auto",
        flex: 1,
        minHeight: 0,
      }}
    >
      <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between" }}>
        <div style={{ fontWeight: 600 }}>
          {node
            ? node.label
            : `${nodeById[edge!.source_node_id]?.label} → ${nodeById[edge!.target_node_id]?.label}`}
        </div>
        <div style={{ display: "flex", gap: 8, flexShrink: 0 }}>
          {node && !isEditing && (
            <button onClick={startEditing} style={linkButtonStyle}>
              編集
            </button>
          )}
          <button onClick={onClose} style={{ ...linkButtonStyle, fontSize: 14 }} aria-label="閉じる">
            ×
          </button>
        </div>
      </div>

      {node && !isEditing && (
        <>
          <div style={{ color: "var(--text-secondary)", marginTop: 4 }}>
            {CATEGORY_LABEL[node.category]}
            {node.statement && ` ・ ${node.statement}`}
          </div>
          {node.unit && <div style={{ color: "var(--text-muted)" }}>単位: {node.unit}</div>}
          {node.description && <div style={{ marginTop: 8 }}>{node.description}</div>}

          {availablePeriods.length > 0 && (
            <>
              <div style={sectionTitleStyle}>期間別の値</div>
              {availablePeriods.some((p) => node.values_by_period?.[p] !== undefined) ? (
                <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
                  <tbody>
                    {availablePeriods.map((period) => (
                      <tr key={period}>
                        <td style={{ color: "var(--text-muted)", padding: "2px 0" }}>{period}</td>
                        <td style={{ textAlign: "right", fontVariantNumeric: "tabular-nums" }}>
                          {node.values_by_period?.[period] !== undefined
                            ? node.values_by_period[period].toLocaleString("ja-JP")
                            : "—"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : (
                <div style={{ color: "var(--text-muted)", fontSize: 12 }}>
                  実測値は未登録です（「編集」から入力できます）
                </div>
              )}
            </>
          )}

          {(node.source_citation?.document_name || node.source_citation?.url || node.source_citation?.excerpt) && (
            <>
              <div style={sectionTitleStyle}>出典情報</div>
              {node.source_citation.document_name && <div>{node.source_citation.document_name}</div>}
              {node.source_citation.url && (
                <a
                  href={node.source_citation.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  style={{ color: "var(--mode-discovery-accent)", wordBreak: "break-all" }}
                >
                  {node.source_citation.url}
                </a>
              )}
              {node.source_citation.excerpt && (
                <div
                  style={{
                    marginTop: 4,
                    paddingLeft: 8,
                    borderLeft: "2px solid var(--border-hairline)",
                    color: "var(--text-secondary)",
                    fontStyle: "italic",
                  }}
                >
                  {node.source_citation.excerpt}
                </div>
              )}
            </>
          )}

          {connectedEdges.length > 0 && (
            <>
              <div style={sectionTitleStyle}>因果効果</div>
              {incoming.map((e) => (
                <EdgeEffectRow
                  key={e.id}
                  label={`← ${nodeById[e.source_node_id]?.label ?? e.source_node_id}`}
                  edge={e}
                  effect={edgeEffects[e.id]}
                />
              ))}
              {outgoing.map((e) => (
                <EdgeEffectRow
                  key={e.id}
                  label={`→ ${nodeById[e.target_node_id]?.label ?? e.target_node_id}`}
                  edge={e}
                  effect={edgeEffects[e.id]}
                />
              ))}
            </>
          )}
        </>
      )}

      {node && isEditing && (
        <div style={{ marginTop: 10, display: "flex", flexDirection: "column", gap: 10 }}>
          {availablePeriods.length > 0 && (
            <div>
              <div style={sectionTitleStyle}>期間別の値</div>
              <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                {availablePeriods.map((period) => (
                  <label key={period} style={{ display: "flex", alignItems: "center", gap: 6 }}>
                    <span style={{ width: 88, flexShrink: 0, fontSize: 12, color: "var(--text-secondary)" }}>
                      {period}
                    </span>
                    <input
                      type="number"
                      value={draftValues[period] ?? ""}
                      onChange={(ev) =>
                        setDraftValues((prev) => ({ ...prev, [period]: ev.target.value }))
                      }
                      style={inputStyle}
                    />
                  </label>
                ))}
              </div>
            </div>
          )}

          <label>
            <div style={sectionTitleStyle}>単位</div>
            <input value={draftUnit} onChange={(ev) => setDraftUnit(ev.target.value)} style={inputStyle} />
          </label>

          <label>
            <div style={sectionTitleStyle}>説明</div>
            <textarea
              value={draftDescription}
              onChange={(ev) => setDraftDescription(ev.target.value)}
              rows={3}
              style={{ ...inputStyle, resize: "vertical" }}
            />
          </label>

          <div>
            <div style={sectionTitleStyle}>出典情報</div>
            <input
              placeholder="出典名（例: 決算短信）"
              value={draftDocName}
              onChange={(ev) => setDraftDocName(ev.target.value)}
              style={{ ...inputStyle, marginBottom: 6 }}
            />
            <input
              placeholder="URL（任意）"
              value={draftUrl}
              onChange={(ev) => setDraftUrl(ev.target.value)}
              style={inputStyle}
            />
          </div>

          {saveError && (
            <div style={{ color: "var(--status-critical)", fontSize: 12 }}>エラー: {saveError}</div>
          )}

          <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
            <button onClick={() => setIsEditing(false)} disabled={isSaving} style={secondaryButtonStyle}>
              キャンセル
            </button>
            <button onClick={handleSave} disabled={isSaving} style={primaryButtonStyle}>
              {isSaving ? "保存中…" : "保存"}
            </button>
          </div>
        </div>
      )}

      {edge && (
        <>
          <div style={{ color: "var(--text-secondary)", marginTop: 4 }}>{SIGN_LABEL[edge.sign]}</div>
          <div style={{ color: "var(--text-muted)" }}>{STATUS_LABEL[edge.status]}</div>
          {edge.lag && (
            <div style={{ marginTop: 6 }}>
              タイムラグ: {edge.lag.value} {edge.lag.unit}
            </div>
          )}
          {edgeEffects[edge.id] !== undefined && (
            <div style={{ marginTop: 6, fontWeight: 600 }}>推定効果: {edgeEffects[edge.id].toFixed(4)}</div>
          )}
          {edge.rationale && (
            <div style={{ marginTop: 8, color: "var(--text-secondary)" }}>{edge.rationale}</div>
          )}
        </>
      )}
    </div>
  );
}

function EdgeEffectRow({ label, edge, effect }: { label: string; edge: DagEdge; effect?: number }) {
  return (
    <div
      style={{
        display: "flex",
        justifyContent: "space-between",
        alignItems: "baseline",
        fontSize: 12,
        padding: "3px 0",
        borderBottom: "1px solid var(--border-hairline)",
      }}
    >
      <span>
        {label}
        <span style={{ color: "var(--text-muted)", marginLeft: 6 }}>{STATUS_LABEL[edge.status]}</span>
      </span>
      <span style={{ fontWeight: 600, color: edge.sign === "negative" ? "var(--status-critical)" : "var(--status-good)" }}>
        {effect !== undefined ? effect.toFixed(3) : SIGN_LABEL[edge.sign]}
      </span>
    </div>
  );
}

const linkButtonStyle: React.CSSProperties = {
  border: "none",
  background: "none",
  color: "var(--text-muted)",
  cursor: "pointer",
  fontSize: 12,
  padding: 0,
};

const primaryButtonStyle: React.CSSProperties = {
  fontSize: 12,
  padding: "6px 12px",
  borderRadius: 6,
  border: "none",
  background: "var(--mode-discovery-accent)",
  color: "#ffffff",
  cursor: "pointer",
};

const secondaryButtonStyle: React.CSSProperties = {
  fontSize: 12,
  padding: "6px 12px",
  borderRadius: 6,
  border: "1px solid var(--border-hairline)",
  background: "none",
  color: "var(--text-secondary)",
  cursor: "pointer",
};

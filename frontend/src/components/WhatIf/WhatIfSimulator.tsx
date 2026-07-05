import { useEffect, useState } from "react";
import { Modal } from "../Modal";
import { fetchCausalAvailableNodes, fetchWhatIf } from "../../api/client";
import type { WhatIfProjection } from "../../api/causalTypes";
import type { FinancialCausalDAG } from "../../types/dag";
import { useReasoningLog } from "../ReasoningLog/useReasoningLog";
import { JARGON } from "../ReasoningLog/useReasoningLog";

export function WhatIfSimulator({
  dag,
  onClose,
  onResults,
}: {
  dag: FinancialCausalDAG;
  onClose: () => void;
  onResults?: (results: Record<string, number>) => void;
}) {
  const { pushLogEntry } = useReasoningLog();
  const [availableNodeIds, setAvailableNodeIds] = useState<string[] | null>(null);
  const [sourceNodeId, setSourceNodeId] = useState("");
  const [deltaPercent, setDeltaPercent] = useState(0);
  const [projections, setProjections] = useState<WhatIfProjection[] | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const nodeById = Object.fromEntries(dag.nodes.map((n) => [n.id, n]));

  useEffect(() => {
    fetchCausalAvailableNodes()
      .then((ids) => {
        const inDag = ids.filter((id) => id in nodeById);
        setAvailableNodeIds(inDag);
        if (inDag.length > 0) setSourceNodeId(inDag[0]);
      })
      .catch((e) => setError(e instanceof Error ? e.message : String(e)));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function handleRecompute() {
    if (!sourceNodeId || isLoading) return;
    setIsLoading(true);
    setError(null);
    try {
      const results = await fetchWhatIf(sourceNodeId, deltaPercent);
      setProjections(results);
      onResults?.(Object.fromEntries(results.map((p) => [p.node_id, p.delta_absolute])));
      const sourceLabel = nodeById[sourceNodeId]?.label ?? sourceNodeId;
      pushLogEntry({
        phase: "inference",
        method: "DoWhy backdoor.linear_regression",
        message: `「${sourceLabel}」が${deltaPercent > 0 ? "+" : ""}${deltaPercent}%変化した場合の下流${results.length}件のノードへの影響を算出しました。`,
        jargon: [{ term: "平均処置効果", explanation: JARGON["平均処置効果"] }],
      });
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <Modal title="What-ifシミュレーター" onClose={onClose} width={560}>
      <p style={{ fontSize: 13, color: "var(--text-secondary)", marginTop: 0 }}>
        起点ノードを選び、その値が変化した場合（%）を仮定して、確定済みの因果構造上で
        到達可能な下流ノードへの影響をDoWhyで再推論します。
        <strong>実測データを未収集のため、符号が既知の合成デモデータによる推定です。</strong>
      </p>

      {availableNodeIds === null ? (
        <div style={{ fontSize: 12, color: "var(--text-muted)" }}>読み込み中…</div>
      ) : (
        <>
          <div style={{ marginBottom: 14 }}>
            <label style={{ fontSize: 12, color: "var(--text-secondary)", display: "block", marginBottom: 4 }}>
              起点ノード（何を変化させるか）
            </label>
            <select
              value={sourceNodeId}
              onChange={(e) => setSourceNodeId(e.target.value)}
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
            >
              {availableNodeIds.map((id) => (
                <option key={id} value={id}>
                  {nodeById[id]?.label ?? id}
                </option>
              ))}
            </select>
          </div>

          <div style={{ marginBottom: 14 }}>
            <label style={{ fontSize: 12, color: "var(--text-secondary)", display: "block", marginBottom: 4 }}>
              変化率: {deltaPercent > 0 ? "+" : ""}
              {deltaPercent}%
            </label>
            <input
              type="range"
              min={-50}
              max={50}
              step={1}
              value={deltaPercent}
              onChange={(e) => setDeltaPercent(Number(e.target.value))}
              style={{ width: "100%", accentColor: "var(--mode-inference-accent)" }}
            />
          </div>

          {error && (
            <div style={{ color: "var(--status-critical)", fontSize: 12, marginBottom: 10 }}>
              エラー: {error}
            </div>
          )}

          {projections && (
            <div
              style={{
                border: "1px solid var(--border-hairline)",
                borderRadius: 6,
                marginBottom: 14,
                overflow: "hidden",
              }}
            >
              {projections.map((p, i) => (
                <div
                  key={p.node_id}
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "baseline",
                    padding: "8px 12px",
                    fontSize: 13,
                    borderBottom: i < projections.length - 1 ? "1px solid var(--border-hairline)" : undefined,
                  }}
                >
                  <span>{nodeById[p.node_id]?.label ?? p.node_id}</span>
                  <span
                    style={{
                      fontWeight: 700,
                      color: p.delta_absolute >= 0 ? "var(--status-good)" : "var(--status-critical)",
                    }}
                  >
                    {p.delta_absolute >= 0 ? "+" : ""}
                    {p.delta_absolute.toFixed(2)}
                    <span style={{ fontWeight: 400, color: "var(--text-muted)", marginLeft: 6 }}>
                      ({p.delta_percent >= 0 ? "+" : ""}
                      {p.delta_percent.toFixed(1)}%)
                    </span>
                  </span>
                </div>
              ))}
            </div>
          )}

          <div style={{ display: "flex", justifyContent: "flex-end" }}>
            <button
              onClick={handleRecompute}
              disabled={isLoading || !sourceNodeId}
              style={{
                fontSize: 13,
                padding: "8px 16px",
                borderRadius: 6,
                border: "none",
                background: "var(--mode-inference-accent)",
                color: "#ffffff",
                cursor: isLoading ? "default" : "pointer",
                opacity: isLoading ? 0.6 : 1,
              }}
            >
              {isLoading ? "再推論中…" : "条件を変更して因果効果を再推論する"}
            </button>
          </div>
        </>
      )}
    </Modal>
  );
}

import { useEffect, useState } from "react";
import { Modal } from "../Modal";
import { estimateCausalEffect, fetchCausalAvailableNodes } from "../../api/client";
import type { CausalEffectResult } from "../../api/causalTypes";
import type { FinancialCausalDAG } from "../../types/dag";
import { useReasoningLog } from "../ReasoningLog/useReasoningLog";
import { JARGON } from "../ReasoningLog/useReasoningLog";

export function EffectEstimationPanel({
  dag,
  onClose,
}: {
  dag: FinancialCausalDAG;
  onClose: () => void;
}) {
  const [availableNodeIds, setAvailableNodeIds] = useState<string[] | null>(null);
  const [treatment, setTreatment] = useState("");
  const [outcome, setOutcome] = useState("");
  const [result, setResult] = useState<CausalEffectResult | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { pushLogEntry } = useReasoningLog();

  const nodeById = Object.fromEntries(dag.nodes.map((n) => [n.id, n]));

  useEffect(() => {
    fetchCausalAvailableNodes()
      .then((ids) => {
        const inDag = ids.filter((id) => id in nodeById);
        setAvailableNodeIds(inDag);
        if (inDag.length >= 2) {
          setTreatment(inDag[0]);
          setOutcome(inDag[1]);
        }
      })
      .catch((e) => setError(e instanceof Error ? e.message : String(e)));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function handleEstimate() {
    if (!treatment || !outcome || treatment === outcome || isLoading) return;
    setIsLoading(true);
    setError(null);
    setResult(null);
    try {
      const r = await estimateCausalEffect(treatment, outcome);
      setResult(r);
      pushLogEntry({
        phase: "inference",
        method: "DoWhy backdoor.linear_regression",
        message: `「${nodeById[treatment]?.label ?? treatment}」→「${nodeById[outcome]?.label ?? outcome}」への効果を${r.estimated_effect.toFixed(4)}と算出しました。`,
        jargon: [
          { term: "バックドア調整変数", explanation: JARGON["バックドア調整変数"] },
          { term: "backdoor.linear_regression", explanation: JARGON["backdoor.linear_regression"] },
        ],
      });
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setIsLoading(false);
    }
  }

  const selectStyle: React.CSSProperties = {
    width: "100%",
    boxSizing: "border-box",
    fontSize: 13,
    padding: "8px 10px",
    borderRadius: 6,
    border: "1px solid var(--border-hairline)",
    background: "var(--page-plane)",
    color: "var(--text-primary)",
  };

  return (
    <Modal title="因果効果を推定（DoWhy）" onClose={onClose}>
      <p style={{ fontSize: 13, color: "var(--text-secondary)", marginTop: 0 }}>
        確定済み（AI仮説を除く）のエッジ構造をもとに、処置変数が結果変数に与える
        因果効果をDoWhyで推定します。<strong>
          実測の時系列データを未収集のため、符号が既知の合成デモデータによる推定です。
        </strong>
      </p>

      {availableNodeIds === null ? (
        <div style={{ fontSize: 12, color: "var(--text-muted)" }}>読み込み中…</div>
      ) : availableNodeIds.length < 2 ? (
        <div style={{ fontSize: 12, color: "var(--status-critical)" }}>
          デモデータに対応するノードが不足しています。
        </div>
      ) : (
        <>
          <div style={{ marginBottom: 10 }}>
            <label style={{ fontSize: 12, color: "var(--text-secondary)", display: "block", marginBottom: 4 }}>
              処置変数（原因）
            </label>
            <select value={treatment} onChange={(e) => setTreatment(e.target.value)} style={selectStyle}>
              {availableNodeIds.map((id) => (
                <option key={id} value={id}>
                  {nodeById[id]?.label ?? id}
                </option>
              ))}
            </select>
          </div>
          <div style={{ marginBottom: 10 }}>
            <label style={{ fontSize: 12, color: "var(--text-secondary)", display: "block", marginBottom: 4 }}>
              結果変数
            </label>
            <select value={outcome} onChange={(e) => setOutcome(e.target.value)} style={selectStyle}>
              {availableNodeIds.map((id) => (
                <option key={id} value={id}>
                  {nodeById[id]?.label ?? id}
                </option>
              ))}
            </select>
          </div>

          {error && (
            <div style={{ color: "var(--status-critical)", fontSize: 12, marginBottom: 10 }}>
              エラー: {error}
            </div>
          )}

          {result && (
            <div
              style={{
                background: "var(--page-plane)",
                border: "1px solid var(--border-hairline)",
                borderRadius: 6,
                padding: "10px 12px",
                fontSize: 13,
                marginBottom: 10,
              }}
            >
              <div>
                手法: <span style={{ color: "var(--text-secondary)" }}>{result.method_name}</span>
              </div>
              <div>
                バックドア調整変数:{" "}
                <span style={{ color: "var(--text-secondary)" }}>
                  {result.backdoor_variables.length > 0 ? result.backdoor_variables.join(", ") : "なし"}
                </span>
              </div>
              <div style={{ fontWeight: 600, marginTop: 6 }}>
                推定効果: {result.estimated_effect.toFixed(4)}
              </div>
            </div>
          )}

          <div style={{ display: "flex", justifyContent: "flex-end" }}>
            <button
              onClick={handleEstimate}
              disabled={isLoading || treatment === outcome}
              style={{
                fontSize: 13,
                padding: "8px 16px",
                borderRadius: 6,
                border: "none",
                background: "var(--mode-inference-accent)",
                color: "#ffffff",
                cursor: isLoading ? "default" : "pointer",
                opacity: isLoading || treatment === outcome ? 0.6 : 1,
              }}
            >
              {isLoading ? "推論中…" : "因果効果を推論する"}
            </button>
          </div>
        </>
      )}
    </Modal>
  );
}

import { useRef, useState } from "react";
import { Modal } from "../Modal";
import { extractIrData, mergeIrData } from "../../api/client";
import type { IRDataPoint } from "../../api/irTypes";
import type { FinancialCausalDAG, NodeSource } from "../../types/dag";

const MANUAL_DATA_SUFFIXES = [".csv", ".xlsx", ".xlsm"];

function guessSource(fileName: string): NodeSource {
  const lower = fileName.toLowerCase();
  return MANUAL_DATA_SUFFIXES.some((s) => lower.endsWith(s)) ? "user_added" : "ir_data";
}

export function IrDataPanel({
  onMerged,
  onClose,
}: {
  onMerged: (dag: FinancialCausalDAG) => void;
  onClose: () => void;
}) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [dataPoints, setDataPoints] = useState<IRDataPoint[] | null>(null);
  const [source, setSource] = useState<NodeSource>("ir_data");
  const [isExtracting, setIsExtracting] = useState(false);
  const [isMerging, setIsMerging] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setIsExtracting(true);
    setError(null);
    setDataPoints(null);
    try {
      const points = await extractIrData(file);
      setDataPoints(points);
      setSource(guessSource(file.name));
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setIsExtracting(false);
    }
  }

  async function handleMerge() {
    if (!dataPoints || dataPoints.length === 0 || isMerging) return;
    setIsMerging(true);
    setError(null);
    try {
      const dag = await mergeIrData(dataPoints, source);
      onMerged(dag);
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setIsMerging(false);
    }
  }

  return (
    <Modal title="IRデータ・手動データの取り込み" onClose={onClose}>
      <p style={{ fontSize: 13, color: "var(--text-secondary)", marginTop: 0 }}>
        決算資料等(PDF/HTML/テキスト)はLLMで財務数値・KPIを抽出し、CSV/Excelは
        列（label, kind, value, unit, period）をそのまま読み込みます。
      </p>
      <input
        ref={fileInputRef}
        type="file"
        accept=".pdf,.html,.htm,.txt,.csv,.xlsx,.xlsm"
        onChange={handleFileChange}
        disabled={isExtracting}
        style={{ fontSize: 13 }}
      />

      {isExtracting && (
        <div style={{ fontSize: 12, color: "var(--text-muted)", marginTop: 10 }}>
          抽出中…
        </div>
      )}

      {error && (
        <div style={{ color: "var(--status-critical)", fontSize: 12, marginTop: 10 }}>
          エラー: {error}
        </div>
      )}

      {dataPoints && (
        <>
          <div style={{ marginTop: 14, marginBottom: 8, fontSize: 12, color: "var(--text-secondary)" }}>
            抽出結果 {dataPoints.length}件
          </div>
          <div
            style={{
              maxHeight: 220,
              overflowY: "auto",
              border: "1px solid var(--border-hairline)",
              borderRadius: 6,
            }}
          >
            {dataPoints.map((dp, i) => (
              <div
                key={i}
                style={{
                  padding: "8px 10px",
                  borderBottom: i < dataPoints.length - 1 ? "1px solid var(--border-hairline)" : undefined,
                  fontSize: 12,
                }}
              >
                <div style={{ fontWeight: 600 }}>
                  {dp.label}
                  {dp.period ? `（${dp.period}）` : ""}
                </div>
                <div style={{ color: "var(--text-secondary)" }}>
                  {dp.value ?? "—"} {dp.unit ?? ""} ・ {dp.kind === "financial" ? "財務" : "非財務"}
                </div>
                {dp.source.excerpt && (
                  <div style={{ color: "var(--text-muted)", marginTop: 2 }}>「{dp.source.excerpt}」</div>
                )}
              </div>
            ))}
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 12 }}>
            <label style={{ fontSize: 12, color: "var(--text-secondary)" }}>マージ後の由来:</label>
            <select
              value={source}
              onChange={(e) => setSource(e.target.value as NodeSource)}
              style={{
                fontSize: 12,
                padding: "4px 8px",
                borderRadius: 6,
                border: "1px solid var(--border-hairline)",
                background: "var(--page-plane)",
                color: "var(--text-primary)",
              }}
            >
              <option value="ir_data">IRデータ</option>
              <option value="user_added">手動追加</option>
            </select>
          </div>

          <div style={{ display: "flex", justifyContent: "flex-end", marginTop: 14 }}>
            <button
              onClick={handleMerge}
              disabled={isMerging}
              style={{
                fontSize: 13,
                padding: "8px 16px",
                borderRadius: 6,
                border: "none",
                background: "var(--cat-pl)",
                color: "#ffffff",
                cursor: isMerging ? "default" : "pointer",
                opacity: isMerging ? 0.6 : 1,
              }}
            >
              {isMerging ? "マージ中…" : "ツリーにマージする"}
            </button>
          </div>
        </>
      )}
    </Modal>
  );
}

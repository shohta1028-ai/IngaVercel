import { useRef, useState } from "react";
import { Modal } from "../Modal";
import { extractIrData, fetchEdinetDocument, mergeIrData, searchEdinetDocuments } from "../../api/client";
import type { IRDataPoint } from "../../api/irTypes";
import type { EdinetDocumentSummary } from "../../api/edinetTypes";
import type { FinancialCausalDAG, NodeSource } from "../../types/dag";

const MANUAL_DATA_SUFFIXES = [".csv", ".xlsx", ".xlsm"];
const EDINET_MAX_SEARCH_DAYS = 31;

function guessSource(fileName: string): NodeSource {
  const lower = fileName.toLowerCase();
  return MANUAL_DATA_SUFFIXES.some((s) => lower.endsWith(s)) ? "user_added" : "ir_data";
}

function toDateInputValue(d: Date): string {
  return d.toISOString().slice(0, 10);
}

function defaultFromDate(): string {
  const d = new Date();
  d.setDate(d.getDate() - 30);
  return toDateInputValue(d);
}

type IngestMode = "file" | "edinet";

const tabButtonStyle = (active: boolean): React.CSSProperties => ({
  flex: 1,
  padding: "8px 10px",
  fontSize: 12,
  fontWeight: 600,
  border: "none",
  borderBottom: active ? "2px solid var(--mode-discovery-accent)" : "2px solid transparent",
  background: "none",
  color: active ? "var(--mode-discovery-accent)" : "var(--text-secondary)",
  cursor: "pointer",
});

const dateInputStyle: React.CSSProperties = {
  fontSize: 12,
  padding: "5px 8px",
  borderRadius: 6,
  border: "1px solid var(--border-hairline)",
  background: "var(--page-plane)",
  color: "var(--text-primary)",
};

export function IrDataPanel({
  onMerged,
  onClose,
}: {
  onMerged: (dag: FinancialCausalDAG) => void;
  onClose: () => void;
}) {
  const [mode, setMode] = useState<IngestMode>("file");
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [dataPoints, setDataPoints] = useState<IRDataPoint[] | null>(null);
  const [source, setSource] = useState<NodeSource>("ir_data");
  const [isExtracting, setIsExtracting] = useState(false);
  const [isMerging, setIsMerging] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // EDINET検索モード
  const [company, setCompany] = useState("");
  const [fromDate, setFromDate] = useState(defaultFromDate());
  const [toDate, setToDate] = useState(toDateInputValue(new Date()));
  const [searchResults, setSearchResults] = useState<EdinetDocumentSummary[] | null>(null);
  const [isSearching, setIsSearching] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);
  const [fetchingDocId, setFetchingDocId] = useState<string | null>(null);

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

  async function handleEdinetSearch() {
    if (!company.trim() || isSearching) return;
    setIsSearching(true);
    setSearchError(null);
    setSearchResults(null);
    try {
      const results = await searchEdinetDocuments(company.trim(), fromDate, toDate);
      setSearchResults(results);
    } catch (err) {
      setSearchError(err instanceof Error ? err.message : String(err));
    } finally {
      setIsSearching(false);
    }
  }

  async function handleEdinetFetch(doc: EdinetDocumentSummary) {
    if (fetchingDocId) return;
    setFetchingDocId(doc.doc_id);
    setError(null);
    setDataPoints(null);
    try {
      const points = await fetchEdinetDocument(doc.doc_id, doc.filer_name, doc.doc_description ?? undefined);
      setDataPoints(points);
      setSource("ir_data");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setFetchingDocId(null);
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
      <div style={{ display: "flex", marginBottom: 12, borderBottom: "1px solid var(--border-hairline)" }}>
        <button style={tabButtonStyle(mode === "file")} onClick={() => setMode("file")}>
          ファイルアップロード
        </button>
        <button style={tabButtonStyle(mode === "edinet")} onClick={() => setMode("edinet")}>
          EDINETから検索
        </button>
      </div>

      {mode === "file" && (
        <>
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
        </>
      )}

      {mode === "edinet" && (
        <>
          <p style={{ fontSize: 13, color: "var(--text-secondary)", marginTop: 0 }}>
            金融庁EDINET（有価証券報告書等の法定開示API）を企業名または証券コードで
            検索します（検索範囲は最大{EDINET_MAX_SEARCH_DAYS}日間）。取得した書類は
            ファイルアップロードと同じくLLMで財務数値・KPIを抽出します。
          </p>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
            <input
              value={company}
              onChange={(e) => setCompany(e.target.value)}
              placeholder="企業名または証券コード（例: ファナック、6954）"
              style={{ ...dateInputStyle, flex: "1 1 200px" }}
            />
            <label style={{ fontSize: 12, color: "var(--text-secondary)", display: "flex", alignItems: "center", gap: 4 }}>
              期間
              <input
                type="date"
                value={fromDate}
                onChange={(e) => setFromDate(e.target.value)}
                style={dateInputStyle}
              />
              〜
              <input
                type="date"
                value={toDate}
                onChange={(e) => setToDate(e.target.value)}
                style={dateInputStyle}
              />
            </label>
            <button
              onClick={handleEdinetSearch}
              disabled={isSearching || !company.trim()}
              style={{
                fontSize: 12,
                padding: "6px 14px",
                borderRadius: 6,
                border: "none",
                background: "var(--mode-discovery-accent)",
                color: "#ffffff",
                cursor: isSearching ? "default" : "pointer",
                opacity: isSearching || !company.trim() ? 0.6 : 1,
              }}
            >
              {isSearching ? "検索中…" : "検索"}
            </button>
          </div>

          {searchError && (
            <div style={{ color: "var(--status-critical)", fontSize: 12, marginTop: 10 }}>
              エラー: {searchError}
            </div>
          )}

          {searchResults && (
            <div
              style={{
                marginTop: 12,
                maxHeight: 200,
                overflowY: "auto",
                border: "1px solid var(--border-hairline)",
                borderRadius: 6,
              }}
            >
              {searchResults.length === 0 && (
                <div style={{ padding: 10, fontSize: 12, color: "var(--text-muted)" }}>
                  該当する書類が見つかりませんでした。企業名の表記や期間を変えて再検索してください。
                </div>
              )}
              {searchResults.map((doc) => (
                <div
                  key={doc.doc_id}
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    gap: 8,
                    padding: "8px 10px",
                    borderBottom: "1px solid var(--border-hairline)",
                    fontSize: 12,
                  }}
                >
                  <div>
                    <div style={{ fontWeight: 600 }}>{doc.filer_name}</div>
                    <div style={{ color: "var(--text-secondary)" }}>{doc.doc_description ?? "—"}</div>
                    <div style={{ color: "var(--text-muted)" }}>提出日: {doc.submit_date_time ?? "—"}</div>
                  </div>
                  <button
                    onClick={() => handleEdinetFetch(doc)}
                    disabled={fetchingDocId !== null}
                    style={{
                      flexShrink: 0,
                      fontSize: 12,
                      padding: "6px 10px",
                      borderRadius: 6,
                      border: "1px solid var(--border-hairline)",
                      background: "var(--page-plane)",
                      color: "var(--text-primary)",
                      cursor: fetchingDocId !== null ? "default" : "pointer",
                      opacity: fetchingDocId !== null && fetchingDocId !== doc.doc_id ? 0.5 : 1,
                    }}
                  >
                    {fetchingDocId === doc.doc_id ? "取込中…" : "この書類を取り込む"}
                  </button>
                </div>
              ))}
            </div>
          )}
        </>
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

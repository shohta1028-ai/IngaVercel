import { useEffect, useRef, useState } from "react";
import type { Dispatch, SetStateAction } from "react";
import type { FinancialCausalDAG } from "../../types/dag";
import type { TuningProposal } from "../../api/tuningTypes";
import { fetchTuningProposal, respondToTuningProposal } from "../../api/client";

type ChatMessage = { role: "ai" | "user"; text: string };

const BASE_ROUNDS = 5;

function defaultTuningState(): NonNullable<FinancialCausalDAG["tuning_state"]> {
  return { status: "not_started", completed_rounds: 0, rounds: [] };
}

export function ChatTuning({
  dag,
  setDag,
  onClose,
}: {
  dag: FinancialCausalDAG;
  setDag: Dispatch<SetStateAction<FinancialCausalDAG>>;
  onClose: () => void;
}) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [currentProposal, setCurrentProposal] = useState<TuningProposal | null>(null);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const logEndRef = useRef<HTMLDivElement>(null);
  const hasFetchedInitial = useRef(false);

  const tuningState = dag.tuning_state ?? defaultTuningState();

  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, isLoading]);

  async function loadNextProposal() {
    setIsLoading(true);
    setError(null);
    try {
      const proposal = await fetchTuningProposal();
      if (proposal) {
        setCurrentProposal(proposal);
        setMessages((prev) => [...prev, { role: "ai", text: proposal.ai_message }]);
      } else {
        setCurrentProposal(null);
        setMessages((prev) => [
          ...prev,
          { role: "ai", text: "現時点で確認・提案する項目はありません。" },
        ]);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    if (hasFetchedInitial.current) return;
    hasFetchedInitial.current = true;
    loadNextProposal();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function handleSend() {
    const text = input.trim();
    if (!text || !currentProposal || isLoading) return;

    setInput("");
    setMessages((prev) => [...prev, { role: "user", text }]);
    setIsLoading(true);
    setError(null);

    try {
      const updatedDag = await respondToTuningProposal(currentProposal, text);
      setDag(updatedDag);
      setCurrentProposal(null);
      await loadNextProposal();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
      setIsLoading(false);
    }
  }

  const isLocked = tuningState.status === "locked";

  return (
    <div
      style={{
        borderTop: "1px solid var(--border-hairline)",
        background: "var(--surface-1)",
        display: "flex",
        flexDirection: "column",
        height: 320,
        flexShrink: 0,
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "8px 14px",
          borderBottom: "1px solid var(--border-hairline)",
          fontSize: 12,
          color: "var(--text-secondary)",
        }}
      >
        <span>
          対話チューニング（{tuningState.completed_rounds}/{BASE_ROUNDS}ラウンド完了
          {isLocked ? " ・ ロック中" : ""}）
        </span>
        <button
          onClick={onClose}
          style={{ border: "none", background: "none", color: "var(--text-muted)", cursor: "pointer" }}
          aria-label="閉じる"
        >
          ×
        </button>
      </div>

      <div style={{ flex: 1, overflowY: "auto", padding: "10px 14px", display: "flex", flexDirection: "column", gap: 8 }}>
        {messages.map((m, i) => (
          <div
            key={i}
            style={{
              alignSelf: m.role === "ai" ? "flex-start" : "flex-end",
              maxWidth: "80%",
              background: m.role === "ai" ? "var(--page-plane)" : "var(--cat-pl)",
              color: m.role === "ai" ? "var(--text-primary)" : "#ffffff",
              borderRadius: 10,
              padding: "8px 12px",
              fontSize: 13,
            }}
          >
            {m.text}
          </div>
        ))}
        {isLoading && (
          <div
            style={{
              alignSelf: "flex-start",
              color: "var(--text-muted)",
              fontSize: 12,
              fontStyle: "italic",
            }}
          >
            AIが考えています…
          </div>
        )}
        {error && (
          <div style={{ alignSelf: "flex-start", color: "var(--status-critical)", fontSize: 12 }}>
            エラー: {error}
          </div>
        )}
        <div ref={logEndRef} />
      </div>

      <div style={{ display: "flex", gap: 8, padding: "10px 14px", borderTop: "1px solid var(--border-hairline)" }}>
        {currentProposal ? (
          <>
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") handleSend();
              }}
              disabled={isLoading}
              placeholder="回答を入力（例: YES、3ヶ月後にタイムラグ設定希望）"
              style={{
                flex: 1,
                fontSize: 13,
                padding: "6px 10px",
                borderRadius: 6,
                border: "1px solid var(--border-hairline)",
                background: "var(--page-plane)",
                color: "var(--text-primary)",
              }}
            />
            <button
              onClick={handleSend}
              disabled={isLoading}
              style={{
                fontSize: 13,
                padding: "6px 14px",
                borderRadius: 6,
                border: "none",
                background: "var(--cat-pl)",
                color: "#ffffff",
                cursor: isLoading ? "default" : "pointer",
                opacity: isLoading ? 0.6 : 1,
              }}
            >
              送信
            </button>
          </>
        ) : (
          <button
            onClick={loadNextProposal}
            disabled={isLoading}
            style={{
              fontSize: 13,
              padding: "6px 14px",
              borderRadius: 6,
              border: "1px solid var(--border-hairline)",
              background: "var(--page-plane)",
              color: "var(--text-primary)",
              cursor: isLoading ? "default" : "pointer",
              width: "100%",
            }}
          >
            次の提案を確認する（新しい候補ノードの追加後などに再実行）
          </button>
        )}
      </div>
    </div>
  );
}

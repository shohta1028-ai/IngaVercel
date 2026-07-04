import { useEffect, useRef, useState } from "react";
import type { Dispatch, SetStateAction } from "react";
import type { DagEdge, FinancialCausalDAG, TuningRound } from "../../types/dag";
import { interpretUserText, pickNextProposal, type TuningProposal } from "../../lib/tuningSimulation";

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
  const logEndRef = useRef<HTMLDivElement>(null);

  const tuningState = dag.tuning_state ?? defaultTuningState();

  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages]);

  useEffect(() => {
    if (messages.length > 0) return; // 初回のみ自動で最初の提案を出す
    const proposal = pickNextProposal(dag);
    if (proposal) {
      setCurrentProposal(proposal);
      setMessages([{ role: "ai", text: proposal.aiMessage }]);
    } else {
      setMessages([{ role: "ai", text: "現時点で確認・提案する項目はありません。" }]);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function applyRound(userText: string, appliedChanges: string[], edgeUpdate?: DagEdge, replaceEdgeId?: string) {
    setDag((prev) => {
      const prevTuning = prev.tuning_state ?? defaultTuningState();
      const roundNumber = prevTuning.rounds.length + 1;

      let edges = prev.edges;
      if (edgeUpdate) {
        edges = replaceEdgeId
          ? edges.map((e) => (e.id === replaceEdgeId ? edgeUpdate : e))
          : [...edges, edgeUpdate];
      }

      const round: TuningRound = {
        round_number: roundNumber,
        ai_message: currentProposal?.aiMessage ?? "(自由記述ラウンド)",
        user_response: userText,
        applied_changes: appliedChanges,
      };

      return {
        ...prev,
        edges,
        tuning_state: {
          status: roundNumber >= BASE_ROUNDS ? "locked" : "in_progress",
          completed_rounds: Math.min(roundNumber, BASE_ROUNDS),
          rounds: [...prevTuning.rounds, round],
        },
      };
    });
  }

  function fetchNextProposal(nextDag: FinancialCausalDAG) {
    const proposal = pickNextProposal(nextDag);
    if (proposal) {
      setCurrentProposal(proposal);
      setMessages((prev) => [...prev, { role: "ai", text: proposal.aiMessage }]);
    } else {
      setCurrentProposal(null);
      setMessages((prev) => [
        ...prev,
        { role: "ai", text: "確認する項目がなくなりました。ここまでの内容で調整を完了します。" },
      ]);
    }
  }

  function handleSend() {
    const text = input.trim();
    if (!text) return;
    setInput("");
    setMessages((prev) => [...prev, { role: "user", text }]);

    if (!currentProposal) {
      // ロック後の任意追加ラウンド: 具体的な提案が無い場合はコメントとして記録するのみ
      applyRound(text, ["ユーザーからの追加コメントを記録（構造変更は自動適用されません）"]);
      return;
    }

    const parsed = interpretUserText(text);
    const proposal = currentProposal;

    if (parsed.decision === "reject") {
      if (proposal.kind === "confirm_edge") {
        const rejected: DagEdge = { ...proposal.candidateEdge, status: "rejected", round_added: proposal.roundNumber };
        applyRound(text, [`エッジ${rejected.id}を却下(rejected)`], rejected, rejected.id);
      } else {
        applyRound(text, [`ノード「${proposal.candidateEdge.source_node_id}」の紐付け提案を却下（未接続のまま）`]);
      }
    } else {
      const status = parsed.decision === "modify" ? "user_modified" : "user_confirmed";
      const finalEdge: DagEdge = {
        ...proposal.candidateEdge,
        sign: parsed.signOverride ?? proposal.candidateEdge.sign,
        lag:
          parsed.lagValue !== undefined && parsed.lagUnit !== undefined
            ? { value: parsed.lagValue, unit: parsed.lagUnit }
            : proposal.candidateEdge.lag,
        status,
        round_added: proposal.roundNumber,
      };
      const changeDescription =
        proposal.kind === "confirm_edge"
          ? [`エッジ${finalEdge.id}を${status}として確定`]
          : [`新規エッジ${finalEdge.id}を追加し${status}として確定`];
      applyRound(
        text,
        changeDescription,
        finalEdge,
        proposal.kind === "confirm_edge" ? finalEdge.id : undefined
      );
    }

    setCurrentProposal(null);
  }

  // ラウンドが1件確定した直後に次の提案を出す（roundsの件数をトリガーにする —
  // 却下ラウンドのようにedges参照が変化しないケースでも確実に発火させるため）
  const roundsCount = tuningState.rounds.length;
  useEffect(() => {
    if (messages.length === 0) return;
    if (currentProposal) return;
    fetchNextProposal(dag);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [roundsCount]);

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
          {isLocked ? " ・ ロック中 - 自由記述で追加ラウンドを開始できます" : ""}）
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
        <div ref={logEndRef} />
      </div>

      <div style={{ display: "flex", gap: 8, padding: "10px 14px", borderTop: "1px solid var(--border-hairline)" }}>
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") handleSend();
          }}
          placeholder={isLocked && !currentProposal ? "追加の調整指示を自由に入力…" : "回答を入力（例: YES、3ヶ月後にタイムラグ設定希望）"}
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
          style={{
            fontSize: 13,
            padding: "6px 14px",
            borderRadius: 6,
            border: "none",
            background: "var(--cat-pl)",
            color: "#ffffff",
            cursor: "pointer",
          }}
        >
          送信
        </button>
      </div>
    </div>
  );
}

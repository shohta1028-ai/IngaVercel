import { useEffect, useRef } from "react";
import { useReasoningLog } from "./useReasoningLog";
import { JargonTerm } from "./JargonTerm";

const PHASE_LABEL: Record<string, string> = {
  discovery: "因果探索",
  inference: "因果推論",
};

export function ReasoningLog() {
  const { entries } = useReasoningLog();
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [entries.length]);

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        minHeight: 0,
        flex: 1,
        borderTop: "1px solid var(--border-hairline)",
      }}
    >
      <div
        style={{
          padding: "10px 14px 6px",
          fontSize: 11,
          fontWeight: 600,
          color: "var(--text-muted)",
          textTransform: "uppercase",
          letterSpacing: "0.04em",
        }}
      >
        AIの脳内ログ
      </div>
      <div style={{ flex: 1, overflowY: "auto", padding: "0 14px 12px", display: "flex", flexDirection: "column", gap: 8 }}>
        {entries.length === 0 && (
          <div style={{ fontSize: 12, color: "var(--text-muted)" }}>
            まだ記録はありません。対話チューニングや因果効果の推論を行うと、
            AIの処理内容がここに表示されます。
          </div>
        )}
        {entries.map((entry) => {
          const accent =
            entry.phase === "discovery" ? "var(--mode-discovery-accent)" : "var(--mode-inference-accent)";
          return (
            <div
              key={entry.id}
              style={{
                fontSize: 12.5,
                lineHeight: 1.6,
                borderLeft: `2px solid ${accent}`,
                paddingLeft: 8,
              }}
            >
              <div style={{ color: accent, fontWeight: 600, fontSize: 11 }}>
                [{PHASE_LABEL[entry.phase]}: {entry.method}
                {entry.jargon?.map((j) => (
                  <JargonTerm key={j.term} term={j.term} explanation={j.explanation} />
                ))}
                ]
              </div>
              <div style={{ color: "var(--text-primary)" }}>{entry.message}</div>
            </div>
          );
        })}
        <div ref={endRef} />
      </div>
    </div>
  );
}

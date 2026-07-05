import { createContext, useCallback, useContext, useState } from "react";
import type { ReactNode } from "react";

export type LogPhase = "discovery" | "inference";

export interface JargonEntry {
  term: string;
  explanation: string;
}

export interface LogEntry {
  id: string;
  phase: LogPhase;
  method: string;
  message: string;
  jargon?: JargonEntry[];
  timestamp: number;
}

interface ReasoningLogContextValue {
  entries: LogEntry[];
  pushLogEntry: (entry: Omit<LogEntry, "id" | "timestamp">) => void;
}

const ReasoningLogContext = createContext<ReasoningLogContextValue | null>(null);

export function ReasoningLogProvider({ children }: { children: ReactNode }) {
  const [entries, setEntries] = useState<LogEntry[]>([]);

  const pushLogEntry = useCallback((entry: Omit<LogEntry, "id" | "timestamp">) => {
    setEntries((prev) => [
      ...prev,
      {
        ...entry,
        id: `log_${Date.now()}_${Math.random().toString(36).slice(2, 7)}`,
        timestamp: Date.now(),
      },
    ]);
  }, []);

  return (
    <ReasoningLogContext.Provider value={{ entries, pushLogEntry }}>
      {children}
    </ReasoningLogContext.Provider>
  );
}

export function useReasoningLog(): ReasoningLogContextValue {
  const ctx = useContext(ReasoningLogContext);
  if (!ctx) {
    throw new Error("useReasoningLog must be used within a ReasoningLogProvider");
  }
  return ctx;
}

// 因果探索・因果推論でよく出てくる専門用語の説明集
export const JARGON: Record<string, string> = {
  "LLM仮説生成": "大規模言語モデルが会計知識やIRデータをもとに因果関係の仮説を提示する手法。統計的な自動検出ではなく、対話で人間が確認・修正する前提。",
  "backdoor.linear_regression": "DoWhyの効果推定手法の一つ。バックドア基準で特定した交絡変数を回帰式に含めて処置変数の係数を効果として推定する。",
  "バックドア調整変数": "処置と結果の両方に影響しうる交絡変数のうち、これを統計的に制御すれば因果効果を正しく推定できるという基準（バックドア基準）で選ばれた変数。",
  "平均処置効果": "処置（原因側の変数）が1単位変化したときに、結果側の変数が平均してどれだけ変化するかを表す値。",
};

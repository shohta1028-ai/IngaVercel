import { useEffect, useState } from "react";
import { fetchDag } from "./api/client";
import { DagTree } from "./components/DagTree/DagTree";
import type { FinancialCausalDAG } from "./types/dag";

export default function App() {
  const [dag, setDag] = useState<FinancialCausalDAG | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchDag()
      .then(setDag)
      .catch((e) => setError(e instanceof Error ? e.message : String(e)));
  }, []);

  if (error) {
    return (
      <div style={{ padding: 24, fontFamily: "system-ui, sans-serif", color: "#c0392b" }}>
        バックエンドAPIに接続できませんでした。backendディレクトリで
        <code style={{ margin: "0 4px" }}>uvicorn app.api.main:app --port 8000</code>
        を起動してください。
        <div style={{ marginTop: 8, color: "#888" }}>{error}</div>
      </div>
    );
  }

  if (!dag) {
    return <div style={{ padding: 24, fontFamily: "system-ui, sans-serif" }}>読み込み中…</div>;
  }

  return (
    <div style={{ width: "100vw", height: "100vh" }}>
      <DagTree dag={dag} />
    </div>
  );
}

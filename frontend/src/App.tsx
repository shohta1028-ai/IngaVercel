import sampleDag from "./fixtures/sample_dag.json";
import { DagTree } from "./components/DagTree/DagTree";
import type { FinancialCausalDAG } from "./types/dag";

const dag = sampleDag as FinancialCausalDAG;

export default function App() {
  return (
    <div style={{ width: "100vw", height: "100vh" }}>
      <DagTree dag={dag} />
    </div>
  );
}

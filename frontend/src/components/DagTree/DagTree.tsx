import { useMemo, useState } from "react";
import {
  Background,
  Controls,
  ReactFlow,
  type Connection,
  type Edge as FlowEdge,
  type Node as FlowNode,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";

import type { FinancialCausalDAG } from "../../types/dag";
import { createEdge, fetchEdgeEffects, updateGoal } from "../../api/client";
import { layoutDagNodes, unconnectedNodeIds } from "../../lib/layout";
import type { Mode } from "../../lib/mode";
import { DagNodeCard, type DagFlowNodeData } from "./DagNodeCard";
import { SectionLabelNode } from "./SectionLabelNode";
import { AnimatedDashedEdge, type DagFlowEdgeData } from "./AnimatedDashedEdge";
import { Legend } from "./Legend";
import { DetailPanel } from "./DetailPanel";
import { TopStrip } from "./TopStrip";
import { ChatTuning } from "../ChatTuning/ChatTuning";
import { TemplateGeneratorPanel } from "../TemplateGenerator/TemplateGeneratorPanel";
import { IrDataPanel } from "../IrData/IrDataPanel";
import { EffectEstimationPanel } from "../CausalEffect/EffectEstimationPanel";
import { WhatIfSimulator } from "../WhatIf/WhatIfSimulator";
import { Sidebar } from "../Sidebar/Sidebar";
import { ReasoningLogProvider, useReasoningLog } from "../ReasoningLog/useReasoningLog";
import { ReasoningLog } from "../ReasoningLog/ReasoningLog";

const nodeTypes = { dagNode: DagNodeCard, sectionLabel: SectionLabelNode };
const edgeTypes = { animatedDashed: AnimatedDashedEdge };

function DagTreeInner({ dag: initialDag }: { dag: FinancialCausalDAG }) {
  const [dag, setDag] = useState(initialDag);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [selectedEdgeId, setSelectedEdgeId] = useState<string | null>(null);
  const [isChatOpen, setIsChatOpen] = useState(false);
  const [isTemplatePanelOpen, setIsTemplatePanelOpen] = useState(false);
  const [isIrPanelOpen, setIsIrPanelOpen] = useState(false);
  const [isEffectPanelOpen, setIsEffectPanelOpen] = useState(false);
  const [isWhatIfPanelOpen, setIsWhatIfPanelOpen] = useState(false);
  const [mode, setMode] = useState<Mode>("discovery");
  const [edgeEffects, setEdgeEffects] = useState<Record<string, number>>({});
  const [whatIfResults, setWhatIfResults] = useState<Record<string, number>>({});
  const { pushLogEntry } = useReasoningLog();

  const isTuningLocked = dag.tuning_state?.status === "locked";

  const nodeById = useMemo(
    () => Object.fromEntries(dag.nodes.map((n) => [n.id, n])),
    [dag.nodes]
  );

  const candidateIds = useMemo(
    () => new Set(unconnectedNodeIds(dag.nodes, dag.edges)),
    [dag.nodes, dag.edges]
  );

  const positions = useMemo(
    () => layoutDagNodes(dag.nodes, dag.edges),
    [dag.nodes, dag.edges]
  );

  const flowNodes: FlowNode[] = useMemo(() => {
    const dagFlowNodes: FlowNode<DagFlowNodeData>[] = dag.nodes.map((n) => ({
      id: n.id,
      type: "dagNode",
      position: positions[n.id],
      data: {
        dagNode: n,
        isCandidate: candidateIds.has(n.id),
        whatIfDelta: mode === "inference" ? whatIfResults[n.id] : undefined,
      },
    }));

    if (candidateIds.size === 0) return dagFlowNodes;

    const anyCandidateId = candidateIds.values().next().value as string;
    const labelNode: FlowNode = {
      id: "__candidate_label",
      type: "sectionLabel",
      position: { x: positions[anyCandidateId].x, y: -50 },
      data: { text: "未接続の候補ノード（ドラッグして紐付け）" },
      draggable: false,
      selectable: false,
    };
    return [...dagFlowNodes, labelNode];
  }, [dag.nodes, positions, candidateIds, mode, whatIfResults]);

  const flowEdges: FlowEdge[] = useMemo(
    () =>
      dag.edges
        // 却下(rejected)されたエッジは対話履歴には残すが、ツリー上には描画しない
        .filter((e) => e.status !== "rejected")
        .map((e) => {
          const data: DagFlowEdgeData = {
            sign: e.sign,
            status: e.status,
            rationale: e.rationale,
            mode,
            effectValue: edgeEffects[e.id],
          };
          return {
            id: e.id,
            source: e.source_node_id,
            target: e.target_node_id,
            type: "animatedDashed",
            data,
            selected: e.id === selectedEdgeId,
          };
        }),
    [dag.edges, selectedEdgeId, mode, edgeEffects]
  );

  const selectedNode = selectedNodeId ? nodeById[selectedNodeId] : undefined;
  const selectedEdge = selectedEdgeId
    ? dag.edges.find((e) => e.id === selectedEdgeId)
    : undefined;

  function handleConnect(connection: Connection) {
    if (!connection.source || !connection.target) return;
    createEdge(connection.source, connection.target)
      .then(setDag)
      .catch((e) => console.error("エッジの追加に失敗しました", e));
  }

  function handleGoalChange(goal: string) {
    setDag((prev) => ({ ...prev, goal })); // 入力中の見た目を即時反映
    updateGoal(goal).catch((e) => console.error("ゴールの更新に失敗しました", e));
  }

  async function handleToggleMode() {
    if (mode === "discovery") {
      setMode("inference");
      try {
        const effects = await fetchEdgeEffects();
        setEdgeEffects(effects);
        pushLogEntry({
          phase: "inference",
          method: "DoWhy backdoor.linear_regression",
          message: `確定済みの${Object.keys(effects).length}本のエッジについて、直接効果を一括推定しツリーに反映しました。`,
        });
      } catch (e) {
        console.error("エッジ効果の一括推定に失敗しました", e);
      }
    } else {
      setMode("discovery");
    }
  }

  return (
    <div style={{ width: "100%", height: "100%", display: "flex" }} data-mode={mode}>
      <Sidebar
        mode={mode}
        isChatOpen={isChatOpen}
        isTuningLocked={isTuningLocked}
        onToggleChat={() => setIsChatOpen((v) => !v)}
        onOpenTemplateGenerator={() => setIsTemplatePanelOpen(true)}
        onOpenIrData={() => setIsIrPanelOpen(true)}
        onOpenEffectEstimation={() => setIsEffectPanelOpen(true)}
        onOpenWhatIf={() => setIsWhatIfPanelOpen(true)}
        onToggleMode={handleToggleMode}
      />
      <div style={{ flex: 1, minWidth: 0, display: "flex", flexDirection: "column" }}>
        <TopStrip goal={dag.goal ?? ""} onGoalChange={handleGoalChange} mode={mode} />
        <div style={{ flex: 1, minHeight: 0, display: "flex" }}>
          <Legend />
          <div style={{ flex: 1, minWidth: 0, position: "relative" }}>
            <ReactFlow
              nodes={flowNodes}
              edges={flowEdges}
              nodeTypes={nodeTypes}
              edgeTypes={edgeTypes}
              onConnect={handleConnect}
              onNodeClick={(_, node) => {
                if (node.type !== "dagNode") return;
                setSelectedNodeId(node.id);
                setSelectedEdgeId(null);
              }}
              onEdgeClick={(_, edge) => {
                setSelectedEdgeId(edge.id);
                setSelectedNodeId(null);
              }}
              onPaneClick={() => {
                setSelectedNodeId(null);
                setSelectedEdgeId(null);
              }}
              fitView
              fitViewOptions={{ padding: 0.15 }}
              proOptions={{ hideAttribution: true }}
            >
              <Background color="var(--gridline)" gap={24} />
              <Controls />
            </ReactFlow>
          </div>
          <div
            style={{
              width: 280,
              flexShrink: 0,
              display: "flex",
              flexDirection: "column",
              borderLeft: "1px solid var(--border-hairline)",
              background: "var(--surface-1)",
            }}
          >
            <DetailPanel
              node={selectedNode}
              edge={selectedEdge}
              nodeById={nodeById}
              onClose={() => {
                setSelectedNodeId(null);
                setSelectedEdgeId(null);
              }}
            />
            <ReasoningLog />
          </div>
        </div>
        {isChatOpen && (
          <ChatTuning dag={dag} setDag={setDag} onClose={() => setIsChatOpen(false)} />
        )}
      </div>
      {isTemplatePanelOpen && (
        <TemplateGeneratorPanel
          onGenerated={setDag}
          onClose={() => setIsTemplatePanelOpen(false)}
        />
      )}
      {isIrPanelOpen && (
        <IrDataPanel onMerged={setDag} onClose={() => setIsIrPanelOpen(false)} />
      )}
      {isEffectPanelOpen && (
        <EffectEstimationPanel dag={dag} onClose={() => setIsEffectPanelOpen(false)} />
      )}
      {isWhatIfPanelOpen && (
        <WhatIfSimulator
          dag={dag}
          onClose={() => setIsWhatIfPanelOpen(false)}
          onResults={setWhatIfResults}
        />
      )}
    </div>
  );
}

export function DagTree({ dag }: { dag: FinancialCausalDAG }) {
  return (
    <ReasoningLogProvider>
      <DagTreeInner dag={dag} />
    </ReasoningLogProvider>
  );
}

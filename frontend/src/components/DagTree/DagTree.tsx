import { useEffect, useMemo, useState } from "react";
import {
  Background,
  Controls,
  ReactFlow,
  type Connection,
  type Edge as FlowEdge,
  type Node as FlowNode,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";

import type { DagNode, FinancialCausalDAG } from "../../types/dag";
import { createEdge, fetchEdgeEffects, updateGoal, updateNode } from "../../api/client";
import { layoutDagNodes, unconnectedNodeIds } from "../../lib/layout";
import type { Mode } from "../../lib/mode";
import { DagNodeCard, type DagFlowNodeData } from "./DagNodeCard";
import { SectionLabelNode } from "./SectionLabelNode";
import { AnimatedDashedEdge, type DagFlowEdgeData } from "./AnimatedDashedEdge";
import { Legend } from "./Legend";
import { DetailPanel } from "./DetailPanel";
import { RightPanel, type RightPanelTab } from "./RightPanel";
import { TopStrip } from "./TopStrip";
import { ChatTuning } from "../ChatTuning/ChatTuning";
import { TemplateLibraryPanel } from "../TemplateLibrary/TemplateLibraryPanel";
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
  const [rightPanelTab, setRightPanelTab] = useState<RightPanelTab>("detail");
  const [isChatOpen, setIsChatOpen] = useState(false);
  const [isTemplatePanelOpen, setIsTemplatePanelOpen] = useState(false);
  const [isIrPanelOpen, setIsIrPanelOpen] = useState(false);
  const [isEffectPanelOpen, setIsEffectPanelOpen] = useState(false);
  const [isWhatIfPanelOpen, setIsWhatIfPanelOpen] = useState(false);
  const [mode, setMode] = useState<Mode>("discovery");
  const [edgeEffects, setEdgeEffects] = useState<Record<string, number>>({});
  const [whatIfResults, setWhatIfResults] = useState<Record<string, number>>({});
  const [selectedPeriod, setSelectedPeriod] = useState<string | undefined>(
    initialDag.available_periods?.[initialDag.available_periods.length - 1]
  );
  const { pushLogEntry } = useReasoningLog();

  const isTuningLocked = dag.tuning_state?.status === "locked";

  // テンプレート適用等でDAGそのものが差し替わったら、新しいDAGの最新期に追従する
  useEffect(() => {
    setSelectedPeriod(dag.available_periods?.[dag.available_periods.length - 1]);
  }, [dag.id]);

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
        periodValue: selectedPeriod ? n.values_by_period?.[selectedPeriod] : undefined,
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
  }, [dag.nodes, positions, candidateIds, mode, whatIfResults, selectedPeriod]);

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

  async function handleUpdateNode(
    nodeId: string,
    patch: Partial<Pick<DagNode, "values_by_period" | "unit" | "description" | "source_citation">>
  ) {
    const updated = await updateNode(nodeId, patch);
    setDag(updated);
  }

  function handleGoalChange(goal: string) {
    setDag((prev) => ({ ...prev, goal })); // 入力中の見た目を即時反映
    updateGoal(goal).catch((e) => console.error("ゴールの更新に失敗しました", e));
  }

  function handleTemplateApplied(newDag: FinancialCausalDAG) {
    setDag(newDag);
    setIsTemplatePanelOpen(false);
    setIsChatOpen(true); // そのまま対話チューニングへ
  }

  function handleRequestUploadFromLibrary() {
    setIsTemplatePanelOpen(false);
    setIsIrPanelOpen(true);
  }

  function handleIrDataMerged(newDag: FinancialCausalDAG) {
    setDag(newDag);
    setIsIrPanelOpen(false);
    setIsChatOpen(true); // 未接続ノードの接続をAIにアシストしてもらう
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
        onOpenTemplateLibrary={() => setIsTemplatePanelOpen(true)}
        onOpenIrData={() => setIsIrPanelOpen(true)}
        onOpenEffectEstimation={() => setIsEffectPanelOpen(true)}
        onOpenWhatIf={() => setIsWhatIfPanelOpen(true)}
        onToggleMode={handleToggleMode}
      />
      <div style={{ flex: 1, minWidth: 0, display: "flex", flexDirection: "column" }}>
        <TopStrip
          goal={dag.goal ?? ""}
          onGoalChange={handleGoalChange}
          mode={mode}
          company={dag.company}
          availablePeriods={dag.available_periods}
          selectedPeriod={selectedPeriod}
          onPeriodChange={setSelectedPeriod}
        />
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
                setRightPanelTab("detail");
              }}
              onEdgeClick={(_, edge) => {
                setSelectedEdgeId(edge.id);
                setSelectedNodeId(null);
                setRightPanelTab("detail");
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
          <RightPanel
            activeTab={rightPanelTab}
            onTabChange={setRightPanelTab}
            mode={mode}
            detail={
              <DetailPanel
                node={selectedNode}
                edge={selectedEdge}
                nodeById={nodeById}
                edges={dag.edges}
                edgeEffects={edgeEffects}
                availablePeriods={dag.available_periods ?? []}
                onClose={() => {
                  setSelectedNodeId(null);
                  setSelectedEdgeId(null);
                }}
                onUpdateNode={handleUpdateNode}
              />
            }
            log={<ReasoningLog />}
          />
        </div>
        {isChatOpen && (
          <ChatTuning dag={dag} setDag={setDag} onClose={() => setIsChatOpen(false)} />
        )}
      </div>
      {isTemplatePanelOpen && (
        <TemplateLibraryPanel
          onApplied={handleTemplateApplied}
          onRequestUpload={handleRequestUploadFromLibrary}
          onClose={() => setIsTemplatePanelOpen(false)}
        />
      )}
      {isIrPanelOpen && (
        <IrDataPanel onMerged={handleIrDataMerged} onClose={() => setIsIrPanelOpen(false)} />
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

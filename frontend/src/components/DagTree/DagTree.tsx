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
import { createEdge, updateGoal } from "../../api/client";
import { layoutDagNodes, unconnectedNodeIds } from "../../lib/layout";
import { edgeColorVar, edgeDashArray } from "../../lib/colors";
import { DagNodeCard, type DagFlowNodeData } from "./DagNodeCard";
import { SectionLabelNode } from "./SectionLabelNode";
import { Legend } from "./Legend";
import { DetailPanel } from "./DetailPanel";
import { GoalBar } from "./GoalBar";
import { ChatTuning } from "../ChatTuning/ChatTuning";

const nodeTypes = { dagNode: DagNodeCard, sectionLabel: SectionLabelNode };

export function DagTree({ dag: initialDag }: { dag: FinancialCausalDAG }) {
  const [dag, setDag] = useState(initialDag);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [selectedEdgeId, setSelectedEdgeId] = useState<string | null>(null);
  const [isChatOpen, setIsChatOpen] = useState(false);

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
      data: { dagNode: n, isCandidate: candidateIds.has(n.id) },
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
  }, [dag.nodes, positions, candidateIds]);

  const flowEdges: FlowEdge[] = useMemo(
    () =>
      dag.edges
        // 却下(rejected)されたエッジは対話履歴には残すが、ツリー上には描画しない
        .filter((e) => e.status !== "rejected")
        .map((e) => ({
          id: e.id,
          source: e.source_node_id,
          target: e.target_node_id,
          style: {
            stroke: edgeColorVar(e.sign),
            strokeWidth: 2,
            strokeDasharray: edgeDashArray(e.status),
          },
          selected: e.id === selectedEdgeId,
        })),
    [dag.edges, selectedEdgeId]
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

  return (
    <div style={{ width: "100%", height: "100%", display: "flex", flexDirection: "column" }}>
      <GoalBar
        goal={dag.goal ?? ""}
        onChange={handleGoalChange}
        onToggleChat={() => setIsChatOpen((v) => !v)}
        isChatOpen={isChatOpen}
      />
      <div style={{ flex: 1, minHeight: 0, display: "flex" }}>
        <Legend />
        <div style={{ flex: 1, minWidth: 0, position: "relative" }}>
          <ReactFlow
            nodes={flowNodes}
            edges={flowEdges}
            nodeTypes={nodeTypes}
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
        <DetailPanel
          node={selectedNode}
          edge={selectedEdge}
          nodeById={nodeById}
          onClose={() => {
            setSelectedNodeId(null);
            setSelectedEdgeId(null);
          }}
        />
      </div>
      {isChatOpen && (
        <ChatTuning dag={dag} setDag={setDag} onClose={() => setIsChatOpen(false)} />
      )}
    </div>
  );
}

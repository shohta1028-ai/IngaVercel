import { useMemo, useState } from "react";
import {
  Background,
  Controls,
  ReactFlow,
  type Edge as FlowEdge,
  type Node as FlowNode,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";

import type { FinancialCausalDAG } from "../../types/dag";
import { layoutDagNodes } from "../../lib/layout";
import { edgeColorVar, edgeDashArray } from "../../lib/colors";
import { DagNodeCard, type DagFlowNodeData } from "./DagNodeCard";
import { Legend } from "./Legend";
import { DetailPanel } from "./DetailPanel";

const nodeTypes = { dagNode: DagNodeCard };

export function DagTree({ dag }: { dag: FinancialCausalDAG }) {
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [selectedEdgeId, setSelectedEdgeId] = useState<string | null>(null);

  const nodeById = useMemo(
    () => Object.fromEntries(dag.nodes.map((n) => [n.id, n])),
    [dag.nodes]
  );

  const positions = useMemo(
    () => layoutDagNodes(dag.nodes, dag.edges),
    [dag.nodes, dag.edges]
  );

  const flowNodes: FlowNode<DagFlowNodeData>[] = useMemo(
    () =>
      dag.nodes.map((n) => ({
        id: n.id,
        type: "dagNode",
        position: positions[n.id],
        data: { dagNode: n },
      })),
    [dag.nodes, positions]
  );

  const flowEdges: FlowEdge[] = useMemo(
    () =>
      dag.edges.map((e) => ({
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

  return (
    <div style={{ width: "100%", height: "100%", display: "flex" }}>
      <Legend />
      <div style={{ flex: 1, minWidth: 0, position: "relative" }}>
        <ReactFlow
          nodes={flowNodes}
          edges={flowEdges}
          nodeTypes={nodeTypes}
          onNodeClick={(_, node) => {
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
  );
}

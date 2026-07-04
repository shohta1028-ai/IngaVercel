import { Handle, Position, type NodeProps } from "@xyflow/react";
import { CATEGORY_COLOR_VAR } from "../../lib/colors";
import type { DagNode } from "../../types/dag";

export type DagFlowNodeData = { dagNode: DagNode; isCandidate?: boolean };

const handleStyle = {
  width: 8,
  height: 8,
  background: "var(--text-muted)",
  border: "2px solid var(--surface-1)",
};

export function DagNodeCard({ data }: NodeProps) {
  const { dagNode, isCandidate } = data as unknown as DagFlowNodeData;

  return (
    <div
      style={{
        borderLeft: `4px solid ${CATEGORY_COLOR_VAR[dagNode.category]}`,
        border: isCandidate ? "1px dashed var(--text-muted)" : undefined,
        borderLeftWidth: 4,
        borderLeftColor: CATEGORY_COLOR_VAR[dagNode.category],
        background: "var(--surface-1)",
        color: "var(--text-primary)",
        borderRadius: 6,
        padding: "8px 12px",
        minWidth: 160,
        boxShadow: "0 1px 2px var(--border-hairline)",
        fontSize: 13,
      }}
      title={isCandidate ? "ドラッグしてツリーのノードに紐付けできます" : undefined}
    >
      <Handle type="target" position={Position.Left} style={handleStyle} />
      <div style={{ fontWeight: 600 }}>{dagNode.label}</div>
      <div style={{ color: "var(--text-muted)", fontSize: 11, marginTop: 2 }}>
        {dagNode.unit ?? " "}
      </div>
      <Handle type="source" position={Position.Right} style={handleStyle} />
    </div>
  );
}

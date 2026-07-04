import { Handle, Position, type NodeProps } from "@xyflow/react";
import { CATEGORY_COLOR_VAR } from "../../lib/colors";
import type { DagNode } from "../../types/dag";

export type DagFlowNodeData = { dagNode: DagNode };

export function DagNodeCard({ data }: NodeProps) {
  const { dagNode } = data as unknown as DagFlowNodeData;

  return (
    <div
      style={{
        borderLeft: `4px solid ${CATEGORY_COLOR_VAR[dagNode.category]}`,
        background: "var(--surface-1)",
        color: "var(--text-primary)",
        borderRadius: 6,
        padding: "8px 12px",
        minWidth: 160,
        boxShadow: "0 1px 2px var(--border-hairline)",
        fontSize: 13,
      }}
    >
      <Handle type="target" position={Position.Left} style={{ opacity: 0 }} />
      <div style={{ fontWeight: 600 }}>{dagNode.label}</div>
      <div style={{ color: "var(--text-muted)", fontSize: 11, marginTop: 2 }}>
        {dagNode.unit ?? " "}
      </div>
      <Handle type="source" position={Position.Right} style={{ opacity: 0 }} />
    </div>
  );
}

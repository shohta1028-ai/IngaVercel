import type { DagEdge, DagNode } from "../types/dag";

const COLUMN_WIDTH = 260;
const ROW_HEIGHT = 110;

/** ノードをトポロジカルな層（原因→結果の深さ）に基づいて配置する簡易レイアウト */
export function layoutDagNodes(
  nodes: DagNode[],
  edges: DagEdge[]
): Record<string, { x: number; y: number }> {
  const incoming = new Map<string, string[]>();
  nodes.forEach((n) => incoming.set(n.id, []));
  edges.forEach((e) => {
    incoming.get(e.target_node_id)?.push(e.source_node_id);
  });

  const depth = new Map<string, number>();
  const resolving = new Set<string>();

  function depthOf(id: string): number {
    if (depth.has(id)) return depth.get(id)!;
    if (resolving.has(id)) return 0; // サイクル保護
    resolving.add(id);
    const parents = incoming.get(id) ?? [];
    const d = parents.length === 0 ? 0 : Math.max(...parents.map(depthOf)) + 1;
    depth.set(id, d);
    resolving.delete(id);
    return d;
  }

  nodes.forEach((n) => depthOf(n.id));

  const rowCountByColumn = new Map<number, number>();
  const positions: Record<string, { x: number; y: number }> = {};

  nodes.forEach((n) => {
    const col = depth.get(n.id) ?? 0;
    const row = rowCountByColumn.get(col) ?? 0;
    rowCountByColumn.set(col, row + 1);
    positions[n.id] = { x: col * COLUMN_WIDTH, y: row * ROW_HEIGHT };
  });

  return positions;
}

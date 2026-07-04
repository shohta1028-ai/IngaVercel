import type { DagEdge, DagNode } from "../types/dag";

const COLUMN_WIDTH = 260;
const ROW_HEIGHT = 110;
const CANDIDATE_COLUMN_GAP = 1; // 未接続候補ノードは本体ツリーの右に1列分あけて配置

/** どのエッジにも接続されていないノードのID一覧（Phase4マージ候補の抽出用） */
export function unconnectedNodeIds(nodes: DagNode[], edges: DagEdge[]): string[] {
  const connected = new Set<string>();
  edges.forEach((e) => {
    connected.add(e.source_node_id);
    connected.add(e.target_node_id);
  });
  return nodes.filter((n) => !connected.has(n.id)).map((n) => n.id);
}

/**
 * ノードをトポロジカルな層（原因→結果の深さ）に基づいて配置する簡易レイアウト。
 * どのエッジにも繋がっていない「未接続の候補ノード」は、本体ツリーの右側に
 * 独立した列として配置し、ドラッグ操作での紐付け対象であることを視覚的に示す。
 */
export function layoutDagNodes(
  nodes: DagNode[],
  edges: DagEdge[]
): Record<string, { x: number; y: number }> {
  const candidateIds = new Set(unconnectedNodeIds(nodes, edges));
  const connectedNodes = nodes.filter((n) => !candidateIds.has(n.id));

  const incoming = new Map<string, string[]>();
  connectedNodes.forEach((n) => incoming.set(n.id, []));
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

  connectedNodes.forEach((n) => depthOf(n.id));

  const rowCountByColumn = new Map<number, number>();
  const positions: Record<string, { x: number; y: number }> = {};

  connectedNodes.forEach((n) => {
    const col = depth.get(n.id) ?? 0;
    const row = rowCountByColumn.get(col) ?? 0;
    rowCountByColumn.set(col, row + 1);
    positions[n.id] = { x: col * COLUMN_WIDTH, y: row * ROW_HEIGHT };
  });

  const maxDepth = Math.max(0, ...Array.from(depth.values()));
  const candidateColumn = maxDepth + 1 + CANDIDATE_COLUMN_GAP;
  nodes
    .filter((n) => candidateIds.has(n.id))
    .forEach((n, i) => {
      positions[n.id] = { x: candidateColumn * COLUMN_WIDTH, y: i * ROW_HEIGHT };
    });

  return positions;
}

import { useState } from "react";
import { EdgeLabelRenderer, getBezierPath, type EdgeProps } from "@xyflow/react";
import { edgeColorVar } from "../../lib/colors";
import type { Mode } from "../../lib/mode";

export type DagFlowEdgeData = {
  sign: "positive" | "negative" | "ambiguous";
  status: "ai_proposed" | "user_confirmed" | "user_modified" | "rejected";
  rationale?: string | null;
  mode: Mode;
  effectValue?: number;
};

function formatEffect(value: number): string {
  const sign = value > 0 ? "+" : "";
  return `${sign}${value.toFixed(2)}`;
}

export function AnimatedDashedEdge(props: EdgeProps) {
  const { sourceX, sourceY, targetX, targetY, sourcePosition, targetPosition, selected } = props;
  const data = props.data as unknown as DagFlowEdgeData;
  const [hovered, setHovered] = useState(false);

  const [path, labelX, labelY] = getBezierPath({
    sourceX,
    sourceY,
    sourcePosition,
    targetX,
    targetY,
    targetPosition,
  });

  const isDiscoveryHypothesis = data.mode === "discovery" && data.status === "ai_proposed";
  const isInferenceConfirmed =
    data.mode === "inference" && (data.status === "user_confirmed" || data.status === "user_modified");

  const stroke = edgeColorVar(data.sign);
  const strokeWidth = isInferenceConfirmed ? 3 : 2;

  const tooltipText = isDiscoveryHypothesis
    ? `【因果探索】AIが仮説として提示中${data.rationale ? `：${data.rationale}` : ""}`
    : isInferenceConfirmed
      ? `【因果推論】DoWhy (backdoor.linear_regression) による推定効果${
          data.effectValue !== undefined ? `: ${formatEffect(data.effectValue)}` : "（未計算）"
        }`
      : data.rationale ?? undefined;

  return (
    <>
      <path
        d={path}
        fill="none"
        stroke={stroke}
        strokeWidth={strokeWidth}
        strokeDasharray={isDiscoveryHypothesis ? "6 4" : undefined}
        style={{
          animation: isDiscoveryHypothesis ? "inga-dash-flow 0.9s linear infinite" : undefined,
          opacity: selected ? 1 : 0.92,
        }}
      />
      {/* ホバー判定用の広い透明パス */}
      <path
        d={path}
        fill="none"
        stroke="transparent"
        strokeWidth={16}
        onMouseEnter={() => setHovered(true)}
        onMouseLeave={() => setHovered(false)}
      />
      <EdgeLabelRenderer>
        {isInferenceConfirmed && data.effectValue !== undefined && (
          <div
            style={{
              position: "absolute",
              transform: `translate(-50%, -50%) translate(${labelX}px, ${labelY}px)`,
              fontSize: 11,
              fontWeight: 700,
              padding: "1px 6px",
              borderRadius: 999,
              background: "var(--surface-1)",
              border: `1px solid ${stroke}`,
              color: stroke,
              pointerEvents: "none",
            }}
          >
            {formatEffect(data.effectValue)}
          </div>
        )}
        {hovered && tooltipText && (
          <div
            style={{
              position: "absolute",
              transform: `translate(-50%, calc(-100% - 14px)) translate(${labelX}px, ${labelY}px)`,
              fontSize: 12,
              lineHeight: 1.5,
              padding: "8px 10px",
              borderRadius: 6,
              width: 260,
              background: "var(--surface-1)",
              color: "var(--text-primary)",
              border: "1px solid var(--border-hairline)",
              boxShadow: "0 4px 12px rgba(0,0,0,0.15)",
              pointerEvents: "none",
              zIndex: 200,
            }}
          >
            {tooltipText}
          </div>
        )}
      </EdgeLabelRenderer>
    </>
  );
}

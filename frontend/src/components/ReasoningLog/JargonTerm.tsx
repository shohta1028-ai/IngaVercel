import { Tooltip } from "../Tooltip";

export function JargonTerm({ term, explanation }: { term: string; explanation: string }) {
  return (
    <Tooltip content={<><strong>{term}</strong><br />{explanation}</>} placement="top">
      <span
        style={{
          display: "inline-flex",
          alignItems: "center",
          justifyContent: "center",
          width: 14,
          height: 14,
          borderRadius: "50%",
          border: "1px solid var(--text-muted)",
          color: "var(--text-muted)",
          fontSize: 9,
          fontWeight: 700,
          cursor: "default",
          marginLeft: 3,
        }}
      >
        ?
      </span>
    </Tooltip>
  );
}

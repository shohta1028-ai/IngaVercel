export function SectionLabelNode({ data }: { data: { text: string } }) {
  return (
    <div
      style={{
        color: "var(--text-muted)",
        fontSize: 12,
        fontWeight: 600,
        whiteSpace: "nowrap",
      }}
    >
      {data.text}
    </div>
  );
}

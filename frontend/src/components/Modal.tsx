import type { ReactNode } from "react";

export function Modal({
  title,
  onClose,
  children,
  width = 480,
}: {
  title: string;
  onClose: () => void;
  children: ReactNode;
  width?: number;
}) {
  return (
    <div
      onClick={onClose}
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(0, 0, 0, 0.4)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 100,
      }}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          width,
          maxWidth: "90vw",
          maxHeight: "80vh",
          overflowY: "auto",
          background: "var(--surface-1)",
          color: "var(--text-primary)",
          borderRadius: 10,
          boxShadow: "0 8px 24px rgba(0,0,0,0.3)",
        }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            padding: "14px 18px",
            borderBottom: "1px solid var(--border-hairline)",
          }}
        >
          <div style={{ fontWeight: 600, fontSize: 14 }}>{title}</div>
          <button
            onClick={onClose}
            aria-label="閉じる"
            style={{
              border: "none",
              background: "none",
              color: "var(--text-muted)",
              fontSize: 16,
              cursor: "pointer",
            }}
          >
            ×
          </button>
        </div>
        <div style={{ padding: 18 }}>{children}</div>
      </div>
    </div>
  );
}

import { useState } from "react";
import type { ReactNode } from "react";

// 軽量なホバー/フォーカスポップオーバー。サイドバーのラベル表示や、
// エッジ・専門用語の説明表示に共通で使う。
export function Tooltip({
  content,
  placement = "right",
  children,
}: {
  content: ReactNode;
  placement?: "right" | "top";
  children: ReactNode;
}) {
  const [visible, setVisible] = useState(false);

  const positionStyle: React.CSSProperties =
    placement === "right"
      ? { left: "calc(100% + 8px)", top: "50%", transform: "translateY(-50%)" }
      : { bottom: "calc(100% + 8px)", left: "50%", transform: "translateX(-50%)" };

  return (
    <span
      style={{ position: "relative", display: "inline-flex" }}
      onMouseEnter={() => setVisible(true)}
      onMouseLeave={() => setVisible(false)}
      onFocus={() => setVisible(true)}
      onBlur={() => setVisible(false)}
    >
      {children}
      {visible && (
        <span
          role="tooltip"
          style={{
            position: "absolute",
            zIndex: 200,
            ...positionStyle,
            background: "var(--surface-1)",
            color: "var(--text-primary)",
            border: "1px solid var(--border-hairline)",
            borderRadius: 6,
            padding: "6px 10px",
            fontSize: 12,
            lineHeight: 1.5,
            whiteSpace: "normal",
            width: 240,
            boxShadow: "0 4px 12px rgba(0,0,0,0.15)",
            pointerEvents: "none",
          }}
        >
          {content}
        </span>
      )}
    </span>
  );
}

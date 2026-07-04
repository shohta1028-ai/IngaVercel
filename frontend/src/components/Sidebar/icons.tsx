// 軽量な自前インラインSVGアイコン（追加ライブラリ不要）。
// すべてstroke="currentColor"で、呼び出し側のcolorスタイルを継承する。

type IconProps = { size?: number };

const base = (size: number) => ({
  width: size,
  height: size,
  viewBox: "0 0 24 24",
  fill: "none" as const,
  stroke: "currentColor",
  strokeWidth: 1.8,
  strokeLinecap: "round" as const,
  strokeLinejoin: "round" as const,
});

export function TemplateIcon({ size = 20 }: IconProps) {
  return (
    <svg {...base(size)}>
      <rect x="3.5" y="3.5" width="7" height="7" rx="1.2" />
      <rect x="13.5" y="3.5" width="7" height="7" rx="1.2" />
      <rect x="3.5" y="13.5" width="7" height="7" rx="1.2" />
      <rect x="13.5" y="13.5" width="7" height="7" rx="1.2" />
    </svg>
  );
}

export function IrDataIcon({ size = 20 }: IconProps) {
  return (
    <svg {...base(size)}>
      <path d="M6 3.5h8l4 4v13a1 1 0 0 1-1 1H6a1 1 0 0 1-1-1v-16a1 1 0 0 1 1-1Z" />
      <path d="M14 3.5v4h4" />
      <path d="M12 12v6M9 15l3-3 3 3" />
    </svg>
  );
}

export function ChatIcon({ size = 20 }: IconProps) {
  return (
    <svg {...base(size)}>
      <path d="M4 5.5h16v11H9l-4 3.5v-3.5H4v-11Z" />
      <path d="M8 9.5h8M8 13h5" />
    </svg>
  );
}

export function EffectIcon({ size = 20 }: IconProps) {
  return (
    <svg {...base(size)}>
      <circle cx="12" cy="12" r="8" />
      <circle cx="12" cy="12" r="4" />
      <circle cx="12" cy="12" r="0.6" fill="currentColor" />
    </svg>
  );
}

export function SliderIcon({ size = 20 }: IconProps) {
  return (
    <svg {...base(size)}>
      <path d="M4 7h9M17 7h3M4 17h3M9 17h11" />
      <circle cx="14" cy="7" r="2.2" />
      <circle cx="7" cy="17" r="2.2" />
    </svg>
  );
}

export function ModeSwapIcon({ size = 20 }: IconProps) {
  return (
    <svg {...base(size)}>
      <path d="M6 8h11l-3-3M18 16H7l3 3" />
    </svg>
  );
}

export function GoalIcon({ size = 20 }: IconProps) {
  return (
    <svg {...base(size)}>
      <circle cx="12" cy="12" r="8.5" />
      <circle cx="12" cy="12" r="5" />
      <circle cx="12" cy="12" r="1.4" fill="currentColor" />
    </svg>
  );
}

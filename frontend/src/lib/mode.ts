// 因果探索モード(構造発見)と因果推論モード(効果シミュレーション)を
// 切り替えるためのモード定義。背景・文字色などのテーマ(ライト/ダーク)とは
// 独立した軸で、アクセントカラー・エッジの見た目・AIログの文脈を切り替える。

export type Mode = "discovery" | "inference";

export const MODE_LABEL: Record<Mode, string> = {
  discovery: "因果探索",
  inference: "因果推論",
};

export const MODE_DESCRIPTION: Record<Mode, string> = {
  discovery: "AIが未知の因果関係を探索しています",
  inference: "確定した因果グラフを基に、影響の大きさを推論しています",
};

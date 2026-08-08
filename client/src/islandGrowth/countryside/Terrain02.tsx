import { PALETTE } from '../palette';

// terrain_01과는 다른 실루엣(더 둥글고 완만한 형태) - 같은 규칙
// (viewBox 0 0 180 160), 다른 모양.
export function Terrain02() {
  return (
    <path
      d="M 40,120 Q 30,94 62,88 Q 70,72 100,76 Q 132,70 146,96 Q 162,106 152,128 Q 156,148 108,150 Q 60,152 44,140 Q 28,136 40,120 Z"
      fill={PALETTE.terrainLight}
      stroke={PALETTE.terrainShadow}
      strokeWidth={1.5}
    />
  );
}

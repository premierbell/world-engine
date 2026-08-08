import { PALETTE } from '../palette';

// 캔버스 규칙: viewBox 0 0 180 160, 땅 모양은 대략 (32~154, 74~152)
// 범위 안 - docs/island_growth_visual.md "통일된 이미지 양식" 참고.
export function Terrain01() {
  return (
    <path
      d="M 32,128 Q 26,102 54,97 Q 60,76 92,79 Q 124,74 140,98 Q 160,104 154,128 Q 154,149 92,151 Q 28,150 32,128 Z"
      fill={PALETTE.terrainLight}
      stroke={PALETTE.terrainShadow}
      strokeWidth={1.5}
    />
  );
}

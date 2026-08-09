import { PALETTE } from '../palette';

// terrain_01/02와 같은 규칙(viewBox 0 0 180 160, 6개의 Q 곡선으로 된
// 땅 모양)이지만 위쪽 능선을 더 넓고 완만하게 잡아서(x 77~135 구간이
// 거의 평평하게 y 77~80) building anchor가 들어갈 여유 공간을 처음부터
// 넉넉하게 확보한 실루엣 - terrain_01/02의 building 겹침 버그를 겪고
// 나서 세 번째 지형은 anchor 배치를 먼저 계산하고 모양을 맞췄다.
export function Terrain03() {
  return (
    <path
      d="M 34,126 Q 26,100 60,92 Q 72,74 106,78 Q 140,72 154,98 Q 166,108 156,130 Q 158,150 100,152 Q 40,154 34,126 Z"
      fill={PALETTE.terrainLight}
      stroke={PALETTE.terrainShadow}
      strokeWidth={1.5}
    />
  );
}

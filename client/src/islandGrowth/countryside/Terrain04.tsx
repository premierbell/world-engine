import { PALETTE } from '../palette';

// terrain_02를 캔버스 폭(180) 기준으로 좌우 미러링해서 만든 네 번째
// 실루엣 - 새 곡선을 손으로 그리면 anchor(index.ts에서 재사용)가
// 땅 밖으로 삐져나올 위험이 있어서, 이미 검증된 terrain_02의 anchor
// 좌표를 그대로 미러링(x' = 180 - x)해 쓰는 쪽을 택했다. 미러링은
// "내부 점 여부"를 보존하는 변환이라 terrain_02에서 유효했던 anchor는
// 미러링된 이 지형에서도 그대로 유효하다.
export function Terrain04() {
  return (
    <path
      d="M 140,120 Q 150,94 118,88 Q 110,72 80,76 Q 48,70 34,96 Q 18,106 28,128 Q 24,148 72,150 Q 120,152 136,140 Q 152,136 140,120 Z"
      fill={PALETTE.terrainLight}
      stroke={PALETTE.terrainShadow}
      strokeWidth={1.5}
    />
  );
}

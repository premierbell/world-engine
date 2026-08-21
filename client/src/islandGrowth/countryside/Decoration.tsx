import { PALETTE } from '../palette';

// City 티어에서만 해금되는 decoration 카테고리 - Phase 2 최소 세트에는
// 없었고(문서 참고), 실사용 중 "Topic 없는 섬이 휑해 보인다"는 피드백
// 이후 nature와 함께 채워 넣었다. 팔레트 밖 색은 안 쓴다는 규칙(문서
// "통일된 이미지 양식") 그대로 지켜서 rock/roof/foliage 톤만 재사용.
// 낮은 실루엣으로 건물과 확실히 구분되게 한다(장식이 건물처럼
// 보이면 "건물=Topic" 신호가 흐려짐).
export function Well01() {
  return (
    <>
      <ellipse cx={2} cy={1} rx={8} ry={2.2} fill={PALETTE.dropShadow} />
      <rect x={-7} y={-8} width={7} height={8} rx={1.5} fill={PALETTE.rock} />
      <rect x={0} y={-8} width={7} height={8} rx={1.5} fill={PALETTE.terrainShadow} />
      <rect x={-1} y={-12} width={2} height={5} fill={PALETTE.trunk} />
    </>
  );
}

export function FlowerPot01() {
  return (
    <>
      <ellipse cx={1.5} cy={1} rx={6} ry={1.8} fill={PALETTE.dropShadow} />
      <path d="M -5,-8 L 0,-8 L -0.5,0 L -4,0 Z" fill={PALETTE.roofLight} />
      <path d="M 0,-8 L 5,-8 L 4,0 L -0.5,0 Z" fill={PALETTE.roofShadow} />
      <circle cx={-1} cy={-11} r={5} fill={PALETTE.foliageLight} />
      <circle cx={2} cy={-9.5} r={4} fill={PALETTE.foliageShadow} />
    </>
  );
}

// well_01/flower_pot_01과 다른 낮고 긴 실루엣 - 벤치. decoration
// 카테고리 종류를 하나 더한다. 다른 decoration과 마찬가지로 건물보다
// 확실히 낮게 유지한다("건물=Topic" 신호가 흐려지지 않게).
export function Bench01() {
  return (
    <>
      <ellipse cx={2} cy={1} rx={9} ry={2} fill={PALETTE.dropShadow} />
      <rect x={-8} y={-6} width={16} height={2} fill={PALETTE.infraLight} />
      <rect x={-8} y={-4} width={16} height={1.5} fill={PALETTE.infraShadow} />
      <rect x={-7} y={-4} width={1.5} height={5} fill={PALETTE.trunk} />
      <rect x={5.5} y={-4} width={1.5} height={5} fill={PALETTE.trunk} />
    </>
  );
}

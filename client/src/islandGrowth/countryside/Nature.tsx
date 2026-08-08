import { PALETTE } from '../palette';

// 좌상단 광원 2톤 음영: 잎을 두 개의 겹친 덩어리로 그려서 오른쪽
// 아래(뒤쪽)가 그림자 톤이 되게 한다. 바닥 접지점은 로컬 (0,0).
export function Tree01() {
  return (
    <>
      <ellipse cx={3} cy={1.5} rx={10} ry={3} fill={PALETTE.dropShadow} />
      <rect x={-1.5} y={-10} width={3} height={10} fill={PALETTE.trunk} />
      <circle cx={-2} cy={-19} r={11} fill={PALETTE.foliageLight} />
      <circle cx={5} cy={-15} r={9} fill={PALETTE.foliageShadow} />
    </>
  );
}

export function Rock01() {
  return (
    <>
      <ellipse cx={2} cy={1} rx={7} ry={2} fill={PALETTE.dropShadow} />
      <path d="M -7,0 Q -8,-6 -2,-8 Q 4,-10 7,-4 Q 8,0 4,1 Q -3,2 -7,0 Z" fill={PALETTE.rock} />
      <path d="M 0,-8 Q 4,-10 7,-4 Q 8,0 4,1 L 0,-1 Z" fill={PALETTE.terrainShadow} />
    </>
  );
}

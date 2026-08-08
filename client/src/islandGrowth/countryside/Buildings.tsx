import { PALETTE } from '../palette';

// 좌상단 광원 2톤 음영: 몸체/지붕을 좌우로 나눠 왼쪽은 밝은면, 오른쪽은
// 그림자면. 바닥에 공용 그림자 타원. 바닥 접지점은 로컬 (0,0).
export function HouseSmall01() {
  return (
    <>
      <ellipse cx={4} cy={2} rx={17} ry={4.5} fill={PALETTE.dropShadow} />
      <rect x={-13} y={-22} width={13} height={22} fill={PALETTE.buildingLight} />
      <rect x={0} y={-22} width={13} height={22} fill={PALETTE.buildingShadow} />
      <polygon points="-15,-22 0,-22 0,-38" fill={PALETTE.roofLight} />
      <polygon points="0,-22 15,-22 0,-38" fill={PALETTE.roofShadow} />
      <rect x={-9} y={-13} width={7} height={7} fill={PALETTE.window} />
    </>
  );
}

// 지붕 경사/창문 위치를 살짝 다르게 한 변형 - 같은 규칙, 다른 실루엣.
export function HouseSmall02() {
  return (
    <>
      <ellipse cx={4} cy={2} rx={15} ry={4} fill={PALETTE.dropShadow} />
      <rect x={-11} y={-18} width={11} height={18} fill={PALETTE.buildingLight} />
      <rect x={0} y={-18} width={11} height={18} fill={PALETTE.buildingShadow} />
      <polygon points="-13,-18 0,-18 0,-32" fill={PALETTE.roofLight} />
      <polygon points="0,-18 13,-18 0,-32" fill={PALETTE.roofShadow} />
      <rect x={-8} y={-11} width={6} height={6} fill={PALETTE.window} />
    </>
  );
}

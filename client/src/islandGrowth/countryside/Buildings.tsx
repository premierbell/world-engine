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
// large 등급 - house_small보다 넓고 높음, 굴뚝으로 실루엣에 포인트.
export function HouseLarge01() {
  return (
    <>
      <ellipse cx={6} cy={2} rx={22} ry={5.5} fill={PALETTE.dropShadow} />
      <rect x={-18} y={-28} width={18} height={28} fill={PALETTE.buildingLight} />
      <rect x={0} y={-28} width={18} height={28} fill={PALETTE.buildingShadow} />
      <polygon points="-20,-28 0,-28 0,-44" fill={PALETTE.roofLight} />
      <polygon points="0,-28 20,-28 0,-44" fill={PALETTE.roofShadow} />
      <rect x={3} y={-50} width={4} height={8} fill={PALETTE.roofShadow} />
      <rect x={-13} y={-22} width={7} height={7} fill={PALETTE.window} />
      <rect x={-13} y={-11} width={7} height={7} fill={PALETTE.window} />
    </>
  );
}

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

// building anchor 중 'small' 등급 전용 - house_small_01/02는 이름과
// 달리 size가 'medium'이라(anchor에 맞는 자산이 없었음), 실제로 더
// 작은 건물이 필요해서 추가. 굴뚝/창문 없이 몸통+지붕만으로 실루엣을
// 짧게 유지 - 다른 건물보다 낮은 anchor 자리에도 여유 있게 들어간다.
export function Cottage01() {
  return (
    <>
      <ellipse cx={3} cy={1.5} rx={12} ry={3.2} fill={PALETTE.dropShadow} />
      <rect x={-8} y={-12} width={8} height={12} fill={PALETTE.buildingLight} />
      <rect x={0} y={-12} width={8} height={12} fill={PALETTE.buildingShadow} />
      <polygon points="-10,-12 0,-12 0,-24" fill={PALETTE.roofLight} />
      <polygon points="0,-12 10,-12 0,-24" fill={PALETTE.roofShadow} />
      <rect x={-6} y={-8} width={5} height={5} fill={PALETTE.window} />
    </>
  );
}

// cottage_01과 같은 'small' 등급, 다른 디테일 - 창문 대신 문이 있는
// 작은 오두막. building 'small' anchor에 cottage_01만 반복되지
// 않게(지금까지는 선택지가 1개뿐이라 모든 섬에서 항상 같은 건물이
// 나왔다) 종류를 하나 더한다.
export function HouseSmall03() {
  return (
    <>
      <ellipse cx={3} cy={1.5} rx={12} ry={3.2} fill={PALETTE.dropShadow} />
      <rect x={-8} y={-13} width={8} height={13} fill={PALETTE.buildingLight} />
      <rect x={0} y={-13} width={8} height={13} fill={PALETTE.buildingShadow} />
      <polygon points="-10,-13 0,-13 0,-25" fill={PALETTE.roofLight} />
      <polygon points="0,-13 10,-13 0,-25" fill={PALETTE.roofShadow} />
      <rect x={-3} y={-7} width={5} height={7} fill={PALETTE.trunk} />
    </>
  );
}

// house_large_01(굴뚝 + 세로로 쌓인 창문 2개)과 다른 실루엣 - 폭이
// 넓고 낮은 "곳간/회관" 형태, 창문 2개를 가로로 나란히 배치하고
// 문을 뒀다. building 'large' anchor에 house_large_01만 반복되지
// 않게(지금까지는 선택지가 1개뿐이었다) 종류를 하나 더한다. 폭/높이
// 모두 house_large_01의 clearance 여유 안에 들어오게 맞췄다.
export function HouseLarge02() {
  return (
    <>
      <ellipse cx={6} cy={2} rx={22} ry={5.5} fill={PALETTE.dropShadow} />
      <rect x={-18} y={-22} width={18} height={22} fill={PALETTE.buildingLight} />
      <rect x={0} y={-22} width={18} height={22} fill={PALETTE.buildingShadow} />
      <polygon points="-20,-22 0,-22 0,-36" fill={PALETTE.roofLight} />
      <polygon points="0,-22 20,-22 0,-36" fill={PALETTE.roofShadow} />
      <rect x={-14} y={-15} width={6} height={6} fill={PALETTE.window} />
      <rect x={-6} y={-15} width={6} height={6} fill={PALETTE.window} />
      <rect x={-4} y={-9} width={7} height={9} fill={PALETTE.buildingShadow} />
    </>
  );
}

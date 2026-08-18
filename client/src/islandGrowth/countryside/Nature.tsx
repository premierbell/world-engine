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

// tree_01(둥근 활엽수)과 다른 실루엣 - 침엽수(층이 진 삼각형). 같은
// 좌상단 광원 규칙: 각 층을 좌(밝은면)/우(그림자면)로 나눔.
export function Tree02() {
  return (
    <>
      <ellipse cx={2} cy={1} rx={8} ry={2.5} fill={PALETTE.dropShadow} />
      <rect x={-1.2} y={-8} width={2.4} height={8} fill={PALETTE.trunk} />
      <polygon points="-9,-8 0,-8 0,-19" fill={PALETTE.foliageLight} />
      <polygon points="0,-8 9,-8 0,-19" fill={PALETTE.foliageShadow} />
      <polygon points="-6,-15 0,-15 0,-26" fill={PALETTE.foliageLight} />
      <polygon points="0,-15 6,-15 0,-26" fill={PALETTE.foliageShadow} />
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

// rock_01과 같은 'small' 등급이지만 초록 계열이라 nature 카테고리
// small anchor에 rock만 반복되지 않게 종류를 하나 더한다 - tree보다
// 훨씬 낮은 실루엣(둥근 잎 덩어리만, 줄기 없음)이라 어떤 자리에도
// 부담 없이 들어간다.
export function Bush01() {
  return (
    <>
      <ellipse cx={2} cy={1} rx={8} ry={2.2} fill={PALETTE.dropShadow} />
      <circle cx={-2} cy={-7} r={7} fill={PALETTE.foliageLight} />
      <circle cx={4} cy={-5.5} r={6} fill={PALETTE.foliageShadow} />
    </>
  );
}

// tree_01(활엽수)/tree_02(침엽수)와 또 다른 실루엣 - 휘어진 줄기 +
// 위쪽에서 사방으로 뻗는 야자잎. 섬/해안 테마에 어울리는 세 번째
// 나무 종류. 'medium' 등급, 줄기는 stroke 곡선이라 다른 나무들의
// 사각 줄기와도 시각적으로 구분된다.
export function Tree03() {
  return (
    <>
      <ellipse cx={2} cy={1.5} rx={9} ry={2.5} fill={PALETTE.dropShadow} />
      <path d="M 0,0 Q -3,-10 1,-20" stroke={PALETTE.trunk} strokeWidth={2.4} fill="none" />
      <path d="M 1,-20 Q -10,-24 -14,-16" fill={PALETTE.foliageShadow} />
      <path d="M 1,-20 Q -6,-28 -4,-34" fill={PALETTE.foliageShadow} />
      <path d="M 1,-20 Q 1,-30 1,-36" fill={PALETTE.foliageLight} />
      <path d="M 1,-20 Q 8,-27 10,-33" fill={PALETTE.foliageLight} />
      <path d="M 1,-20 Q 10,-23 15,-15" fill={PALETTE.foliageLight} />
    </>
  );
}

// rock_01(둥근 바위 하나)과 다른 구성 - 큰 바위 옆에 작은 바위를
// 곁들인 무리. nature 'small' anchor에 rock_01만 반복되지 않게
// 종류를 하나 더한다.
export function Rock02() {
  return (
    <>
      <ellipse cx={2} cy={1} rx={9} ry={2.2} fill={PALETTE.dropShadow} />
      <path d="M -8,0 Q -9,-7 -2,-9 Q 5,-11 8,-4 Q 9,0 5,1 Q -4,2 -8,0 Z" fill={PALETTE.rock} />
      <path d="M 0,-9 Q 5,-11 8,-4 Q 9,0 5,1 L 0,-2 Z" fill={PALETTE.terrainShadow} />
      <path d="M 6,1 Q 5,-4 10,-5 Q 14,-6 15,-2 Q 15,1 12,2 Q 8,2 6,1 Z" fill={PALETTE.rock} />
      <path d="M 10,-5 Q 14,-6 15,-2 Q 15,1 12,2 L 10,-1 Z" fill={PALETTE.terrainShadow} />
    </>
  );
}

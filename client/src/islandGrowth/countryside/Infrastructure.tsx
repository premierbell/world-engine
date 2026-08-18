import { PALETTE } from '../palette';

// 길 - 바닥에 붙어있는 요소라 입체감보다 방향감이 중요. 살짝 기울인
// 띠 모양 + 가운데 그림자 라인.
export function Road01() {
  return (
    <g transform="rotate(-8)">
      <rect x={-16} y={-3} width={32} height={7} rx={3} fill={PALETTE.infraLight} />
      <rect x={-16} y={1} width={32} height={3} rx={1.5} fill={PALETTE.infraShadow} />
    </g>
  );
}

// 부두 - anchor 지점에서 오른쪽(물 쪽으로 가정)으로 뻗어나가는 판자 +
// 기둥 3개. 접지점은 anchor와 만나는 왼쪽 끝(로컬 (0,0)).
export function Dock01() {
  return (
    <>
      <rect x={0} y={-3} width={26} height={6} fill={PALETTE.infraLight} />
      <rect x={0} y={0} width={26} height={3} fill={PALETTE.infraShadow} />
      <rect x={4} y={-5} width={2} height={10} fill={PALETTE.trunk} />
      <rect x={14} y={-5} width={2} height={10} fill={PALETTE.trunk} />
      <rect x={22} y={-5} width={2} height={10} fill={PALETTE.trunk} />
    </>
  );
}

// 울타리 - road_01/dock_01과 다른 실루엣(짧은 말뚝 여러 개 + 가로대
// 2줄). 방향성이 없어서(회전 없이도 자연스러움) road_01과 달리 그대로
// 둔다. infrastructure 카테고리 종류를 하나 더한다.
export function Fence01() {
  return (
    <>
      <rect x={-14} y={-10} width={2} height={10} fill={PALETTE.trunk} />
      <rect x={-4} y={-10} width={2} height={10} fill={PALETTE.trunk} />
      <rect x={6} y={-10} width={2} height={10} fill={PALETTE.trunk} />
      <rect x={-15} y={-8} width={23} height={2} fill={PALETTE.infraShadow} />
      <rect x={-15} y={-3} width={23} height={2} fill={PALETTE.infraShadow} />
    </>
  );
}

// docs/island_growth_visual.md "통일된 이미지 양식" - 이 팔레트 밖의
// 색은 새 에셋에 안 쓴다. 오브젝트 계열은 밝은면/그림자면 쌍으로
// 정의되어 있다 - 좌상단 광원 기준 2톤 음영 규칙과 세트.
export const PALETTE = {
  terrainLight: '#d9c9a3',
  terrainShadow: '#8a7a54',
  buildingLight: '#4a5a68',
  buildingShadow: '#34424e',
  roofLight: '#b5715a',
  roofShadow: '#8a5646',
  window: '#e8dcc0',
  foliageLight: '#7a9b6e',
  foliageShadow: '#5c7d52',
  trunk: '#6b5842',
  rock: '#9c9184',
  infraLight: '#c4b896',
  infraShadow: '#8a7048',
  dropShadow: 'rgba(43,38,32,0.16)',
} as const;

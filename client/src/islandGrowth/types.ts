import type { ComponentType } from 'react';

// docs/island_growth_visual.md 참고 - 섬을 완성된 그림 하나로 그리는 게
// 아니라, 작은 에셋(지형/나무/건물/도로)을 anchor point에 조합해서
// 만든다. 이 파일은 그 조합에 쓰이는 타입만 정의한다.

export type AssetCategory = 'nature' | 'building' | 'infrastructure' | 'decoration';
export type AssetSize = 'small' | 'medium' | 'large';

// 지형 위에 올라가는 오브젝트 하나(나무/건물/길 등). Component는 바닥
// 접지점이 로컬 (0,0)인 SVG 조각(<g> 없이 그 안의 내용물)만 반환한다 -
// 배치할 때 호출부가 <g transform="translate(x,y)">로 감싼다.
export interface ObjectAsset {
  id: string; // '{theme}/{category}_{name}' 예: 'countryside/nature_tree_01'
  category: AssetCategory;
  size: AssetSize;
  Component: ComponentType;
}

export interface TerrainAnchor {
  x: number;
  y: number;
  size: AssetSize;
  category: AssetCategory;
}

export interface TerrainDefinition {
  id: string; // 'countryside/terrain_01'
  Component: ComponentType; // 땅 모양만 그림(오브젝트 없이)
  anchors: TerrainAnchor[];
}

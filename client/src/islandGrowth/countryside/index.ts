import { Terrain01 } from './Terrain01';
import { Rock01, Tree01 } from './Nature';
import { HouseSmall01, HouseSmall02 } from './Buildings';
import type { AssetCategory, ObjectAsset, TerrainDefinition } from '../types';

// 컴포넌트 파일은 컴포넌트만 export하고(Fast Refresh 때문에 lint가
// 요구함), 메타데이터(id/category/size/anchors)는 여기서 감싼다.

const terrain01: TerrainDefinition = {
  id: 'countryside/terrain_01',
  Component: Terrain01,
  // 자리는 실제 필요한 최대치보다 넉넉하게 - 특정 티어에서 자리가
  // 모자라 에셋이 겹치는 일이 없게 한다.
  anchors: [
    { x: 56, y: 100, size: 'medium', category: 'nature' },
    { x: 130, y: 104, size: 'small', category: 'nature' },
    { x: 44, y: 118, size: 'small', category: 'nature' },
    { x: 90, y: 98, size: 'large', category: 'building' },
    { x: 66, y: 104, size: 'medium', category: 'building' },
    { x: 112, y: 100, size: 'medium', category: 'building' },
    { x: 138, y: 120, size: 'small', category: 'building' },
    { x: 90, y: 130, size: 'small', category: 'infrastructure' },
    { x: 60, y: 132, size: 'small', category: 'infrastructure' },
    { x: 100, y: 140, size: 'small', category: 'decoration' },
  ],
};

const tree01: ObjectAsset = {
  id: 'countryside/nature_tree_01',
  category: 'nature',
  size: 'medium',
  Component: Tree01,
};

const rock01: ObjectAsset = {
  id: 'countryside/nature_rock_01',
  category: 'nature',
  size: 'small',
  Component: Rock01,
};

const houseSmall01: ObjectAsset = {
  id: 'countryside/building_house_small_01',
  category: 'building',
  size: 'medium',
  Component: HouseSmall01,
};

const houseSmall02: ObjectAsset = {
  id: 'countryside/building_house_small_02',
  category: 'building',
  size: 'medium',
  Component: HouseSmall02,
};

// Phase 2 시작 세트(docs/island_growth_visual.md) - terrain 1개 +
// nature 2개 + building 2개. infrastructure/decoration은 다음에 추가.
export const countrysideTerrains: TerrainDefinition[] = [terrain01];

export const countrysideAssetsByCategory: Partial<Record<AssetCategory, ObjectAsset[]>> = {
  nature: [tree01, rock01],
  building: [houseSmall01, houseSmall02],
};

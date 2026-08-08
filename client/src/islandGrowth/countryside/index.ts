import { Terrain01 } from './Terrain01';
import { Terrain02 } from './Terrain02';
import { Rock01, Tree01, Tree02 } from './Nature';
import { HouseLarge01, HouseSmall01, HouseSmall02 } from './Buildings';
import { Dock01, Road01 } from './Infrastructure';
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

const terrain02: TerrainDefinition = {
  id: 'countryside/terrain_02',
  Component: Terrain02,
  anchors: [
    { x: 70, y: 96, size: 'medium', category: 'nature' },
    { x: 130, y: 108, size: 'small', category: 'nature' },
    { x: 50, y: 122, size: 'small', category: 'nature' },
    { x: 100, y: 90, size: 'large', category: 'building' },
    { x: 76, y: 110, size: 'medium', category: 'building' },
    { x: 124, y: 88, size: 'medium', category: 'building' },
    { x: 144, y: 112, size: 'small', category: 'building' },
    { x: 96, y: 132, size: 'small', category: 'infrastructure' },
    { x: 66, y: 136, size: 'small', category: 'infrastructure' },
    { x: 116, y: 140, size: 'small', category: 'decoration' },
  ],
};

const tree01: ObjectAsset = {
  id: 'countryside/nature_tree_01',
  category: 'nature',
  size: 'medium',
  Component: Tree01,
};

const tree02: ObjectAsset = {
  id: 'countryside/nature_tree_02',
  category: 'nature',
  size: 'medium',
  Component: Tree02,
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

const houseLarge01: ObjectAsset = {
  id: 'countryside/building_house_large_01',
  category: 'building',
  size: 'large',
  Component: HouseLarge01,
};

const road01: ObjectAsset = {
  id: 'countryside/infra_road_01',
  category: 'infrastructure',
  size: 'small',
  Component: Road01,
};

const dock01: ObjectAsset = {
  id: 'countryside/infra_dock_01',
  category: 'infrastructure',
  size: 'small',
  Component: Dock01,
};

// Phase 2 최소 세트 완성(docs/island_growth_visual.md) - terrain 2개,
// nature 3개, building 3개, infrastructure 2개.
export const countrysideTerrains: TerrainDefinition[] = [terrain01, terrain02];

export const countrysideAssetsByCategory: Partial<Record<AssetCategory, ObjectAsset[]>> = {
  nature: [tree01, tree02, rock01],
  building: [houseSmall01, houseSmall02, houseLarge01],
  infrastructure: [road01, dock01],
};

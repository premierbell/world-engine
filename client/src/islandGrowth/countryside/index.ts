import { Terrain01 } from './Terrain01';
import { Terrain02 } from './Terrain02';
import { Terrain03 } from './Terrain03';
import { Bush01, Rock01, Tree01, Tree02 } from './Nature';
import { Cottage01, HouseLarge01, HouseSmall01, HouseSmall02 } from './Buildings';
import { Dock01, Road01 } from './Infrastructure';
import { FlowerPot01, Well01 } from './Decoration';
import type { AssetCategory, ObjectAsset, TerrainDefinition } from '../types';

// 컴포넌트 파일은 컴포넌트만 export하고(Fast Refresh 때문에 lint가
// 요구함), 메타데이터(id/category/size/anchors)는 여기서 감싼다.

// building anchor 좌표는 각 지형의 SVG 곡선(top/bottom boundary)을
// 직접 계산해서 잡았다 - 가장 키가 큰 건물(house_large_01, anchor
// 기준 위로 50px, 굴뚝 포함)이 지형 위쪽 경계 밖으로 안 튀어나오게
// 여유(8px)까지 포함해서 역산한 값. 이전엔 anchor가 지형 위쪽 경계에
// 너무 가까워서 건물 지붕/굴뚝이 섬 밖(배경)으로 튀어나와 보이는
// 문제가 있었다.
const terrain01: TerrainDefinition = {
  id: 'countryside/terrain_01',
  Component: Terrain01,
  // 자리는 실제 필요한 최대치보다 넉넉하게 - 특정 티어에서 자리가
  // 모자라 에셋이 겹치는 일이 없게 한다.
  anchors: [
    { x: 56, y: 100, size: 'medium', category: 'nature' },
    { x: 130, y: 104, size: 'small', category: 'nature' },
    { x: 44, y: 118, size: 'small', category: 'nature' },
    // 아래 2개(nature) + decoration 1개는 Topic 없는(건물 0개) 섬이
    // 휑해 보인다는 실사용 피드백 이후 추가 - 티어가 원래도 nature를
    // 최대 5~6개까지 요청했는데 anchor가 3개뿐이라 실제로는 못 채우고
    // 있었다. building들의 밑동(base) 아래, 지형 바닥 쪽 여유 공간에
    // 배치해서 건물과 안 겹치게 했다.
    { x: 70, y: 143, size: 'small', category: 'nature' },
    { x: 125, y: 142, size: 'medium', category: 'nature' },
    { x: 90, y: 137, size: 'large', category: 'building' },
    { x: 60, y: 134, size: 'medium', category: 'building' },
    { x: 118, y: 128, size: 'medium', category: 'building' },
    { x: 136, y: 130, size: 'small', category: 'building' },
    { x: 40, y: 128, size: 'small', category: 'infrastructure' },
    { x: 150, y: 116, size: 'small', category: 'infrastructure' },
    { x: 92, y: 148, size: 'small', category: 'decoration' },
    { x: 45, y: 140, size: 'small', category: 'decoration' },
  ],
};

const terrain02: TerrainDefinition = {
  id: 'countryside/terrain_02',
  Component: Terrain02,
  anchors: [
    { x: 70, y: 96, size: 'medium', category: 'nature' },
    { x: 130, y: 108, size: 'small', category: 'nature' },
    { x: 50, y: 122, size: 'small', category: 'nature' },
    // terrain_01과 같은 이유(휑함 보완) - building 밑동 아래 여유
    // 공간에 배치.
    { x: 80, y: 141, size: 'small', category: 'nature' },
    { x: 110, y: 139, size: 'medium', category: 'nature' },
    { x: 95, y: 136, size: 'large', category: 'building' },
    { x: 64, y: 134, size: 'medium', category: 'building' },
    { x: 122, y: 126, size: 'medium', category: 'building' },
    { x: 140, y: 122, size: 'small', category: 'building' },
    { x: 45, y: 134, size: 'small', category: 'infrastructure' },
    { x: 150, y: 108, size: 'small', category: 'infrastructure' },
    { x: 100, y: 148, size: 'small', category: 'decoration' },
    { x: 55, y: 138, size: 'small', category: 'decoration' },
  ],
};

// terrain_01/02보다 위쪽 능선이 넓고 완만해서 building anchor 여유가
// 더 크다(위 주석 참고) - 세 번째 테마 지형, 실루엣도 더 길쭉하게
// 달라서 섬마다 확실히 다른 모양이 나온다.
const terrain03: TerrainDefinition = {
  id: 'countryside/terrain_03',
  Component: Terrain03,
  anchors: [
    { x: 56, y: 132, size: 'medium', category: 'nature' },
    { x: 40, y: 132, size: 'small', category: 'nature' },
    { x: 115, y: 98, size: 'small', category: 'nature' },
    // terrain_01/02와 같은 이유(휑함 보완).
    { x: 65, y: 140, size: 'small', category: 'nature' },
    { x: 135, y: 135, size: 'medium', category: 'nature' },
    { x: 100, y: 138, size: 'large', category: 'building' },
    { x: 72, y: 130, size: 'medium', category: 'building' },
    { x: 128, y: 126, size: 'medium', category: 'building' },
    { x: 148, y: 126, size: 'small', category: 'building' },
    { x: 85, y: 148, size: 'small', category: 'infrastructure' },
    { x: 45, y: 118, size: 'small', category: 'infrastructure' },
    { x: 100, y: 148, size: 'small', category: 'decoration' },
    { x: 118, y: 145, size: 'small', category: 'decoration' },
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

const bush01: ObjectAsset = {
  id: 'countryside/nature_bush_01',
  category: 'nature',
  size: 'small',
  Component: Bush01,
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

const cottage01: ObjectAsset = {
  id: 'countryside/building_cottage_01',
  category: 'building',
  size: 'small',
  Component: Cottage01,
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

const well01: ObjectAsset = {
  id: 'countryside/decoration_well_01',
  category: 'decoration',
  size: 'small',
  Component: Well01,
};

const flowerPot01: ObjectAsset = {
  id: 'countryside/decoration_flower_pot_01',
  category: 'decoration',
  size: 'small',
  Component: FlowerPot01,
};

// Phase 2 최소 세트(terrain 2 + nature 3 + building 3 + infrastructure 2)에
// terrain_03/cottage_01(작은 건물)/bush_01(작은 나무)을 더함 -
// docs/island_growth_visual.md 참고. decoration(well_01/flower_pot_01)은
// Phase 2 최소 세트엔 없었고, City 티어가 약속만 하고 실제로는 채운
// 적 없던 카테고리라 실사용 피드백 이후 추가.
export const countrysideTerrains: TerrainDefinition[] = [terrain01, terrain02, terrain03];

export const countrysideAssetsByCategory: Partial<Record<AssetCategory, ObjectAsset[]>> = {
  nature: [tree01, tree02, rock01, bush01],
  building: [houseSmall01, houseSmall02, houseLarge01, cottage01],
  infrastructure: [road01, dock01],
  decoration: [well01, flowerPot01],
};

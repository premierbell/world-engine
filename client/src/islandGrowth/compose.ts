import { seededRandom } from './random';
import type { AssetCategory, ObjectAsset, TerrainAnchor, TerrainDefinition } from './types';

export type GrowthTier = 'SEED' | 'ISLET' | 'VILLAGE' | 'CITY';

// docs/island_growth_visual.md "에셋 분류와 티어별 구성" - 카테고리
// 자체가 티어마다 해금된다. 값은 가안(실제 에셋 조합 보고 조정).
const TIER_COUNTS: Record<GrowthTier, Partial<Record<AssetCategory, [min: number, max: number]>>> = {
  SEED: { nature: [1, 2] },
  ISLET: { nature: [2, 3], building: [1, 1] },
  VILLAGE: { nature: [3, 5], building: [2, 3], infrastructure: [1, 1] },
  CITY: { nature: [4, 6], building: [4, 6], infrastructure: [2, 2], decoration: [1, 2] },
};

export interface PlacedObject {
  asset: ObjectAsset;
  x: number;
  y: number;
}

export interface ComposedIsland {
  terrain: TerrainDefinition;
  objects: PlacedObject[];
}

// islandId를 시드로 지형/오브젝트를 결정론적으로 고른다 - 같은 섬은
// 항상 같은 결과, 다른 섬은 서로 다른 결과. docs/island_growth_visual.md
// "Deterministic 선택" 참고.
export function composeIsland(
  islandId: number,
  tier: GrowthTier,
  terrains: TerrainDefinition[],
  assetsByCategory: Partial<Record<AssetCategory, ObjectAsset[]>>,
): ComposedIsland {
  const rand = seededRandom(islandId);
  const terrain = terrains[Math.floor(rand() * terrains.length)];
  const counts = TIER_COUNTS[tier];

  const anchorsByCategory = groupAnchorsByCategory(terrain.anchors);
  for (const category of Object.keys(anchorsByCategory) as AssetCategory[]) {
    shuffle(anchorsByCategory[category]!, rand);
  }

  const objects: PlacedObject[] = [];
  for (const category of Object.keys(counts) as AssetCategory[]) {
    const [min, max] = counts[category]!;
    const count = min + Math.floor(rand() * (max - min + 1));
    const anchors = (anchorsByCategory[category] ?? []).slice(0, count);
    const pool = assetsByCategory[category] ?? [];
    if (pool.length === 0) {
      continue;
    }
    for (const anchor of anchors) {
      const asset = pool[Math.floor(rand() * pool.length)];
      objects.push({ asset, x: anchor.x, y: anchor.y });
    }
  }

  return { terrain, objects };
}

function groupAnchorsByCategory(anchors: TerrainAnchor[]): Partial<Record<AssetCategory, TerrainAnchor[]>> {
  const grouped: Partial<Record<AssetCategory, TerrainAnchor[]>> = {};
  for (const anchor of anchors) {
    (grouped[anchor.category] ??= []).push(anchor);
  }
  return grouped;
}

function shuffle<T>(items: T[], rand: () => number): void {
  for (let i = items.length - 1; i > 0; i--) {
    const j = Math.floor(rand() * (i + 1));
    [items[i], items[j]] = [items[j], items[i]];
  }
}

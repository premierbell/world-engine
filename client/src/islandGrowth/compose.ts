import { seededRandom } from './random';
import type { AssetCategory, ObjectAsset, TerrainAnchor, TerrainDefinition } from './types';

export type GrowthTier = 'SEED' | 'ISLET' | 'VILLAGE' | 'CITY';

// B안(docs/island_growth_visual.md "B안") 적용 이후 building은 여기 없다 -
// 실제 Topic 개수가 대신 정한다(아래 composeIsland 참고). nature/
// infrastructure/decoration은 여전히 티어가 해금/개수를 정한다(가안 -
// 실제 에셋 조합 보고 조정).
const TIER_COUNTS: Record<GrowthTier, Partial<Record<Exclude<AssetCategory, 'building'>, [min: number, max: number]>>> = {
  SEED: { nature: [1, 2] },
  ISLET: { nature: [2, 3] },
  VILLAGE: { nature: [3, 5], infrastructure: [1, 1] },
  CITY: { nature: [4, 6], infrastructure: [2, 2], decoration: [1, 2] },
};

// building anchor의 순서를 섞는 시드를 장식(nature/infrastructure/
// decoration) 쪽 시드와 완전히 분리하기 위한 오프셋 - 나중에 장식
// 로직(개수/카테고리)이 바뀌어도 이미 배정된 Topic의 건물 자리는 절대
// 안 흔들리게 하기 위함. docs/island_growth_visual.md "B안" 참고.
const BUILDING_ANCHOR_SEED_OFFSET = 1_000_003;

export interface PlacedObject {
  asset: ObjectAsset;
  x: number;
  y: number;
}

export interface ComposedIsland {
  terrain: TerrainDefinition;
  objects: PlacedObject[];
}

// islandId를 시드로 지형/장식을 결정론적으로 고르고, topicIds(생성
// 순서로 이미 정렬돼서 온다)로 building을 채운다. 같은 섬은 항상 같은
// 결과, Topic이 늘어나도 기존에 배정된 건물은 안 바뀐다.
// docs/island_growth_visual.md "Deterministic 선택"/"B안" 참고.
export function composeIsland(
  islandId: number,
  tier: GrowthTier,
  topicIds: number[],
  terrains: TerrainDefinition[],
  assetsByCategory: Partial<Record<AssetCategory, ObjectAsset[]>>,
): ComposedIsland {
  const rand = seededRandom(islandId);
  const terrain = terrains[Math.floor(rand() * terrains.length)];
  const anchorsByCategory = groupAnchorsByCategory(terrain.anchors);

  const objects: PlacedObject[] = [];

  // 장식(nature/infrastructure/decoration) - 섬 전체 시드 공유, 티어가
  // 개수를 정함(기존 로직 그대로).
  const decorationCounts = TIER_COUNTS[tier];
  for (const category of Object.keys(decorationCounts) as (keyof typeof decorationCounts)[]) {
    const anchors = anchorsByCategory[category];
    if (!anchors) {
      continue;
    }
    shuffle(anchors, rand);
    const [min, max] = decorationCounts[category]!;
    const count = min + Math.floor(rand() * (max - min + 1));
    const pool = assetsByCategory[category] ?? [];
    if (pool.length === 0) {
      continue;
    }
    for (const anchor of anchors.slice(0, count)) {
      const asset = pool[Math.floor(rand() * pool.length)];
      objects.push({ asset, x: anchor.x, y: anchor.y });
    }
  }

  // building - B안: Topic이 개수/자리를 정한다. anchor 순서는 장식과
  // 별개의 독립 시드로 섞어서, 장식 로직이 나중에 바뀌어도 이미 배정된
  // Topic의 자리가 흔들리지 않게 한다("한 번 배정된 anchor는 안
  // 바뀐다" 원칙).
  const buildingAnchors = [...(anchorsByCategory.building ?? [])];
  shuffle(buildingAnchors, seededRandom(islandId + BUILDING_ANCHOR_SEED_OFFSET));

  const buildingPool = assetsByCategory.building ?? [];
  if (buildingPool.length > 0) {
    topicIds.forEach((topicId, index) => {
      const anchor = buildingAnchors[index];
      if (!anchor) {
        // Topic이 지형의 building anchor 수보다 많아진 경우 - 지금은
        // 그냥 자리 없는 만큼 생략한다(docs/island_growth_visual.md
        // "B안" 참고, 실제로 이런 섬이 생기면 그때 anchor를 늘린다).
        return;
      }
      // 건물 종류는 이 Topic 고유의 시드로 고른다 - 다른 Topic이
      // 추가/변경돼도 이 건물의 모양은 안 바뀐다. anchor.size와 같은
      // 크기의 건물만 후보로 좁힌다 - large 건물(지붕/굴뚝까지 anchor
      // 기준 50px)이 좁은 자리에 배정돼 지형 밖으로 튀어나오는 걸
      // 막기 위함(같은 크기가 없으면 전체 풀로 폴백해서 항상 뭔가는
      // 배정되게 한다).
      const topicRand = seededRandom(topicId);
      const sizedPool = buildingPool.filter((asset) => asset.size === anchor.size);
      const pool = sizedPool.length > 0 ? sizedPool : buildingPool;
      const asset = pool[Math.floor(topicRand() * pool.length)];
      objects.push({ asset, x: anchor.x, y: anchor.y });
    });
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

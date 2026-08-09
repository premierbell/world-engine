import { countrysideAssetsByCategory, countrysideTerrains } from './countryside';
import { composeIsland } from './compose';
import type { GrowthTier } from './compose';

interface ComposedIslandViewProps {
  islandId: number;
  tier: GrowthTier;
  topicIds?: number[];
  size?: number;
}

// Phase 3 조합 테스트용 미리보기 컴포넌트 - 실제 렌더링은 MapView.tsx가
// 한다(Phase 4). docs/island_growth_visual.md 참고.
export function ComposedIslandView({ islandId, tier, topicIds = [], size = 180 }: ComposedIslandViewProps) {
  const composed = composeIsland(islandId, tier, topicIds, countrysideTerrains, countrysideAssetsByCategory);
  const Terrain = composed.terrain.Component;

  return (
    <svg viewBox="0 0 180 160" width={size} height={(size * 160) / 180}>
      <Terrain />
      {composed.objects.map((placed, index) => {
        const Asset = placed.asset.Component;
        return (
          <g key={index} transform={`translate(${placed.x}, ${placed.y})`}>
            <Asset />
          </g>
        );
      })}
    </svg>
  );
}

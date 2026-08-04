import type { IslandSummary } from '../types/island';

interface MapViewProps {
  islands: IslandSummary[];
  onIslandClick: (islandId: number) => void;
  selectedIslandId?: number | null;
}

const SIZE = 600;
const CENTER = SIZE / 2;
const MIN_CIRCLE_RADIUS = 18;
const MAX_CIRCLE_RADIUS = 50;
const ZOOM_LEVEL = 2.5;

export function MapView({ islands, onIslandClick, selectedIslandId = null }: MapViewProps) {
  if (islands.length === 0) {
    return null;
  }

  const maxScrapCount = Math.max(...islands.map((island) => island.scrapCount), 1);
  const selectedIsland = islands.find((island) => island.id === selectedIslandId) ?? null;

  // 카메라: 선택된 섬이 있으면 그 섬의 화면 좌표(CENTER + island.x/y)가
  // 뷰포트 중앙에 오도록 확대+평행이동한다. 섬 좌표(x,y) 자체는 전혀
  // 안 바뀐다 - 화면에 어떻게 그릴지(카메라)만 바뀐다.
  // docs/map_home_redesign.md "World Unit vs 화면 좌표" 참고.
  const zoom = selectedIsland ? ZOOM_LEVEL : 1;
  const targetX = selectedIsland ? CENTER + selectedIsland.x : 0;
  const targetY = selectedIsland ? CENTER + selectedIsland.y : 0;
  const translateX = selectedIsland ? CENTER - zoom * targetX : 0;
  const translateY = selectedIsland ? CENTER - zoom * targetY : 0;

  return (
    <svg className="map-view" viewBox={`0 0 ${SIZE} ${SIZE}`} role="img" aria-label="Island 지도">
      <g
        className="map-camera"
        style={{ transform: `translate(${translateX}px, ${translateY}px) scale(${zoom})`, transformOrigin: '0 0' }}
      >
        {islands.map((island) => {
          const x = CENTER + island.x;
          const y = CENTER + island.y;
          const r =
            MIN_CIRCLE_RADIUS + (island.scrapCount / maxScrapCount) * (MAX_CIRCLE_RADIUS - MIN_CIRCLE_RADIUS);

          return (
            <g
              key={island.id}
              className="map-island"
              transform={`translate(${x}, ${y})`}
              onClick={() => onIslandClick(island.id)}
            >
              <circle r={r} />
              {Array.from({ length: island.topicCount }).map((_, topicIndex) => {
                const dotAngle = (2 * Math.PI * topicIndex) / island.topicCount;
                const dotX = (r - 6) * Math.cos(dotAngle);
                const dotY = (r - 6) * Math.sin(dotAngle);
                return <circle key={topicIndex} cx={dotX} cy={dotY} r={2.5} className="map-island-topic-dot" />;
              })}
              <text y={r + 16} textAnchor="middle">
                {island.name} ({island.scrapCount})
              </text>
            </g>
          );
        })}
      </g>
    </svg>
  );
}

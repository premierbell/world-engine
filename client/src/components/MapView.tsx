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
const FIT_PADDING = 150; // World Unit - 섬 원+라벨이 화면 가장자리에 안 붙도록 여백

export function MapView({ islands, onIslandClick, selectedIslandId = null }: MapViewProps) {
  if (islands.length === 0) {
    return null;
  }

  const maxScrapCount = Math.max(...islands.map((island) => island.scrapCount), 1);
  const selectedIsland = islands.find((island) => island.id === selectedIslandId) ?? null;

  // 카메라: 화면에 어떻게 보여줄지(줌/이동)만 결정한다 - 섬의 World
  // Unit 좌표(x,y) 자체는 전혀 안 바뀐다. 섬을 선택하면 그 섬으로
  // 확대하고, 선택이 없으면(홈 화면) 모든 섬이 화면 안에 들어오도록
  // 자동으로 축소한다(fit-to-bounds) - 세계가 계속 커져도 항상 전체를
  // 볼 수 있어야 한다. docs/map_home_redesign.md 참고.
  let zoom: number;
  let targetX: number;
  let targetY: number;

  if (selectedIsland) {
    zoom = ZOOM_LEVEL;
    targetX = CENTER + selectedIsland.x;
    targetY = CENTER + selectedIsland.y;
  } else {
    const minX = Math.min(...islands.map((island) => island.x));
    const maxX = Math.max(...islands.map((island) => island.x));
    const minY = Math.min(...islands.map((island) => island.y));
    const maxY = Math.max(...islands.map((island) => island.y));

    const width = maxX - minX + FIT_PADDING * 2;
    const height = maxY - minY + FIT_PADDING * 2;

    zoom = Math.min(SIZE / width, SIZE / height);
    targetX = CENTER + (minX + maxX) / 2;
    targetY = CENTER + (minY + maxY) / 2;
  }

  const translateX = CENTER - zoom * targetX;
  const translateY = CENTER - zoom * targetY;

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

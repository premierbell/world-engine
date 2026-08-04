import { useNavigate } from 'react-router-dom';
import type { IslandSummary } from '../types/island';

interface MapViewProps {
  islands: IslandSummary[];
}

const SIZE = 600;
const CENTER = SIZE / 2;
const MIN_CIRCLE_RADIUS = 18;
const MAX_CIRCLE_RADIUS = 50;

export function MapView({ islands }: MapViewProps) {
  const navigate = useNavigate();

  if (islands.length === 0) {
    return null;
  }

  const maxScrapCount = Math.max(...islands.map((island) => island.scrapCount), 1);

  return (
    <svg className="map-view" viewBox={`0 0 ${SIZE} ${SIZE}`} role="img" aria-label="Island 지도">
      {islands.map((island) => {
        // island.x/y는 서버(MapCoordinateService)가 주는 World Unit 좌표 -
        // 화면 좌표로는 CENTER만큼 평행이동해서 그린다(줌/팬은 아직 없음, zoom=1 고정).
        const x = CENTER + island.x;
        const y = CENTER + island.y;
        const r =
          MIN_CIRCLE_RADIUS + (island.scrapCount / maxScrapCount) * (MAX_CIRCLE_RADIUS - MIN_CIRCLE_RADIUS);

        return (
          <g
            key={island.id}
            className="map-island"
            transform={`translate(${x}, ${y})`}
            onClick={() => navigate(`/islands/${island.id}`)}
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
    </svg>
  );
}

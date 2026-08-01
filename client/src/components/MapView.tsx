import { useNavigate } from 'react-router-dom';
import type { IslandSummary } from '../types/island';

interface MapViewProps {
  islands: IslandSummary[];
}

const SIZE = 600;
const CENTER = SIZE / 2;
const PLACEMENT_RADIUS = 220;
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
      {islands.map((island, index) => {
        const angle = (2 * Math.PI * index) / islands.length;
        const x = CENTER + PLACEMENT_RADIUS * Math.cos(angle);
        const y = CENTER + PLACEMENT_RADIUS * Math.sin(angle);
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
            <text y={r + 16} textAnchor="middle">
              {island.name} ({island.scrapCount})
            </text>
          </g>
        );
      })}
    </svg>
  );
}

import type { TopicSummary } from '../types/topic';

interface TopicMapViewProps {
  topics: TopicSummary[];
}

const SIZE = 320;
const CENTER = SIZE / 2;
const PLACEMENT_RADIUS = 100;
const MIN_CIRCLE_RADIUS = 12;
const MAX_CIRCLE_RADIUS = 32;

export function TopicMapView({ topics }: TopicMapViewProps) {
  if (topics.length === 0) {
    return null;
  }

  const maxScrapCount = Math.max(...topics.map((topic) => topic.scraps.length), 1);

  const handleClick = (topicId: number) => {
    document.getElementById(`topic-${topicId}`)?.scrollIntoView({ behavior: 'smooth', block: 'center' });
  };

  return (
    <svg
      className="map-view map-view-topics"
      viewBox={`0 0 ${SIZE} ${SIZE}`}
      role="img"
      aria-label="Topic 지도"
    >
      {topics.map((topic, index) => {
        const angle = (2 * Math.PI * index) / topics.length;
        const x = CENTER + PLACEMENT_RADIUS * Math.cos(angle);
        const y = CENTER + PLACEMENT_RADIUS * Math.sin(angle);
        const r =
          MIN_CIRCLE_RADIUS + (topic.scraps.length / maxScrapCount) * (MAX_CIRCLE_RADIUS - MIN_CIRCLE_RADIUS);

        return (
          <g
            key={topic.id}
            className="map-island"
            transform={`translate(${x}, ${y})`}
            onClick={() => handleClick(topic.id)}
          >
            <circle r={r} />
            <text y={r + 14} textAnchor="middle">
              {topic.name} ({topic.scraps.length})
            </text>
          </g>
        );
      })}
    </svg>
  );
}

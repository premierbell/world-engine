import type { TopicSummary } from '../types/topic';

interface TopicListProps {
  topics: TopicSummary[];
}

export function TopicList({ topics }: TopicListProps) {
  if (topics.length === 0) {
    return null;
  }

  return (
    <div id="island-topics">
      {topics.map((topic) => (
        <div key={topic.id} className="topic-candidate-card">
          <div className="topic-candidate-heading">
            📍 {topic.name} ({topic.scraps.length})
          </div>
          <ul className="entity-list">
            {topic.scraps.map((scrap) => (
              <li key={scrap.id}>{scrap.title ?? scrap.url}</li>
            ))}
          </ul>
        </div>
      ))}
    </div>
  );
}

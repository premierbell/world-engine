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
        <div key={topic.id} id={`topic-${topic.id}`} className="topic-candidate-card">
          <div className="topic-candidate-heading">
            📍 {topic.name} ({topic.scraps.length})
          </div>
          <ul className="entity-list">
            {topic.scraps.map((scrap) => (
              <li key={scrap.id}>
                <a href={scrap.url} target="_blank" rel="noopener noreferrer">
                  {scrap.title ?? scrap.url}
                </a>
              </li>
            ))}
          </ul>
        </div>
      ))}
    </div>
  );
}

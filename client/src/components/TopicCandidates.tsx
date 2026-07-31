import type { ExistingTopicMatch, TopicCandidateResponse } from '../types/topic';

interface TopicCandidatesProps {
  status: string;
  data: TopicCandidateResponse | null;
  isGenerating: boolean;
  onGenerate: () => void;
  onFillCandidate: (scrapIds: number[]) => void;
  onAddToExistingTopic: (topicId: number, scrapIds: number[]) => void;
}

interface TopicGroup {
  topicName: string;
  matches: ExistingTopicMatch[];
}

export function TopicCandidates({
  status,
  data,
  isGenerating,
  onGenerate,
  onFillCandidate,
  onAddToExistingTopic,
}: TopicCandidatesProps) {
  const matchesByTopic = new Map<number, TopicGroup>();
  data?.existingTopicMatches.forEach((match) => {
    const group = matchesByTopic.get(match.topicId);
    if (group) {
      group.matches.push(match);
    } else {
      matchesByTopic.set(match.topicId, { topicName: match.topicName, matches: [match] });
    }
  });

  const isEmpty =
    data && data.existingTopicMatches.length === 0 && data.groups.length === 0 && data.ungrouped.length === 0;

  return (
    <>
      <button type="button" onClick={onGenerate} disabled={isGenerating}>
        Topic 후보 찾기
      </button>
      <p className="result">{status}</p>
      <div>
        {isEmpty && <p className="result">스크랩이 없어요.</p>}

        {Array.from(matchesByTopic.entries()).map(([topicId, { topicName, matches }]) => {
          const bestScore = Math.max(...matches.map((match) => match.score));
          return (
            <div key={topicId} className="topic-candidate-card">
              <div className="topic-candidate-heading">
                📍 {topicName} 에 추가 제안 (최고 점수 {bestScore.toFixed(2)})
              </div>
              <ul className="entity-list">
                {matches.map((match) => (
                  <li key={match.scrap.id}>
                    {match.scrap.title ?? match.scrap.url} ({match.score.toFixed(2)}, 근거:{' '}
                    {match.matchedAgainst.title ?? match.matchedAgainst.url})
                  </li>
                ))}
              </ul>
              <button
                type="button"
                className="fill-candidate-button"
                onClick={() => onAddToExistingTopic(topicId, matches.map((match) => match.scrap.id))}
              >
                이 Topic에 추가
              </button>
            </div>
          );
        })}

        {data?.groups.map((group, index) => (
          <div key={index} className="topic-candidate-card">
            <div className="topic-candidate-heading">
              후보 {index + 1} (평균 {group.averageScore.toFixed(2)} / 최소 {group.minimumScore.toFixed(2)})
            </div>
            <ul className="entity-list">
              {group.scraps.map((scrap) => (
                <li key={scrap.id}>{scrap.title ?? scrap.url}</li>
              ))}
            </ul>
            <button
              type="button"
              className="fill-candidate-button"
              onClick={() => onFillCandidate(group.scraps.map((scrap) => scrap.id))}
            >
              이 후보 추가
            </button>
          </div>
        ))}

        {data && data.ungrouped.length > 0 && (
          <>
            <div className="topic-candidate-heading">미분류 ({data.ungrouped.length})</div>
            <ul className="entity-list">
              {data.ungrouped.map((scrap) => (
                <li key={scrap.id}>{scrap.title ?? scrap.url}</li>
              ))}
            </ul>
          </>
        )}
      </div>
    </>
  );
}

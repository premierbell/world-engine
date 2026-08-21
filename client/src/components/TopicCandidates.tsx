import { useEffect, useState } from 'react';
import { useSuggestTopicName } from '../hooks/useSuggestTopicName';
import type { ExistingTopicMatch, TopicCandidateResponse } from '../types/topic';

interface TopicCandidatesProps {
  status: string;
  data: TopicCandidateResponse | null;
  isGenerating: boolean;
  onGenerate: () => void;
  onFillCandidate: (scrapIds: number[], name?: string) => void;
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
  // "후보 1/2/3" 대신 AI가 지어준 이름을 보여주는 건 그룹 단위로만,
  // 버튼을 눌렀을 때만 호출한다(생성될 때마다 그룹 수만큼 자동 호출하면
  // 후보 찾기 자체가 이미 느린데 그 위에 대기시간+비용이 더 붙는다 -
  // suggest-name 엔드포인트는 Topic 이름 AI 제안 기능에서 이미 만든 걸
  // 그대로 재사용).
  const [suggestedNames, setSuggestedNames] = useState<Record<number, string>>({});
  const [suggestingIndex, setSuggestingIndex] = useState<number | null>(null);
  const suggestNameMutation = useSuggestTopicName();

  useEffect(() => {
    setSuggestedNames({});
    setSuggestingIndex(null);
  }, [data]);

  const handleSuggestGroupName = (index: number, scrapIds: number[]) => {
    setSuggestingIndex(index);
    suggestNameMutation.mutate(scrapIds, {
      onSuccess: (result) => {
        setSuggestedNames((prev) => ({ ...prev, [index]: result.name }));
        setSuggestingIndex(null);
      },
      onError: () => {
        setSuggestingIndex(null);
      },
    });
  };

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

        {data?.groups.map((group, index) => {
          const scrapIds = group.scraps.map((scrap) => scrap.id);
          const suggestedName = suggestedNames[index];
          return (
            <div key={index} className="topic-candidate-card">
              <div className="topic-candidate-heading">
                <span>
                  {suggestedName ? `🏷️ ${suggestedName}` : `후보 ${index + 1}`} (평균 {group.averageScore.toFixed(2)}{' '}
                  / 최소 {group.minimumScore.toFixed(2)})
                </span>
                <button
                  type="button"
                  className="suggest-name-button"
                  onClick={() => handleSuggestGroupName(index, scrapIds)}
                  disabled={suggestingIndex === index}
                >
                  {suggestingIndex === index ? '...' : suggestedName ? '다시 제안' : '이름 제안'}
                </button>
              </div>
              <ul className="entity-list">
                {group.scraps.map((scrap) => (
                  <li key={scrap.id}>{scrap.title ?? scrap.url}</li>
                ))}
              </ul>
              <button
                type="button"
                className="fill-candidate-button"
                onClick={() => onFillCandidate(scrapIds, suggestedName)}
              >
                이 후보 추가
              </button>
            </div>
          );
        })}

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

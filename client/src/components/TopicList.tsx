import { useState } from 'react';
import type { TopicSummary } from '../types/topic';
import { useDeleteTopic } from '../hooks/useDeleteTopic';
import { useRenameTopic } from '../hooks/useRenameTopic';

interface TopicListProps {
  topics: TopicSummary[];
  islandId: number;
}

export function TopicList({ topics, islandId }: TopicListProps) {
  if (topics.length === 0) {
    return null;
  }

  const sortedTopics = topics.slice().sort((a, b) => b.id - a.id);

  return (
    <div id="island-topics">
      {sortedTopics.map((topic) => (
        <TopicCard key={topic.id} topic={topic} islandId={islandId} />
      ))}
    </div>
  );
}

// island_growth_visual.md의 "건물"과 짝인 실제 관리 카드 - 이름 수정/
// 삭제도 Island 삭제와 같은 원칙(스크랩은 안 지우고 topicId만 비움).
function TopicCard({ topic, islandId }: { topic: TopicSummary; islandId: number }) {
  const renameMutation = useRenameTopic(islandId);
  const deleteMutation = useDeleteTopic(islandId);

  const [isEditingName, setIsEditingName] = useState(false);
  const [nameDraft, setNameDraft] = useState(topic.name);
  const [isConfirmingDelete, setIsConfirmingDelete] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');

  const startEditing = () => {
    setNameDraft(topic.name);
    setIsEditingName(true);
    setErrorMessage('');
  };

  const handleRename = () => {
    const name = nameDraft.trim();
    if (!name || name === topic.name) {
      setIsEditingName(false);
      return;
    }
    renameMutation.mutate(
      { topicId: topic.id, name },
      {
        onSuccess: () => setIsEditingName(false),
        onError: (err) => setErrorMessage(`이름 변경 실패: ${err.message}`),
      },
    );
  };

  const handleDelete = () => {
    deleteMutation.mutate(topic.id, {
      onError: (err) => setErrorMessage(`삭제 실패: ${err.message}`),
    });
  };

  return (
    <div id={`topic-${topic.id}`} className="topic-candidate-card">
      <div className="topic-candidate-heading">
        {isEditingName ? (
          <div className="topic-name-edit">
            <input
              type="text"
              value={nameDraft}
              onChange={(event) => setNameDraft(event.target.value)}
              autoFocus
            />
            <button type="button" onClick={handleRename} disabled={renameMutation.isPending}>
              저장
            </button>
            <button type="button" onClick={() => setIsEditingName(false)}>
              취소
            </button>
          </div>
        ) : (
          <>
            <span>
              📍 {topic.name} ({topic.scraps.length})
            </span>
            <button type="button" className="icon-button" onClick={startEditing} aria-label="Topic 이름 수정">
              ✏️
            </button>
            {isConfirmingDelete ? (
              <>
                <button
                  type="button"
                  className="danger-button"
                  onClick={handleDelete}
                  disabled={deleteMutation.isPending}
                >
                  정말 삭제
                </button>
                <button type="button" onClick={() => setIsConfirmingDelete(false)}>
                  취소
                </button>
              </>
            ) : (
              <button
                type="button"
                className="icon-button"
                onClick={() => setIsConfirmingDelete(true)}
                aria-label="Topic 삭제"
              >
                🗑️
              </button>
            )}
          </>
        )}
      </div>
      {errorMessage && <p className="result">{errorMessage}</p>}
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
  );
}

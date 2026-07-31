import { useState } from 'react';
import { useIslands } from '../hooks/useIslands';
import type { IslandRecommendation } from '../types/scrap';

interface RecommendPanelProps {
  recommendations: IslandRecommendation[];
  confirmMessage: string;
  onConfirm: (body: { islandId?: number; newIslandName?: string }) => void;
}

export function RecommendPanel({ recommendations, confirmMessage, onConfirm }: RecommendPanelProps) {
  const { data: islands } = useIslands();
  const [selectedIslandId, setSelectedIslandId] = useState('');
  const [newIslandName, setNewIslandName] = useState('');
  const [localError, setLocalError] = useState('');

  const handleOtherIslandConfirm = () => {
    const islandId = Number(selectedIslandId);
    if (!islandId) {
      setLocalError('추천 목록에 없는 Island를 선택해주세요.');
      return;
    }
    setLocalError('');
    onConfirm({ islandId });
  };

  const handleNewIslandConfirm = () => {
    const name = newIslandName.trim();
    if (!name) {
      setLocalError('새 Island 이름을 입력해주세요.');
      return;
    }
    setLocalError('');
    onConfirm({ newIslandName: name });
    setNewIslandName('');
  };

  return (
    <section className="card">
      <h2>추천 Island</h2>
      <ul className="recommend-list">
        {recommendations.length === 0 ? (
          <li>추천 후보 없음 - 새 Island를 만들어주세요.</li>
        ) : (
          recommendations.map((recommendation) => (
            <li key={recommendation.islandId}>
              <button type="button" onClick={() => onConfirm({ islandId: recommendation.islandId })}>
                {recommendation.islandName} (score: {recommendation.llmScore.toFixed(2)})
              </button>
            </li>
          ))
        )}
      </ul>
      <div className="new-island">
        <select value={selectedIslandId} onChange={(event) => setSelectedIslandId(event.target.value)}>
          <option value="">다른 Island 선택...</option>
          {islands?.map((island) => (
            <option key={island.id} value={island.id}>
              {island.name} ({island.scrapCount})
            </option>
          ))}
        </select>
        <button type="button" onClick={handleOtherIslandConfirm}>
          이 Island로 확정
        </button>
      </div>
      <div className="new-island">
        <input
          type="text"
          placeholder="새 Island 이름"
          value={newIslandName}
          onChange={(event) => setNewIslandName(event.target.value)}
        />
        <button type="button" onClick={handleNewIslandConfirm}>
          새 Island로 확정
        </button>
      </div>
      <p className="result">{localError || confirmMessage}</p>
    </section>
  );
}

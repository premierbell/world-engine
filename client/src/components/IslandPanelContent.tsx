import { useEffect, useState } from 'react';
import { ApiError } from '../api/client';
import { useAddScrapsToTopic } from '../hooks/useAddScrapsToTopic';
import { useCreateTopic } from '../hooks/useCreateTopic';
import { useGenerateTopicCandidates } from '../hooks/useGenerateTopicCandidates';
import { useIsland } from '../hooks/useIsland';
import type { ScrapSummary } from '../types/scrap';
import type { TopicCandidateResponse } from '../types/topic';
import { ErrorCard } from './ErrorCard';
import { IslandHeader } from './IslandHeader';
import { LoadingCard } from './LoadingCard';
import { ScrapList } from './ScrapList';
import { TopicCandidates } from './TopicCandidates';
import { TopicList } from './TopicList';
import { TopicMapView } from './TopicMapView';

interface IslandPanelContentProps {
  islandId: number;
}

/**
 * Island 상세(Topic 후보/지도/목록, 스크랩 목록, 검색)를 렌더링하는
 * 내용물 - HomePage가 /islands/:id일 때 지도 위 Panel 안에 이걸
 * 그대로 띄운다(별도 페이지로 이동하지 않음). docs/map_home_redesign.md
 * 참고.
 */
export function IslandPanelContent({ islandId }: IslandPanelContentProps) {
  const { data: island, isLoading, isError, error, refetch } = useIsland(islandId, true);

  const [selectedScrapIds, setSelectedScrapIds] = useState<Set<number>>(new Set());
  const [topicName, setTopicName] = useState('');
  const [topicCandidates, setTopicCandidates] = useState<TopicCandidateResponse | null>(null);
  const [topicCandidatesStatus, setTopicCandidatesStatus] = useState('');
  const [topicCreateResult, setTopicCreateResult] = useState('');
  const [searchQuery, setSearchQuery] = useState('');

  useEffect(() => {
    setSelectedScrapIds(new Set());
    setTopicName('');
    setTopicCandidates(null);
    setTopicCandidatesStatus('');
    setTopicCreateResult('');
    setSearchQuery('');
  }, [islandId]);

  const generateCandidatesMutation = useGenerateTopicCandidates();
  const createTopicMutation = useCreateTopic();
  const addScrapsToTopicMutation = useAddScrapsToTopic(islandId);

  if (isLoading) {
    return <LoadingCard />;
  }

  if (isError || !island) {
    const status = error instanceof ApiError ? error.status : null;
    const message = status === 404 ? 'Island를 찾을 수 없어요.' : `불러오기 실패: ${error?.message}`;
    return <ErrorCard message={message} onRetry={() => refetch()} />;
  }

  const handleToggleScrap = (scrapId: number) => {
    setSelectedScrapIds((prev) => {
      const next = new Set(prev);
      if (next.has(scrapId)) {
        next.delete(scrapId);
      } else {
        next.add(scrapId);
      }
      return next;
    });
  };

  const handleFillCandidate = (scrapIds: number[]) => {
    setSelectedScrapIds((prev) => new Set([...prev, ...scrapIds]));
  };

  const handleGenerateCandidates = () => {
    setTopicCandidatesStatus('분석 중... (스크랩이 많으면 1~2분 걸릴 수 있어요)');
    setTopicCandidates(null);
    generateCandidatesMutation.mutate(islandId, {
      onSuccess: (data) => {
        setTopicCandidates(data);
        setTopicCandidatesStatus('');
      },
      onError: (err) => {
        setTopicCandidatesStatus(`실패: ${err.message}`);
      },
    });
  };

  const handleCreateTopic = () => {
    const name = topicName.trim();
    if (!name) {
      setTopicCreateResult('Topic 이름을 입력해주세요.');
      return;
    }
    if (selectedScrapIds.size === 0) {
      setTopicCreateResult('스크랩을 하나 이상 선택해주세요.');
      return;
    }
    createTopicMutation.mutate(
      { islandId, name, scrapIds: Array.from(selectedScrapIds) },
      {
        onSuccess: () => {
          setTopicCreateResult(`"${name}" Topic 생성됨`);
          setTopicName('');
          setSelectedScrapIds(new Set());
        },
        onError: (err) => {
          setTopicCreateResult(`실패: ${err.message}`);
        },
      },
    );
  };

  const handleAddToExistingTopic = (topicId: number, scrapIds: number[]) => {
    addScrapsToTopicMutation.mutate(
      { topicId, scrapIds },
      {
        onSuccess: (data) => {
          setTopicCandidatesStatus(`"${data.name}"에 ${scrapIds.length}개 추가됨`);
        },
        onError: (err) => {
          setTopicCandidatesStatus(`실패: ${err.message}`);
        },
      },
    );
  };

  const assignedScrapIds = new Set(island.topics.flatMap((topic) => topic.scraps.map((scrap) => scrap.id)));
  const unassignedScraps = island.scraps.filter((scrap) => !assignedScrapIds.has(scrap.id));

  const normalizedQuery = searchQuery.trim().toLowerCase();
  const matchesQuery = (scrap: ScrapSummary) =>
    !normalizedQuery ||
    (scrap.title ?? '').toLowerCase().includes(normalizedQuery) ||
    scrap.url.toLowerCase().includes(normalizedQuery);

  const filteredTopics = normalizedQuery
    ? island.topics
        .map((topic) => ({ ...topic, scraps: topic.scraps.filter(matchesQuery) }))
        .filter((topic) => topic.scraps.length > 0)
    : island.topics;
  const filteredUnassignedScraps = unassignedScraps.filter(matchesQuery);

  return (
    <>
      <IslandHeader island={island} />

      <TopicCandidates
        status={topicCandidatesStatus}
        data={topicCandidates}
        isGenerating={generateCandidatesMutation.isPending}
        onGenerate={handleGenerateCandidates}
        onFillCandidate={handleFillCandidate}
        onAddToExistingTopic={handleAddToExistingTopic}
      />

      <TopicMapView topics={island.topics} />

      <input
        type="text"
        className="search-input"
        placeholder="제목/URL로 스크랩 찾기"
        value={searchQuery}
        onChange={(event) => setSearchQuery(event.target.value)}
      />

      <TopicList topics={filteredTopics} islandId={islandId} />

      <div className="topic-create-form">
        <input
          type="text"
          placeholder="Topic 이름"
          value={topicName}
          onChange={(event) => setTopicName(event.target.value)}
        />
        <button type="button" onClick={handleCreateTopic}>
          선택한 스크랩으로 Topic 생성
        </button>
      </div>
      <p className="result">{topicCreateResult}</p>

      <ScrapList scraps={filteredUnassignedScraps} selectedIds={selectedScrapIds} onToggle={handleToggleScrap} />
    </>
  );
}

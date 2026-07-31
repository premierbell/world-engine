import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { ApiError } from '../api/client';
import { BackLink } from '../components/BackLink';
import { ErrorCard } from '../components/ErrorCard';
import { IslandHeader } from '../components/IslandHeader';
import { LoadingCard } from '../components/LoadingCard';
import { ScrapList } from '../components/ScrapList';
import { TopicCandidates } from '../components/TopicCandidates';
import { TopicList } from '../components/TopicList';
import { useAddScrapsToTopic } from '../hooks/useAddScrapsToTopic';
import { useCreateTopic } from '../hooks/useCreateTopic';
import { useGenerateTopicCandidates } from '../hooks/useGenerateTopicCandidates';
import { useIsland } from '../hooks/useIsland';
import type { TopicCandidateResponse } from '../types/topic';

export function IslandDetailPage() {
  const params = useParams();
  const islandId = Number(params.id);
  const isValidId = Number.isFinite(islandId) && islandId > 0;
  const { data: island, isLoading, isError, error, refetch } = useIsland(islandId, isValidId);

  const [selectedScrapIds, setSelectedScrapIds] = useState<Set<number>>(new Set());
  const [topicName, setTopicName] = useState('');
  const [topicCandidates, setTopicCandidates] = useState<TopicCandidateResponse | null>(null);
  const [topicCandidatesStatus, setTopicCandidatesStatus] = useState('');
  const [topicCreateResult, setTopicCreateResult] = useState('');

  // Island를 새로 열 때만 초기화한다 - Topic 생성/편입 후에는 후보 카드가 남아있어야
  // 사용자가 나머지 후보를 이어서 처리할 수 있다(app.js의 openIslandDetail vs
  // refreshIslandDetail 구분과 동일한 이유).
  useEffect(() => {
    setSelectedScrapIds(new Set());
    setTopicName('');
    setTopicCandidates(null);
    setTopicCandidatesStatus('');
    setTopicCreateResult('');
  }, [islandId]);

  const generateCandidatesMutation = useGenerateTopicCandidates();
  const createTopicMutation = useCreateTopic();
  const addScrapsToTopicMutation = useAddScrapsToTopic(islandId);

  if (!isValidId) {
    return (
      <div className="layout">
        <BackLink />
        <ErrorCard message="잘못된 Island ID예요." />
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="layout">
        <BackLink />
        <LoadingCard />
      </div>
    );
  }

  if (isError || !island) {
    const status = error instanceof ApiError ? error.status : null;
    const message = status === 404 ? 'Island를 찾을 수 없어요.' : `불러오기 실패: ${error?.message}`;
    return (
      <div className="layout">
        <BackLink />
        <ErrorCard message={message} onRetry={() => refetch()} />
      </div>
    );
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

  return (
    <section className="card">
      <BackLink />
      <IslandHeader island={island} />

      <TopicCandidates
        status={topicCandidatesStatus}
        data={topicCandidates}
        isGenerating={generateCandidatesMutation.isPending}
        onGenerate={handleGenerateCandidates}
        onFillCandidate={handleFillCandidate}
        onAddToExistingTopic={handleAddToExistingTopic}
      />

      <TopicList topics={island.topics} />

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

      <ScrapList scraps={unassignedScraps} selectedIds={selectedScrapIds} onToggle={handleToggleScrap} />
    </section>
  );
}

import { useState } from 'react';
import { ApiError } from '../api/client';
import { IslandList } from '../components/IslandList';
import { MapView } from '../components/MapView';
import { PendingList } from '../components/PendingList';
import { RecentScraps } from '../components/RecentScraps';
import { RecommendPanel } from '../components/RecommendPanel';
import { ScrapForm } from '../components/ScrapForm';
import { useConfirmScrap } from '../hooks/useConfirmScrap';
import { useCreateScrap } from '../hooks/useCreateScrap';
import { useIslands } from '../hooks/useIslands';
import { useRefreshRecommendations } from '../hooks/useRefreshRecommendations';
import type { IslandRecommendation, ScrapSummary } from '../types/scrap';

const FAILURE_MESSAGES: Record<string, string> = {
  ROBOTS_BLOCKED: '사이트가 자동 접근을 차단했어요.',
  NETWORK_ERROR: '연결에 실패했어요.',
  TIMEOUT: '응답이 너무 늦어 시간 초과됐어요.',
  UNSUPPORTED_SOURCE: '지원하지 않는 형식의 URL이에요.',
  EMPTY_CONTENT: '본문을 찾지 못했어요.',
  LOGIN_REQUIRED: '로그인이 필요한 페이지로 보여요.',
};

export function HomePage() {
  const { data: islands } = useIslands();
  const [currentScrapId, setCurrentScrapId] = useState<number | null>(null);
  const [recommendations, setRecommendations] = useState<IslandRecommendation[] | null>(null);
  const [statusMessage, setStatusMessage] = useState('');
  const [confirmMessage, setConfirmMessage] = useState('');

  const createScrapMutation = useCreateScrap();
  const refreshRecommendationsMutation = useRefreshRecommendations();
  const confirmScrapMutation = useConfirmScrap();

  const handleScrapSubmit = (url: string, userContext: string) => {
    setStatusMessage('스크랩하는 중...');
    setConfirmMessage('');
    setRecommendations(null);

    createScrapMutation.mutate(
      { url, userContext: userContext || undefined },
      {
        onSuccess: (data) => {
          setCurrentScrapId(data.scrapId);
          if (data.status === 'FAILED') {
            const reason =
              (data.failureReason && FAILURE_MESSAGES[data.failureReason]) || '본문을 가져오지 못했어요.';
            setStatusMessage(`${reason} (URL만 저장됨)`);
          } else {
            setStatusMessage(`제목: ${data.title ?? '(없음)'}\n상태: ${data.status}`);
          }
          setRecommendations(data.recommendations);
        },
        onError: (error) => {
          const status = error instanceof ApiError ? error.status : '?';
          setStatusMessage(`실패 (HTTP ${status})`);
        },
      },
    );
  };

  const handlePendingSelect = (scrap: ScrapSummary) => {
    setCurrentScrapId(scrap.id);
    setStatusMessage(`다시 확인 중: ${scrap.title ?? scrap.url}`);
    setConfirmMessage('');

    refreshRecommendationsMutation.mutate(scrap.id, {
      onSuccess: (data) => {
        setRecommendations(data);
      },
      onError: (error) => {
        setStatusMessage(`추천 재계산 실패: ${error.message}`);
      },
    });
  };

  const handleConfirm = (body: { islandId?: number; newIslandName?: string }) => {
    if (!currentScrapId) {
      return;
    }

    confirmScrapMutation.mutate(
      { scrapId: currentScrapId, ...body },
      {
        onSuccess: (data) => {
          setConfirmMessage(`"${data.islandName}"(으)로 확정됨`);
          setRecommendations(null);
        },
        onError: (error) => {
          setConfirmMessage(`실패: ${error.message}`);
        },
      },
    );
  };

  return (
    <div className="layout">
      <main className="main">
        <h1>World Engine</h1>

        <MapView islands={islands ?? []} />

        <section className="card">
          <h2>스크랩</h2>
          <ScrapForm onSubmit={handleScrapSubmit} />
          <p className="result">{statusMessage}</p>
        </section>

        {recommendations !== null && (
          <RecommendPanel
            recommendations={recommendations}
            confirmMessage={confirmMessage}
            onConfirm={handleConfirm}
          />
        )}
      </main>
      <aside className="sidebar">
        <IslandList />
        <PendingList onSelect={handlePendingSelect} />
        <RecentScraps />
      </aside>
    </div>
  );
}

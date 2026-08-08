import { useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { ApiError } from '../api/client';
import { IslandList } from '../components/IslandList';
import { IslandPanelContent } from '../components/IslandPanelContent';
import { MapView } from '../components/MapView';
import { Panel } from '../components/Panel';
import { PendingList } from '../components/PendingList';
import { RecentScraps } from '../components/RecentScraps';
import { RecommendPanel } from '../components/RecommendPanel';
import { ScrapForm } from '../components/ScrapForm';
import { SearchPanelContent } from '../components/SearchPanelContent';
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
  const navigate = useNavigate();
  const params = useParams();

  // /islands/:id의 id는 URL이 유일한 출처다 - 별도 로컬 state로 들고
  // 있지 않는다. 그래야 새로고침/공유 링크/브라우저 뒤로가기가 전부
  // 그대로 동작한다(docs/map_home_redesign.md "라우팅 변경" 참고).
  const parsedIslandId = Number(params.id);
  const selectedIslandId =
    params.id !== undefined && Number.isFinite(parsedIslandId) && parsedIslandId > 0 ? parsedIslandId : null;

  const [isScrapPanelOpen, setIsScrapPanelOpen] = useState(false);
  const [isSearchPanelOpen, setIsSearchPanelOpen] = useState(false);
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

  const selectedIsland = islands?.find((island) => island.id === selectedIslandId) ?? null;

  const handleIslandClick = (islandId: number) => {
    navigate(`/islands/${islandId}`);
  };

  const handleClosePanel = () => {
    navigate('/');
  };

  // 모바일에서는 패널이 Bottom Sheet로 화면 하단을 차지해서 FAB과
  // 겹친다(데스크톱은 패널이 좌/우/상단에 있어서 하단 중앙 FAB과
  // 안 겹침) - "패널 열림" 자체는 여기서 계산하고, 실제로 숨길지는
  // CSS 미디어쿼리 안에서만 결정해서 데스크톱은 영향 없게 한다.
  const anyPanelOpen = selectedIslandId !== null || isScrapPanelOpen || isSearchPanelOpen;
  const fabClassName = anyPanelOpen ? ' fab-hide-when-panel-open' : '';

  return (
    <div className="layout">
      <main className="main">
        <h1>World Engine</h1>

        <MapView
          islands={islands ?? []}
          onIslandClick={handleIslandClick}
          selectedIslandId={selectedIslandId}
          onBackgroundClick={handleClosePanel}
        />
      </main>
      <aside className="sidebar">
        <IslandList />
        <PendingList onSelect={handlePendingSelect} />
        <RecentScraps />
      </aside>
      <Panel isOpen={selectedIslandId !== null} onClose={handleClosePanel} title={selectedIsland?.name ?? ''}>
        {selectedIslandId !== null && <IslandPanelContent islandId={selectedIslandId} />}
      </Panel>
      <Panel position="left" isOpen={isScrapPanelOpen} onClose={() => setIsScrapPanelOpen(false)} title="스크랩 추가">
        <ScrapForm onSubmit={handleScrapSubmit} />
        <p className="result">{statusMessage}</p>
        {recommendations !== null && (
          <RecommendPanel
            recommendations={recommendations}
            confirmMessage={confirmMessage}
            onConfirm={handleConfirm}
          />
        )}
      </Panel>
      <Panel position="top" isOpen={isSearchPanelOpen} onClose={() => setIsSearchPanelOpen(false)} title="검색">
        <SearchPanelContent />
      </Panel>
      <button
        type="button"
        className={`fab fab-add${fabClassName}`}
        onClick={() => setIsScrapPanelOpen(true)}
        aria-label="스크랩 추가"
      >
        +
      </button>
      <button
        type="button"
        className={`fab fab-search${fabClassName}`}
        onClick={() => setIsSearchPanelOpen(true)}
        aria-label="검색"
      >
        🔍
      </button>
    </div>
  );
}

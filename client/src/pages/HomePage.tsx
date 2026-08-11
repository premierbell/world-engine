import { useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { ApiError } from '../api/client';
import { IslandList } from '../components/IslandList';
import { IslandPanelContent } from '../components/IslandPanelContent';
import { MapView } from '../components/MapView';
import { Panel } from '../components/Panel';
import { PendingList } from '../components/PendingList';
import { PendingReview } from '../components/PendingReview';
import { RecentScraps } from '../components/RecentScraps';
import { WorldExport } from '../components/WorldExport';
import { RecommendPanel } from '../components/RecommendPanel';
import { ScrapForm } from '../components/ScrapForm';
import { SearchPanelContent } from '../components/SearchPanelContent';
import { useConfirmScrap } from '../hooks/useConfirmScrap';
import { useCreateScrap } from '../hooks/useCreateScrap';
import { useIslands } from '../hooks/useIslands';
import { useRefreshRecommendations } from '../hooks/useRefreshRecommendations';
import type { IslandRecommendation, ScrapCreateResponse, ScrapSummary } from '../types/scrap';

interface DuplicateNotice {
  scrapId: number;
  title: string | null;
  islandId: number | null;
  islandName: string | null;
}

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
  const [isListPanelOpen, setIsListPanelOpen] = useState(false);
  const [isPendingReviewOpen, setIsPendingReviewOpen] = useState(false);
  const [currentScrapId, setCurrentScrapId] = useState<number | null>(null);
  const [recommendations, setRecommendations] = useState<IslandRecommendation[] | null>(null);
  const [statusMessage, setStatusMessage] = useState('');
  const [confirmMessage, setConfirmMessage] = useState('');
  const [duplicateNotice, setDuplicateNotice] = useState<DuplicateNotice | null>(null);
  const [lastSubmittedUrl, setLastSubmittedUrl] = useState('');
  const [lastSubmittedContext, setLastSubmittedContext] = useState('');

  const createScrapMutation = useCreateScrap();
  const refreshRecommendationsMutation = useRefreshRecommendations();
  const confirmScrapMutation = useConfirmScrap();

  // 중복 스크랩(POST /api/scraps가 duplicate:true를 준 경우)과 정상
  // 생성 둘 다 결국 같은 방식으로 결과를 반영해야 해서(강제 저장으로
  // 다시 제출한 결과도 포함) 공통 로직만 뽑음.
  const applyCreateResult = (data: ScrapCreateResponse) => {
    setCurrentScrapId(data.scrapId);
    if (data.status === 'FAILED') {
      const reason = (data.failureReason && FAILURE_MESSAGES[data.failureReason]) || '본문을 가져오지 못했어요.';
      setStatusMessage(`${reason} (URL만 저장됨)`);
    } else {
      setStatusMessage(`제목: ${data.title ?? '(없음)'}\n상태: ${data.status}`);
    }
    setRecommendations(data.recommendations);
  };

  const handleScrapSubmit = (url: string, userContext: string) => {
    setStatusMessage('스크랩하는 중...');
    setConfirmMessage('');
    setRecommendations(null);
    setDuplicateNotice(null);
    setLastSubmittedUrl(url);
    setLastSubmittedContext(userContext);

    createScrapMutation.mutate(
      { url, userContext: userContext || undefined },
      {
        onSuccess: (data) => {
          if (data.duplicate) {
            setStatusMessage('');
            setDuplicateNotice({
              scrapId: data.scrapId,
              title: data.title,
              islandId: data.existingIslandId,
              islandName: data.existingIslandName,
            });
            return;
          }
          applyCreateResult(data);
        },
        onError: (error) => {
          const status = error instanceof ApiError ? error.status : '?';
          setStatusMessage(`실패 (HTTP ${status})`);
        },
      },
    );
  };

  const handleForceSaveDuplicate = () => {
    setDuplicateNotice(null);
    setStatusMessage('스크랩하는 중...');

    createScrapMutation.mutate(
      { url: lastSubmittedUrl, userContext: lastSubmittedContext || undefined, force: true },
      {
        onSuccess: applyCreateResult,
        onError: (error) => {
          const status = error instanceof ApiError ? error.status : '?';
          setStatusMessage(`실패 (HTTP ${status})`);
        },
      },
    );
  };

  const handleViewDuplicateIsland = () => {
    if (!duplicateNotice?.islandId) {
      return;
    }
    const islandId = duplicateNotice.islandId;
    setIsScrapPanelOpen(false);
    setDuplicateNotice(null);
    navigate(`/islands/${islandId}`);
  };

  const handlePendingSelect = (scrap: ScrapSummary) => {
    setCurrentScrapId(scrap.id);
    setStatusMessage(`다시 확인 중: ${scrap.title ?? scrap.url}`);
    setConfirmMessage('');
    setDuplicateNotice(null);
    // 결과(추천 목록)가 뜨는 자리가 "스크랩 추가" 패널 안이라, 그
    // 패널이 안 열려 있으면 여기까지 와도 아무것도 안 보이던 기존
    // 사각지대 - 목록에서 클릭하면 같이 열어준다.
    setIsScrapPanelOpen(true);

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

  // 스크랩 추가 패널이 Island 상세 패널과 같은 자리(position="right"
  // 기본값)를 쓴다(docs/map_home_redesign.md "임시 규칙" - 좌/우/상단
  // 3자리뿐) - 섬을 클릭하면 스크랩 추가는 닫는다. 목록 패널(left)은
  // 이 충돌과 무관해서 "목록 보면서 섬 클릭 → 상세 보기" 조합은
  // 그대로 동시에 열려 있을 수 있다.
  const handleIslandClick = (islandId: number) => {
    setIsScrapPanelOpen(false);
    navigate(`/islands/${islandId}`);
  };

  const handleClosePanel = () => {
    navigate('/');
  };

  const openScrapPanel = () => {
    navigate('/');
    setIsScrapPanelOpen(true);
  };

  // 모바일에서는 패널이 Bottom Sheet로 화면 하단을 차지해서 FAB과
  // 겹친다(데스크톱은 패널이 좌/우/상단에 있어서 하단 중앙 FAB과
  // 안 겹침) - "패널 열림" 자체는 여기서 계산하고, 실제로 숨길지는
  // CSS 미디어쿼리 안에서만 결정해서 데스크톱은 영향 없게 한다.
  const anyPanelOpen = selectedIslandId !== null || isScrapPanelOpen || isSearchPanelOpen || isListPanelOpen;
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
      <Panel isOpen={selectedIslandId !== null} onClose={handleClosePanel} title={selectedIsland?.name ?? ''}>
        {selectedIslandId !== null && <IslandPanelContent islandId={selectedIslandId} />}
      </Panel>
      {/* Islands/정리할 스크랩/최근 Scraps - 예전엔 상시 노출 사이드바였는데,
          지도 옆에 항상 고정 폭을 차지해서 데스크톱 지도 영역이 좁아지는
          문제가 있었다. 스크랩 추가/검색과 같은 온디맨드 패널로 통일 -
          기본은 지도만 보이고, 필요할 때 "목록" 버튼으로 불러온다.
          "일괄 처리 시작" 누르면 이 자리가 통째로 PendingReview로
          바뀐다 - 오른쪽 패널은 Island 상세/스크랩 추가가 이미 쓰고
          있어서 새 패널 자리를 안 늘리려고 이 슬롯을 재사용. */}
      <Panel
        position="left"
        isOpen={isListPanelOpen}
        onClose={() => setIsListPanelOpen(false)}
        title={isPendingReviewOpen ? '정리할 스크랩 처리' : '목록'}
      >
        {isPendingReviewOpen ? (
          <PendingReview onExit={() => setIsPendingReviewOpen(false)} />
        ) : (
          <>
            <IslandList />
            <PendingList onSelect={handlePendingSelect} onStartReview={() => setIsPendingReviewOpen(true)} />
            <RecentScraps />
            <WorldExport />
          </>
        )}
      </Panel>
      <Panel isOpen={isScrapPanelOpen} onClose={() => setIsScrapPanelOpen(false)} title="스크랩 추가">
        <ScrapForm onSubmit={handleScrapSubmit} />
        <p className="result">{statusMessage}</p>
        {duplicateNotice && (
          <div className="duplicate-notice">
            <p>
              이미 스크랩한 URL이에요: "{duplicateNotice.title ?? '(제목 없음)'}"
              {duplicateNotice.islandName
                ? ` — ${duplicateNotice.islandName} 섬에 있음`
                : ' — 아직 정리할 스크랩 상태'}
            </p>
            <div className="duplicate-notice-actions">
              {duplicateNotice.islandId !== null && (
                <button type="button" onClick={handleViewDuplicateIsland}>
                  기존 스크랩 보기
                </button>
              )}
              <button type="button" onClick={handleForceSaveDuplicate}>
                그래도 저장
              </button>
            </div>
          </div>
        )}
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
        className={`fab fab-list${fabClassName}`}
        onClick={() => setIsListPanelOpen(true)}
        aria-label="목록"
      >
        📋
      </button>
      <button type="button" className={`fab fab-add${fabClassName}`} onClick={openScrapPanel} aria-label="스크랩 추가">
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

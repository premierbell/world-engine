import { useEffect, useState } from 'react';
import { useConfirmScrap } from '../hooks/useConfirmScrap';
import { useDeleteScrap } from '../hooks/useDeleteScrap';
import { usePendingScraps } from '../hooks/usePendingScraps';
import { useRefreshRecommendations } from '../hooks/useRefreshRecommendations';
import type { IslandRecommendation, ScrapSummary } from '../types/scrap';
import { RecommendPanel } from './RecommendPanel';

type ItemStatus = 'pending' | 'confirmed' | 'skipped' | 'deleted';

interface QueueItem {
  scrap: ScrapSummary;
  status: ItemStatus;
  confirmedIslandName?: string;
}

interface PendingReviewProps {
  onExit: () => void;
}

/**
 * "정리할 스크랩"을 하나씩 화면 전환 없이 연속으로 처리하는 Inbox 모드.
 * "여러 개를 한 번에 확정"하는 게 아니라 "여러 개를 하나의 작업
 * 세션으로 묶어서 끊기지 않게 처리"하는 게 핵심 - 시작 시점의 목록을
 * 그대로 얼려서 대기열로 쓰고(처리 중 다른 스크랩이 새로 들어와도 안
 * 흔들림), 추천은 표시되는 시점에 하나씩만 계산(캐시 재사용)한다.
 * 확정 → 대기열에서 "처리 완료"로 표시, 건너뛰기 → 이 세션에서만
 * 넘어감(DB엔 미확정으로 남음), 삭제 → 완전히 제거(IslandHeader/
 * TopicList와 같은 인라인 2단계 확인, window.confirm 안 씀).
 */
export function PendingReview({ onExit }: PendingReviewProps) {
  const { data: initialPending } = usePendingScraps();
  const [queue, setQueue] = useState<QueueItem[] | null>(null);
  const [index, setIndex] = useState(0);
  const [recommendationsCache, setRecommendationsCache] = useState<Record<number, IslandRecommendation[]>>({});
  const [confirmMessage, setConfirmMessage] = useState('');
  const [confirmingDeleteId, setConfirmingDeleteId] = useState<number | null>(null);

  const refreshRecommendationsMutation = useRefreshRecommendations();
  const confirmScrapMutation = useConfirmScrap();
  const deleteScrapMutation = useDeleteScrap();

  useEffect(() => {
    if (queue === null && initialPending) {
      setQueue(initialPending.map((scrap) => ({ scrap, status: 'pending' as ItemStatus })));
    }
  }, [initialPending, queue]);

  const current = queue?.[index] ?? null;

  useEffect(() => {
    setConfirmMessage('');
    setConfirmingDeleteId(null);
  }, [index]);

  useEffect(() => {
    if (!current || (current.status !== 'pending' && current.status !== 'skipped')) {
      return;
    }
    if (recommendationsCache[current.scrap.id]) {
      return;
    }
    refreshRecommendationsMutation.mutate(current.scrap.id, {
      onSuccess: (data) => {
        setRecommendationsCache((prev) => ({ ...prev, [current.scrap.id]: data }));
      },
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [current?.scrap.id, current?.status]);

  if (!queue) {
    return <p className="result">불러오는 중...</p>;
  }

  if (queue.length === 0) {
    return (
      <div className="pending-review">
        <p className="result">정리할 스크랩이 없어요.</p>
        <button type="button" onClick={onExit}>
          목록으로
        </button>
      </div>
    );
  }

  const confirmedCount = queue.filter((item) => item.status === 'confirmed').length;
  const skippedCount = queue.filter((item) => item.status === 'skipped').length;
  const deletedCount = queue.filter((item) => item.status === 'deleted').length;
  const remainingCount = queue.length - confirmedCount - skippedCount - deletedCount;
  const isDone = index >= queue.length;

  const updateCurrentStatus = (status: ItemStatus, confirmedIslandName?: string) => {
    setQueue((prev) => prev!.map((item, i) => (i === index ? { ...item, status, confirmedIslandName } : item)));
  };

  const goNext = () => setIndex((i) => Math.min(i + 1, queue.length));
  const goPrev = () => setIndex((i) => Math.max(i - 1, 0));

  const handleConfirm = (body: { islandId?: number; newIslandName?: string }) => {
    if (!current) {
      return;
    }
    confirmScrapMutation.mutate(
      { scrapId: current.scrap.id, ...body },
      {
        onSuccess: (data) => {
          updateCurrentStatus('confirmed', data.islandName);
          goNext();
        },
        onError: (error) => setConfirmMessage(`실패: ${error.message}`),
      },
    );
  };

  const handleSkip = () => {
    updateCurrentStatus('skipped');
    goNext();
  };

  const handleDeleteConfirmed = () => {
    if (!current) {
      return;
    }
    deleteScrapMutation.mutate(current.scrap.id, {
      onSuccess: () => {
        updateCurrentStatus('deleted');
        setConfirmingDeleteId(null);
        goNext();
      },
    });
  };

  return (
    <div className="pending-review">
      <p className="pending-review-progress">
        {Math.min(index + 1, queue.length)} / {queue.length}
        <span className="pending-review-summary">
          {' '}
          · 완료 {confirmedCount} · 건너뜀 {skippedCount} · 삭제 {deletedCount} · 남음 {remainingCount}
        </span>
      </p>

      <div className="pending-review-nav">
        <button type="button" onClick={goPrev} disabled={index === 0}>
          ← 이전
        </button>
        <button type="button" onClick={goNext} disabled={index >= queue.length - 1}>
          다음 →
        </button>
      </div>

      {isDone ? (
        <p className="result">정리할 스크랩을 모두 처리했어요! 🎉</p>
      ) : current ? (
        <>
          <p className="pending-review-title">{current.scrap.title ?? current.scrap.url}</p>

          {current.status === 'confirmed' && (
            <p className="result">✅ 이미 "{current.confirmedIslandName}"(으)로 확정됨</p>
          )}
          {current.status === 'deleted' && <p className="result">🗑️ 삭제됨</p>}

          {(current.status === 'pending' || current.status === 'skipped') && (
            <>
              <RecommendPanel
                recommendations={recommendationsCache[current.scrap.id] ?? []}
                confirmMessage={confirmMessage}
                onConfirm={handleConfirm}
              />
              <div className="pending-review-actions">
                <button type="button" onClick={handleSkip}>
                  건너뛰기
                </button>
                {confirmingDeleteId === current.scrap.id ? (
                  <button type="button" className="danger-button" onClick={handleDeleteConfirmed}>
                    정말 삭제
                  </button>
                ) : (
                  <button type="button" onClick={() => setConfirmingDeleteId(current.scrap.id)}>
                    삭제
                  </button>
                )}
              </div>
            </>
          )}
        </>
      ) : null}

      <button type="button" className="pending-review-exit" onClick={onExit}>
        그만하기
      </button>
    </div>
  );
}

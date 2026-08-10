import { useEffect, useState } from 'react';
import type { IslandDetail } from '../types/island';
import { buildGrowthChronicle } from '../islandGrowth/chronicle';
import { ComposedIslandView } from '../islandGrowth/ComposedIslandView';
import { useCollapsible } from '../hooks/useCollapsible';

interface IslandChronicleProps {
  island: IslandDetail;
}

const PLAY_INTERVAL_MS = 1200;

// 섬의 성장을 그래프가 아니라 "그 시점의 실제 섬 그림"으로 보여준다 -
// composeIsland()를 그대로 재사용해서 새 시각 디자인 없이, 탄생/Tier
// 전환/Topic 생성/현재라는 의미 있는 사건만 훑어본다. Island를 열
// 때마다 항상 보일 필요는 없는 "가끔 들여다보는" 기능이라 사이드바
// 카드와 같은 접기/펼치기 패턴(useCollapsible)을 그대로 씀 - 기본은
// 접힘.
export function IslandChronicle({ island }: IslandChronicleProps) {
  const [open, toggleOpen] = useCollapsible('chronicle', false);
  const milestones = buildGrowthChronicle(island);
  const [index, setIndex] = useState(milestones.length - 1);
  const [isPlaying, setIsPlaying] = useState(false);

  // 다른 섬을 열면 항상 "현재"부터 다시 보여준다.
  useEffect(() => {
    setIndex(milestones.length - 1);
    setIsPlaying(false);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [island.id]);

  useEffect(() => {
    if (!open || !isPlaying) {
      return;
    }
    if (index >= milestones.length - 1) {
      setIsPlaying(false);
      return;
    }
    const timer = setTimeout(() => setIndex((prev) => prev + 1), PLAY_INTERVAL_MS);
    return () => clearTimeout(timer);
  }, [open, isPlaying, index, milestones.length]);

  if (milestones.length === 0) {
    return null;
  }

  const current = milestones[index];
  const formattedDate = new Date(current.date).toLocaleDateString('ko-KR');

  const handlePlayToggle = () => {
    if (!isPlaying && index >= milestones.length - 1) {
      setIndex(0);
    }
    setIsPlaying((prev) => !prev);
  };

  const jumpTo = (i: number) => {
    setIsPlaying(false);
    setIndex(i);
  };

  return (
    <div className="chronicle">
      <h2>
        <button type="button" className="card-toggle" onClick={toggleOpen} aria-expanded={open}>
          <span className="chevron" aria-hidden="true">
            {open ? '▾' : '▸'}
          </span>
          연대기
        </button>
      </h2>
      {open && (
        <>
          <div className="chronicle-stage">
            <ComposedIslandView islandId={island.id} tier={current.tier} topicIds={current.topicIds} size={160} />
            <p className="chronicle-caption">
              {formattedDate} · {current.caption}
            </p>
          </div>
          <div className="chronicle-controls">
            <button type="button" onClick={() => jumpTo(Math.max(0, index - 1))} disabled={index === 0}>
              ◀
            </button>
            <button type="button" onClick={handlePlayToggle}>
              {isPlaying ? '정지' : '▶ 재생'}
            </button>
            <button
              type="button"
              onClick={() => jumpTo(Math.min(milestones.length - 1, index + 1))}
              disabled={index === milestones.length - 1}
            >
              ▶
            </button>
          </div>
          <div className="chronicle-track">
            {milestones.map((milestone, i) => (
              <button
                key={`${milestone.date}-${i}`}
                type="button"
                className={`chronicle-milestone${i === index ? ' active' : ''}`}
                onClick={() => jumpTo(i)}
              >
                <span className="dot" />
                <span className="milestone-label">{milestone.label}</span>
              </button>
            ))}
          </div>
        </>
      )}
    </div>
  );
}

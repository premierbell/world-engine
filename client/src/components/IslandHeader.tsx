import type { IslandDetail } from '../types/island';

interface IslandHeaderProps {
  island: IslandDetail;
}

export function IslandHeader({ island }: IslandHeaderProps) {
  return (
    <>
      <h2>{island.name}</h2>
      <div className="island-signals">
        <div className="signal">
          <span className="signal-label">Cosine Variance</span>
          <span className="signal-value">
            {island.cosineVariance == null ? '스크랩 2개 미만' : island.cosineVariance.toFixed(3)}
          </span>
        </div>
        <div className="signal">
          <span className="signal-label">Override Rate</span>
          <span className="signal-value">
            {island.overrideRate == null ? '추천 이력 없음' : `${Math.round(island.overrideRate * 100)}%`}
          </span>
        </div>
      </div>
      <p className="signal-note">참고용 관찰 지표입니다 - 이 값이 무언가를 자동으로 결정하지 않습니다.</p>
    </>
  );
}

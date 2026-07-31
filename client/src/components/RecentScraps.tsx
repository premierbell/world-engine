import { useRecentScraps } from '../hooks/useRecentScraps';

export function RecentScraps() {
  const { data: scraps, refetch } = useRecentScraps();

  return (
    <section className="card">
      <h2>
        최근 Scraps
        <button type="button" className="refresh" onClick={() => refetch()}>
          ↻
        </button>
      </h2>
      <ul id="scrap-list" className="entity-list">
        {!scraps || scraps.length === 0 ? (
          <li>아직 없음</li>
        ) : (
          scraps
            .slice()
            .reverse()
            .map((scrap) => (
              <li key={scrap.id}>
                {scrap.title ?? scrap.url}
                {scrap.wasCorrected ? ' ⚠️정정됨' : ''}
              </li>
            ))
        )}
      </ul>
    </section>
  );
}

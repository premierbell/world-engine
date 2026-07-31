import type { ScrapSummary } from '../types/scrap';
import { usePendingScraps } from '../hooks/usePendingScraps';

interface PendingListProps {
  onSelect: (scrap: ScrapSummary) => void;
}

export function PendingList({ onSelect }: PendingListProps) {
  const { data: scraps, refetch } = usePendingScraps();

  return (
    <section className="card">
      <h2>
        정리할 스크랩
        <button type="button" className="refresh" onClick={() => refetch()}>
          ↻
        </button>
      </h2>
      <ul id="pending-list" className="entity-list pending-list">
        {!scraps || scraps.length === 0 ? (
          <li>정리할 스크랩 없음</li>
        ) : (
          scraps
            .slice()
            .reverse()
            .map((scrap) => (
              <li key={scrap.id}>
                <button type="button" onClick={() => onSelect(scrap)}>
                  {scrap.title ?? scrap.url}
                </button>
              </li>
            ))
        )}
      </ul>
    </section>
  );
}

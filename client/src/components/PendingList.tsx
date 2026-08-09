import type { ScrapSummary } from '../types/scrap';
import { usePendingScraps } from '../hooks/usePendingScraps';
import { useCollapsible } from '../hooks/useCollapsible';

interface PendingListProps {
  onSelect: (scrap: ScrapSummary) => void;
}

export function PendingList({ onSelect }: PendingListProps) {
  const { data: scraps, refetch } = usePendingScraps();
  // 기본 펼침 - "아직 안 정리했다"는 리마인더 역할이라 접혀서 안 보이면
  // 의미가 없다. 접혀 있어도 헤더의 개수 표시는 남는다.
  const [open, toggle] = useCollapsible('pending', true);

  return (
    <section className="card">
      <h2>
        <button type="button" className="card-toggle" onClick={toggle} aria-expanded={open}>
          <span className="chevron" aria-hidden="true">
            {open ? '▾' : '▸'}
          </span>
          정리할 스크랩{scraps ? ` (${scraps.length})` : ''}
        </button>
        <button type="button" className="refresh" onClick={() => refetch()}>
          ↻
        </button>
      </h2>
      {open && (
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
      )}
    </section>
  );
}

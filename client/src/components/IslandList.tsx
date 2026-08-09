import { Link } from 'react-router-dom';
import { useIslands } from '../hooks/useIslands';
import { useCollapsible } from '../hooks/useCollapsible';

export function IslandList() {
  const { data: islands, refetch } = useIslands();
  // 기본 펼침 - 섬 목록은 지도와 짝을 이루는 1차 내비게이션이라 항상
  // 보이는 게 자연스럽다.
  const [open, toggle] = useCollapsible('islands', true);

  return (
    <section className="card">
      <h2>
        <button type="button" className="card-toggle" onClick={toggle} aria-expanded={open}>
          <span className="chevron" aria-hidden="true">
            {open ? '▾' : '▸'}
          </span>
          Islands
        </button>
        <button type="button" className="refresh" onClick={() => refetch()}>
          ↻
        </button>
      </h2>
      {open && (
        <ul id="island-list" className="entity-list">
          {!islands || islands.length === 0 ? (
            <li>아직 없음</li>
          ) : (
            islands.map((island) => (
              <li key={island.id}>
                <Link to={`/islands/${island.id}`}>
                  {island.name} ({island.scrapCount})
                </Link>
              </li>
            ))
          )}
        </ul>
      )}
    </section>
  );
}

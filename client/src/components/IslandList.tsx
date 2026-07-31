import { Link } from 'react-router-dom';
import { useIslands } from '../hooks/useIslands';

export function IslandList() {
  const { data: islands, refetch } = useIslands();

  return (
    <section className="card">
      <h2>
        Islands
        <button type="button" className="refresh" onClick={() => refetch()}>
          ↻
        </button>
      </h2>
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
    </section>
  );
}

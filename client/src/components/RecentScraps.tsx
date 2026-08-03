import { useState } from 'react';
import { useRecentScraps } from '../hooks/useRecentScraps';

export function RecentScraps() {
  const { data: scraps, refetch } = useRecentScraps();
  const [query, setQuery] = useState('');

  const normalizedQuery = query.trim().toLowerCase();
  const filtered = (scraps ?? []).filter((scrap) => {
    if (!normalizedQuery) {
      return true;
    }
    return (
      (scrap.title ?? '').toLowerCase().includes(normalizedQuery) ||
      scrap.url.toLowerCase().includes(normalizedQuery)
    );
  });

  return (
    <section className="card">
      <h2>
        최근 Scraps
        <button type="button" className="refresh" onClick={() => refetch()}>
          ↻
        </button>
      </h2>
      <input
        type="text"
        className="search-input"
        placeholder="제목/URL로 찾기"
        value={query}
        onChange={(event) => setQuery(event.target.value)}
      />
      <ul id="scrap-list" className="entity-list">
        {filtered.length === 0 ? (
          <li>{normalizedQuery ? '검색 결과 없음' : '아직 없음'}</li>
        ) : (
          filtered
            .slice()
            .reverse()
            .map((scrap) => (
              <li key={scrap.id}>
                <a href={scrap.url} target="_blank" rel="noopener noreferrer">
                  {scrap.title ?? scrap.url}
                </a>
                {scrap.wasCorrected ? ' ⚠️정정됨' : ''}
              </li>
            ))
        )}
      </ul>
    </section>
  );
}

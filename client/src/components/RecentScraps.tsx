import { useState } from 'react';
import { useRecentScraps } from '../hooks/useRecentScraps';
import { useCollapsible } from '../hooks/useCollapsible';

export function RecentScraps() {
  const { data: scraps, refetch } = useRecentScraps();
  const [query, setQuery] = useState('');
  // 기본 접힘 - 검색해서 찾아보는 참고용 목록이라 Islands/정리할
  // 스크랩과 달리 항상 펼쳐져 있을 필요는 없다.
  const [open, toggle] = useCollapsible('recent', false);

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
        <button type="button" className="card-toggle" onClick={toggle} aria-expanded={open}>
          <span className="chevron" aria-hidden="true">
            {open ? '▾' : '▸'}
          </span>
          최근 Scraps
        </button>
        <button type="button" className="refresh" onClick={() => refetch()}>
          ↻
        </button>
      </h2>
      {open && (
        <>
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
        </>
      )}
    </section>
  );
}

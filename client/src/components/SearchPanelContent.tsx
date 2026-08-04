import { useState } from 'react';
import { useRecentScraps } from '../hooks/useRecentScraps';

/**
 * 전역 검색 패널 - 어느 Island에 있는지 몰라도 전체 스크랩을 제목/URL로
 * 찾는다. Island 상세 패널 안의 검색(그 Island로 범위가 한정됨)과는
 * 별개 - PR #101의 검색 기능을 지도에서 바로 여는 독립 패널로 승격한
 * 것. docs/map_home_redesign.md 참고.
 */
export function SearchPanelContent() {
  const { data: scraps } = useRecentScraps();
  const [query, setQuery] = useState('');

  const normalizedQuery = query.trim().toLowerCase();
  const filtered = normalizedQuery
    ? (scraps ?? []).filter(
        (scrap) =>
          (scrap.title ?? '').toLowerCase().includes(normalizedQuery) ||
          scrap.url.toLowerCase().includes(normalizedQuery),
      )
    : [];

  return (
    <>
      <input
        type="text"
        className="search-input"
        placeholder="전체 스크랩에서 제목/URL로 찾기"
        value={query}
        onChange={(event) => setQuery(event.target.value)}
        autoFocus
      />
      <ul className="entity-list">
        {!normalizedQuery ? (
          <li>검색어를 입력하세요</li>
        ) : filtered.length === 0 ? (
          <li>검색 결과 없음</li>
        ) : (
          filtered.map((scrap) => (
            <li key={scrap.id}>
              <a href={scrap.url} target="_blank" rel="noopener noreferrer">
                {scrap.title ?? scrap.url}
              </a>
            </li>
          ))
        )}
      </ul>
    </>
  );
}

import type { ScrapSummary } from '../types/scrap';

interface ScrapListProps {
  scraps: ScrapSummary[];
  selectedIds: Set<number>;
  onToggle: (scrapId: number) => void;
}

export function ScrapList({ scraps, selectedIds, onToggle }: ScrapListProps) {
  return (
    <ul id="island-detail-scraps" className="entity-list">
      {scraps
        .slice()
        .reverse()
        .map((scrap) => (
          <li key={scrap.id}>
            <input
              type="checkbox"
              className="scrap-select"
              checked={selectedIds.has(scrap.id)}
              onChange={() => onToggle(scrap.id)}
            />
            <label>
              <a href={scrap.url} target="_blank" rel="noopener noreferrer">
                {scrap.title ?? scrap.url}
              </a>
              {scrap.wasCorrected ? ' ⚠️정정됨' : ''}
            </label>
          </li>
        ))}
    </ul>
  );
}

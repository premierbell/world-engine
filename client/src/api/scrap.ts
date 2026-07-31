import { apiFetch } from './client';
import type {
  IslandRecommendation,
  ScrapConfirmResponse,
  ScrapCreateResponse,
  ScrapDetail,
  ScrapSummary,
} from '../types/scrap';

export function fetchScraps(confirmed?: boolean) {
  const query = confirmed === undefined ? '' : `?confirmed=${confirmed}`;
  return apiFetch<ScrapSummary[]>(`/api/scraps${query}`);
}

export function fetchScrap(id: number) {
  return apiFetch<ScrapDetail>(`/api/scraps/${id}`);
}

export function createScrap(url: string, userContext?: string) {
  return apiFetch<ScrapCreateResponse>('/api/scraps', {
    method: 'POST',
    body: JSON.stringify({ url, userContext: userContext || null }),
  });
}

export function confirmScrap(id: number, islandId?: number, newIslandName?: string) {
  return apiFetch<ScrapConfirmResponse>(`/api/scraps/${id}/confirm`, {
    method: 'POST',
    body: JSON.stringify({ islandId: islandId ?? null, newIslandName: newIslandName ?? null }),
  });
}

export function refreshRecommendations(id: number) {
  return apiFetch<IslandRecommendation[]>(`/api/scraps/${id}/recommendations`, {
    method: 'POST',
  });
}

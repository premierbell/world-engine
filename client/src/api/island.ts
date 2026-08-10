import { apiFetch } from './client';
import type { IslandDetail, IslandSummary } from '../types/island';
import type { TopicCandidateResponse } from '../types/topic';

export function fetchIslands() {
  return apiFetch<IslandSummary[]>('/api/islands');
}

export function fetchIsland(id: number) {
  return apiFetch<IslandDetail>(`/api/islands/${id}`);
}

export function generateTopicCandidates(islandId: number) {
  return apiFetch<TopicCandidateResponse>(`/api/islands/${islandId}/topic-candidates`, {
    method: 'POST',
  });
}

export function renameIsland(id: number, name: string) {
  return apiFetch<{ id: number; name: string }>(`/api/islands/${id}`, {
    method: 'PATCH',
    body: JSON.stringify({ name }),
  });
}

export function deleteIsland(id: number) {
  return apiFetch<void>(`/api/islands/${id}`, { method: 'DELETE' });
}

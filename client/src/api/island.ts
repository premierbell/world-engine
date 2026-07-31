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

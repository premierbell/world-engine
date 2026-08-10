import { apiFetch } from './client';
import type { TopicCreateResponse } from '../types/topic';

export function createTopic(islandId: number, name: string, scrapIds: number[]) {
  return apiFetch<TopicCreateResponse>('/api/topics', {
    method: 'POST',
    body: JSON.stringify({ islandId, name, scrapIds }),
  });
}

export function addScrapsToTopic(topicId: number, scrapIds: number[]) {
  return apiFetch<TopicCreateResponse>(`/api/topics/${topicId}/scraps`, {
    method: 'POST',
    body: JSON.stringify({ scrapIds }),
  });
}

export function renameTopic(id: number, name: string) {
  return apiFetch<{ id: number; name: string }>(`/api/topics/${id}`, {
    method: 'PATCH',
    body: JSON.stringify({ name }),
  });
}

export function deleteTopic(id: number) {
  return apiFetch<void>(`/api/topics/${id}`, { method: 'DELETE' });
}

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

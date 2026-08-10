import type { ScrapSummary } from './scrap';

export interface TopicSummary {
  id: number;
  name: string;
  scraps: ScrapSummary[];
  createdAt: string;
}

export interface TopicCreateResponse {
  id: number;
  name: string;
  islandId: number;
  scrapCount: number;
}

export interface ExistingTopicMatch {
  scrap: ScrapSummary;
  topicId: number;
  topicName: string;
  score: number;
  matchedAgainst: ScrapSummary;
}

export interface TopicCandidateGroup {
  scraps: ScrapSummary[];
  averageScore: number;
  minimumScore: number;
}

export interface TopicCandidateResponse {
  existingTopicMatches: ExistingTopicMatch[];
  groups: TopicCandidateGroup[];
  ungrouped: ScrapSummary[];
}

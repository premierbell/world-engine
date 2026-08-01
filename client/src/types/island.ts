import type { ScrapSummary } from './scrap';
import type { TopicSummary } from './topic';

export interface IslandSummary {
  id: number;
  name: string;
  scrapCount: number;
  topicCount: number;
}

export interface IslandDetail {
  id: number;
  name: string;
  scraps: ScrapSummary[];
  cosineVariance: number | null;
  overrideRate: number | null;
  topics: TopicSummary[];
}

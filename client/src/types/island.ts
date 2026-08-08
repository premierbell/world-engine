import type { ScrapSummary } from './scrap';
import type { TopicSummary } from './topic';

export type GrowthTier = 'SEED' | 'ISLET' | 'VILLAGE' | 'CITY';

export interface IslandSummary {
  id: number;
  name: string;
  scrapCount: number;
  topicCount: number;
  x: number;
  y: number;
  tier: GrowthTier;
}

export interface IslandDetail {
  id: number;
  name: string;
  scraps: ScrapSummary[];
  cosineVariance: number | null;
  overrideRate: number | null;
  topics: TopicSummary[];
}

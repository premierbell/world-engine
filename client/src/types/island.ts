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
  // 생성 순서(id) 오름차순으로 정렬돼서 온다 - Island Growth Visual
  // "B안"에서 건물 자리를 이 순서대로 고정 배정하는 데 쓴다.
  topicIds: number[];
}

export interface IslandDetail {
  id: number;
  name: string;
  scraps: ScrapSummary[];
  cosineVariance: number | null;
  overrideRate: number | null;
  topics: TopicSummary[];
}

import type { ScrapSummary } from './scrap';
import type { TopicSummary } from './topic';

export type GrowthTier = 'SEED' | 'ISLET' | 'VILLAGE' | 'CITY';

// Growth Point(scrapCount)를 사람이 체감할 수 있는 이름으로 보여준다 -
// "성장은 체감 가능해야 한다", docs/vision.md 제품 원칙 4번. 경계값은
// 서버 GrowthTier.fromScrapCount(server/.../island/model/GrowthTier.java)
// 그대로 - 화면 표시/연대기 재구성처럼 서버를 다시 안 부르고 계산해야
// 하는 곳에서만 프론트에 미러링한다. 바뀌면 두 군데 다 맞출 것.
export const TIER_LABELS: Record<GrowthTier, string> = {
  SEED: 'Seed',
  ISLET: 'Islet',
  VILLAGE: 'Village',
  CITY: 'City',
};

export function formatTier(tier: GrowthTier): string {
  return TIER_LABELS[tier];
}

export function tierFromScrapCount(scrapCount: number): GrowthTier {
  if (scrapCount <= 3) {
    return 'SEED';
  }
  if (scrapCount <= 10) {
    return 'ISLET';
  }
  if (scrapCount <= 30) {
    return 'VILLAGE';
  }
  return 'CITY';
}

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

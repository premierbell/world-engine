import type { GrowthTier, IslandDetail } from '../types/island';
import { TIER_LABELS, tierFromScrapCount } from '../types/island';

// 섬의 성장 "히스토리"를 그래프(날짜별 숫자)가 아니라 사건 단위로
// 재구성한다 - 스크랩 23개면 23개 날짜를 다 보여줄 필요 없다, 탄생/
// Tier 전환/Topic 생성/현재처럼 실제로 의미 있는 지점만 뽑는다. 각
// 사건은 그 시점의 (tier, topicIds)를 들고 있어서 composeIsland()에
// 그대로 넣으면 "그때의 섬 모습"이 나온다 - 새 시각 디자인 없이
// 기존 조합 엔진을 시간 축으로 재생하는 것뿐.
export interface GrowthMilestone {
  date: string;
  scrapCount: number;
  tier: GrowthTier;
  topicIds: number[];
  label: string;
  caption: string;
}

export function buildGrowthChronicle(island: IslandDetail): GrowthMilestone[] {
  const scrapDates = island.scraps.map((scrap) => scrap.createdAt).sort();
  if (scrapDates.length === 0) {
    return [];
  }

  // Topic 생성 순서(id 오름차순)는 B안(client/src/islandGrowth/compose.ts)에서
  // building anchor를 배정하는 순서와 같다 - 과거 시점의 topicIds도
  // 항상 이 순서의 "앞부분"이라 어느 시점을 봐도 건물 자리가 안 흔들린다.
  const topicEvents = island.topics
    .map((topic) => ({ id: topic.id, name: topic.name, createdAt: topic.createdAt }))
    .sort((a, b) => a.id - b.id);

  const topicIdsAsOf = (date: string) => topicEvents.filter((topic) => topic.createdAt <= date).map((topic) => topic.id);

  const milestones: GrowthMilestone[] = [];
  let lastTier: GrowthTier | null = null;

  scrapDates.forEach((date, index) => {
    const scrapCount = index + 1;
    const tier = tierFromScrapCount(scrapCount);
    const isBirth = index === 0;
    const isTierChange = tier !== lastTier;

    if (isBirth || isTierChange) {
      milestones.push({
        date,
        scrapCount,
        tier,
        topicIds: topicIdsAsOf(date),
        label: isBirth ? '탄생' : `${TIER_LABELS[tier]} 진입`,
        caption: isBirth
          ? '첫 번째 스크랩이 이 섬을 만들었습니다.'
          : `스크랩 ${scrapCount}개 - ${TIER_LABELS[tier]} 단계로 자랐습니다.`,
      });
    }
    lastTier = tier;
  });

  topicEvents.forEach((topic) => {
    const scrapCountAtCreation = scrapDates.filter((date) => date <= topic.createdAt).length;
    milestones.push({
      date: topic.createdAt,
      scrapCount: scrapCountAtCreation,
      tier: tierFromScrapCount(scrapCountAtCreation),
      topicIds: topicIdsAsOf(topic.createdAt),
      label: 'Topic 생성',
      caption: `"${topic.name}" Topic이 생겼습니다.`,
    });
  });

  milestones.sort((a, b) => a.date.localeCompare(b.date));

  const currentScrapCount = island.scraps.length;
  const currentTier = tierFromScrapCount(currentScrapCount);
  milestones.push({
    date: new Date().toISOString(),
    scrapCount: currentScrapCount,
    tier: currentTier,
    topicIds: island.topics.map((topic) => topic.id).sort((a, b) => a - b),
    label: '현재',
    caption: `지금 ${TIER_LABELS[currentTier]} · 스크랩 ${currentScrapCount}개 · Topic ${island.topics.length}개`,
  });

  return milestones;
}

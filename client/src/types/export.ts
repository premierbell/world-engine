export interface IslandExport {
  id: number;
  name: string;
  x: number | null;
  y: number | null;
  embedding: number[];
}

export interface TopicExport {
  id: number;
  islandId: number;
  name: string;
  createdAt: string;
}

export interface ScrapExport {
  id: number;
  url: string;
  title: string | null;
  content: string | null;
  summary: string | null;
  sourceType: string | null;
  fallbackLevel: string | null;
  failureReason: string | null;
  userContext: string | null;
  islandId: number | null;
  topicId: number | null;
  recommendedIslandId: number | null;
  createdAt: string;
  embedding: number[] | null;
}

export interface WorldExportResponse {
  exportedAt: string;
  version: number;
  islands: IslandExport[];
  topics: TopicExport[];
  scraps: ScrapExport[];
}

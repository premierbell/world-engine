export type SourceType =
  | 'ARTICLE'
  | 'NAVER_BLOG'
  | 'NAMUWIKI'
  | 'GITHUB'
  | 'YOUTUBE'
  | 'PDF'
  | 'NOTION'
  | 'UNKNOWN';

export type FallbackLevel =
  | 'DIRECT_EXTRACTION'
  | 'OPEN_GRAPH_ONLY'
  | 'SEARCH_SNIPPET'
  | 'USER_INPUT'
  | 'EXTRACTION_FAILED';

export type FailureReason =
  | 'NONE'
  | 'ROBOTS_BLOCKED'
  | 'NETWORK_ERROR'
  | 'TIMEOUT'
  | 'UNSUPPORTED_SOURCE'
  | 'EMPTY_CONTENT'
  | 'LOGIN_REQUIRED';

export type ExtractionStatus = 'SUCCESS' | 'PARTIAL' | 'FAILED';

export interface ScrapSummary {
  id: number;
  url: string;
  title: string;
  islandId: number | null;
  wasCorrected: boolean;
  createdAt: string;
}

export interface ScrapDetail {
  id: number;
  url: string;
  title: string;
  summary: string | null;
  sourceType: SourceType;
  fallbackLevel: FallbackLevel;
  failureReason: FailureReason | null;
  userContext: string | null;
  islandId: number | null;
  recommendedIslandId: number | null;
  wasCorrected: boolean;
  createdAt: string;
}

export interface IslandRecommendation {
  islandId: number;
  islandName: string;
  llmScore: number;
}

export interface ScrapCreateResponse {
  scrapId: number;
  title: string;
  status: ExtractionStatus;
  failureReason: FailureReason | null;
  recommendations: IslandRecommendation[];
}

export interface ScrapConfirmResponse {
  scrapId: number;
  islandId: number;
  islandName: string;
}

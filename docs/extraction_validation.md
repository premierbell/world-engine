# Extraction Validation (Baseline)

> `docs/content_extraction.md`가 "설계"라면, 이 문서는 그 설계가 실제
> 데이터에서 어느 정도 성능을 냈는지 기록하는 검증 문서다. V0의
> "가설보다 데이터로 결정한다" 원칙을 V1에도 그대로 적용한다.

## 테스트 데이터

Round 1(`docs/research_phase_2_rq10-0.md`)에서 쓴 사용자 본인의 실제
스크랩 URL 25개(`experiments/real_user_organization/round1.json`,
개인 데이터라 `.gitignore` 대상). `ContentExtractionKpiLiveTest`가
`ContentExtractionService`(5개 전략 전부 연결)로 이 25개를 그대로
재현한다.

측정일: 2026-07-22

## 결과

| 지표 | 값 |
|---|---|
| Success Rate (DIRECT_EXTRACTION + OPEN_GRAPH_ONLY) | **88.0%** (22/25) |
| Average Content Length (DIRECT_EXTRACTION) | 5,961자 |

**Fallback Distribution**

| Level | 건수 |
|---|---|
| DIRECT_EXTRACTION | 22 (88.0%) |
| OPEN_GRAPH_ONLY | 0 |
| SEARCH_SNIPPET | 0(미구현) |
| USER_INPUT | 0(미구현) |
| EXTRACTION_FAILED | 3 (12.0%) |

**SourceType별 (= Strategy Hit Rate)**

| SourceType | Hit | Success |
|---|---|---|
| ARTICLE | 14/25 | 12/14 (86%) |
| NAVER_BLOG | 9/25 | **9/9 (100%)** |
| PDF | 1/25 | 1/1 (100%) |
| UNKNOWN | 1/25 | 0/1 |
| GITHUB | 0/25 | - |
| YOUTUBE | 0/25 | - |

**Failure Reasons**: `ROBOTS_BLOCKED` 1, `NETWORK_ERROR` 1,
`UNSUPPORTED_SOURCE` 1.

## 실패 원인 분석

`UNSUPPORTED_SOURCE` 1건은 **진짜 사이트 접근 문제가 아니다** -
`round1.json`에 저장된 URL 하나(namu.wiki 항목)에 인코딩되지 않은
공백이 그대로 들어있어서 `new URI(...)` 파싱 자체가 실패했다. 데이터
정합성 문제이지 Extraction 전략의 결함이 아니다.

남은 `ROBOTS_BLOCKED`/`NETWORK_ERROR` 각 1건은 전용 전략이 없는
사이트(추정: namu.wiki 계열 - `NaverBlogExtractionStrategy`는
`blog.naver.com`만 처리하고, namu.wiki는 `ArticleExtractionStrategy`
(범용 fallback)가 그대로 시도하다 막힌 것으로 보인다.

## V1 판단

**검색 스니펫 fallback은 지금 단계에서 필수가 아니다.** 88%라는
Success Rate는 이미 높고, 남은 실패의 대부분이 (a) 데이터 인코딩
결함(실제 배포 시 URL을 제대로 인코딩하면 사라짐)과 (b) namu.wiki
한 사이트로 좁혀진다 - 이건 외부 검색 API를 새로 붙이는 것보다
`NaverBlogExtractionStrategy`처럼 namu.wiki 전용 전략을 하나 더
만드는 게 훨씬 싸고 정확한 해결책일 가능성이 높다. 검색 API 키
발급·쿼터 관리라는 운영 복잡도를 지금 감수할 근거가 부족하다.

**Playwright(JS 렌더링)도 필요 없다** - 이번 25개 중 JS 렌더링이
필요해서 실패한 사례는 관측되지 않았다.

**Python 마이크로서비스 분리도 필요 없다** - Java 생태계(jsoup+
readability4j+PDFBox)만으로 88%가 나왔고, `content_extraction.md`가
잠정 목표로 제시했던 70%를 넘었다.

**표본 한계**: N=25, 사용자 1명의 스크랩. GitHub/YouTube가 0건이라
그 두 전략의 실제 성공률은 이번 baseline에 반영되지 않았다(별도
live 테스트에서는 각각 검증됨). 표본이 늘어나면 이 판단은 다시
검증해야 한다.

## 다음

- (낮은 우선순위, 증거 생기면) `NamuWikiExtractionStrategy` 추가 검토
- URL 저장 시점에 인코딩 정규화(`URLEncoder`/`URI` 4-argument 생성자
  사용 등) - Extraction 이전 단계의 개선 과제
- Extraction은 여기서 baseline을 확보했으니, 다음은 AI 추천
  파이프라인(Embedding/Cosine/LLM Rerank)으로 넘어갈 수 있음

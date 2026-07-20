# Content Extraction Design

> `docs/v1_design.md`의 "Open Engineering Risk: Content Extraction"을
> 구체화하는 문서. AI 추천 파이프라인(Embedding/Cosine/LLM Rerank)보다
> 먼저 구현한다 - 뒤 단계 전부가 여기서 나오는 `ExtractionResult`의
> 품질에 의존하기 때문이다.

## 스택 결정

**Java/Spring**을 기본 가정으로 설계한다 - 다른 포트폴리오 프로젝트
(NewsMailer, BuzzerBidder, Notification Platform, MotiPeople)와
일관된 스토리를 만들기 위함이고, 이 프로젝트의 AI 사용 방식(모델을
직접 학습시키는 게 아니라 Embedding/LLM API를 호출하는 것)은 언어
생태계에 종속되지 않아서 Python을 유지할 이유가 크지 않다.

**분리 기준**: Java 생태계(jsoup + readability4j 등)로 검증했을 때
품질이 명확히 부족하면(예: 성공률이 목표치를 못 넘기거나, 특정
플랫폼군이 계속 실패하면) 그때 Extraction만 별도 Python
마이크로서비스로 분리한다. 처음부터 다중 언어로 시작하지 않는다.

## ExtractionResult

```java
public record ExtractionResult(
    ExtractionStatus status,
    String title,
    String content,
    String summaryCandidate,
    SourceType sourceType,
    FallbackLevel fallbackLevel,
    FailureReason failureReason
) {}

public enum ExtractionStatus { SUCCESS, PARTIAL, FAILED }

public enum SourceType {
    ARTICLE,     // 일반 기사/블로그(티스토리/브런치/Notion 등 정적 HTML 포함)
    NAVER_BLOG,
    NAMUWIKI,
    GITHUB,
    YOUTUBE,
    PDF,
    NOTION,
    UNKNOWN
}

/** 숫자가 클수록 정보 손실이 크다 - 로그/통계에서 등급으로 취급한다. */
public enum FallbackLevel {
    DIRECT_EXTRACTION(0),  // 본문 직접 추출 성공
    OPEN_GRAPH_ONLY(1),    // og:title/og:description만 확보
    SEARCH_SNIPPET(2),     // 검색 API 스니펫으로 대체
    USER_INPUT(3),         // 사용자가 직접 한 줄 입력(자동 실패 후)
    EXTRACTION_FAILED(4);  // 아무것도 확보 못 함

    private final int level;
    FallbackLevel(int level) { this.level = level; }
}

public enum FailureReason {
    NONE,                // 실패 아님
    ROBOTS_BLOCKED,      // robots.txt 또는 봇 차단으로 추정되는 거부(403 등)
    NETWORK_ERROR,       // 연결 실패, DNS 오류 등
    TIMEOUT,
    UNSUPPORTED_SOURCE,  // SourceType 자체를 처리할 전략이 없음
    EMPTY_CONTENT,       // 요청은 성공했지만 추출된 본문이 비어 있음(SPA 등)
    LOGIN_REQUIRED        // 로그인/Paywall로 추정
}
```

`status=FAILED`인 경우(`fallbackLevel=EXTRACTION_FAILED`) 뒤
파이프라인(Summary/Embedding/추천)은 이 스크랩을 건너뛰고 사용자에게
"본문을 못 가져왔어요, 직접 한 줄 설명해주시겠어요?"로 대체한다
(`fallbackLevel=USER_INPUT`) - Round 1.5에서 검증된 것처럼 사용자의
직접 입력이 자동 추출보다 항상 못한 건 아니다.

`failureReason`은 실패했을 때만이 아니라 fallback이 발생했을 때도
기록한다 - "네이버는 ROBOTS_BLOCKED가 많은가?", "GitHub는 거의 항상
DIRECT_EXTRACTION인가?", "TIMEOUT이 특정 소스에 몰리는가?" 같은
운영 지표를 나중에 뽑기 위함(아래 "품질 지표" 참고).

## 플랫폼별 처리 전략

| 소스 유형 | 추출 방식 | 라이브러리/방법 | Fallback |
|---|---|---|---|
| 일반 기사/블로그(티스토리/브런치/Notion 포함) | jsoup으로 HTML fetch → readability4j로 본문 추출 - 대체로 정적 HTML | jsoup + readability4j | Open Graph 태그(og:title/og:description) |
| 네이버 블로그 | 겉 URL은 iframe(`mainFrame`) 래퍼 - 실제 본문은 내부 `PostView.naver?blogId=...&logNo=...` URL에 있음, 이 URL을 먼저 찾아서 재요청 | jsoup(2단계 요청) | Open Graph → 검색 스니펫 |
| 나무위키 | 봇 차단이 강함(요청 패턴/User-Agent 기반 추정) | jsoup(User-Agent 조정) 우선 시도 | 실패 시 검색 스니펫으로 바로 전환 |
| GitHub | README를 API로 직접 요청 - HTML 파싱보다 훨씬 안정적 | `raw.githubusercontent.com` 또는 GitHub REST API `/repos/{owner}/{repo}/readme` | Repository description(API) |
| YouTube | 자막(timedtext) 또는 영상 설명 | YouTube Data API | 제목만(oEmbed) |
| PDF | 텍스트 레이어 직접 추출 | Apache PDFBox | 실패 시(스캔본 등) 파일명/제목만 |
| JS 렌더링 필요(SPA) | 위 방법으로 본문이 비어있을 때만 재시도(비용이 크므로 최후 수단) | Playwright for Java | Open Graph → 검색 스니펫 |

**봇 차단(naver/namu.wiki)과 JS 렌더링은 서로 다른 문제**라는 걸
구분해서 접근한다 - Round 1에서 Claude(WebFetch)가 겪은 실패는 대부분
전자였고, Playwright 같은 무거운 대응이 항상 필요한 게 아니다. 먼저
User-Agent/헤더 조정 + 2단계 요청(네이버 블로그 iframe 패턴) 같은
가벼운 방법을 시도하고, 그래도 안 되면 검색 스니펫으로 넘어간다.

## 처리 순서

1. URL 정규화 + `SourceType` 판별(호스트명 기반 라우팅)
2. `SourceType`별 전용 전략 시도(위 표)
3. 실패 시 Open Graph 메타태그로 격하
4. 그마저 실패하면 검색 API 스니펫으로 격하
5. 전부 실패하면 `status=FAILED` - 사용자에게 직접 입력 요청

## 품질 지표 (KPI)

Round 1은 25개 중 9개 직접 성공(36%)이었다 - 이건 **일반 목적
스크래퍼(WebFetch) 기준**이지, 위 전략(플랫폼별 라우팅 + Open Graph
fallback + 네이버 블로그 2단계 요청)을 적용한 기준이 아니다. 구현 후
같은 25개(또는 새 표본)로 재현해서 아래 네 지표를 측정한다:

- **Success Rate** - `FallbackLevel <= OPEN_GRAPH_ONLY`(DIRECT_EXTRACTION
  + OPEN_GRAPH_ONLY) 비율. 목표치(예: 70% 이상)를 넘는지가 Python
  마이크로서비스 분리 여부를 결정하는 근거가 된다.
- **Fallback Distribution** - `FallbackLevel`별 분포(0~4 각각 몇 %인가).
  전체 성공률이 같아도 "대부분 DIRECT_EXTRACTION"과 "대부분 SEARCH_SNIPPET"
  은 품질이 다르다.
- **SourceType Success Rate** - 소스 유형별 성공률. "네이버는
  ROBOTS_BLOCKED가 많은가", "GitHub는 거의 항상 성공하는가"처럼
  어디를 더 개선해야 할지 알려준다.
- **Average Content Length** - `DIRECT_EXTRACTION`으로 확보한 본문의
  평균 길이. 짧으면(예: 메뉴/광고만 걸린 경우) 실제로는 실패에 가까운
  성공일 수 있다.

## Non-goals

의도적으로 다루지 않는다 - 범위를 넘는 접근은 하지 않는다:

- robots.txt 우회
- 로그인 세션 자동화(자동 로그인해서 콘텐츠 확보)
- CAPTCHA 우회
- Paywall 우회
- 위 항목에 해당하는 방식의 스크래핑 전반

이런 경우는 `LOGIN_REQUIRED`/`ROBOTS_BLOCKED`로 분류하고 fallback
(검색 스니펫 → 사용자 직접 입력)으로 넘어간다 - 억지로 뚫으려 하지
않는다.

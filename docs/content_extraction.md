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
| YouTube | watch 페이지 HTML에서 `og:title`/`og:description`(영상 설명) 추출 - 일반 기사와 같은 jsoup 패턴 | jsoup | oEmbed(제목만) |
| PDF | 텍스트 레이어 직접 추출 | Apache PDFBox | 실패 시(스캔본 등) 파일명/제목만 |
| JS 렌더링 필요(SPA) | 위 방법으로 본문이 비어있을 때만 재시도(비용이 크므로 최후 수단) | Playwright for Java | Open Graph → 검색 스니펫 |

**봇 차단(naver/namu.wiki)과 JS 렌더링은 서로 다른 문제**라는 걸
구분해서 접근한다 - Round 1에서 Claude(WebFetch)가 겪은 실패는 대부분
전자였고, Playwright 같은 무거운 대응이 항상 필요한 게 아니다. 먼저
User-Agent/헤더 조정 + 2단계 요청(네이버 블로그 iframe 패턴) 같은
가벼운 방법을 시도하고, 그래도 안 되면 검색 스니펫으로 넘어간다.

**V1에서는 YouTube Data API를 쓰지 않는다.** API 키를 요구하고
운영 복잡도(키 발급/쿼터 관리)를 늘리기 때문이다. 실제로 확인해보니
watch 페이지 HTML 자체에 `og:description`으로 영상 설명이 들어있어서,
다른 HTML 기반 전략과 동일한 패턴(jsoup)으로 처리할 수 있다. 자막
(timedtext)은 비공식 엔드포인트에 언어 선택·자동생성 여부·페이지 내부
JSON 구조 변경 리스크까지 겹쳐서 복잡도가 급격히 늘어난다 - 향후
확장 범위로 미룬다. 지금까지의 V1 원칙과도 일치한다: 완전 자동
분류 대신 AI 추천+사용자 확인, Playwright 대신 HTML 기반 추출
우선, Python 마이크로서비스 대신 Java 단일 서비스 우선 - "가장
단순하면서 충분한 방법을 기본값으로 채택한다."

## 처리 순서

1. URL 정규화 + `SourceType` 판별(호스트명 기반 라우팅)
2. `SourceType`별 전용 전략 시도(위 표)
3. 실패 시 Open Graph 메타태그로 격하
4. 그마저 실패하면 검색 API 스니펫으로 격하
5. 전부 실패하면 `status=FAILED` - 사용자에게 직접 입력 요청

## 품질 지표 (KPI)

> **측정 완료 - `docs/extraction_validation.md` 참고.** Round 1은 25개
> 중 9개 직접 성공(36%, WebFetch 기준)이었는데, 5개 전략을 실제
> 구현하고 같은 25개로 재현하니 **88%**로 올랐다. 검색 스니펫
> fallback/Playwright/Python 마이크로서비스 분리 전부 "지금은 불필요"
> 로 결론 - 근거는 baseline 문서 참고.

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

## Known Limitation: 대형 오픈마켓 봇 차단 (V1 실사용에서 확인, 2026-07-26)

V1 실사용 중 쿠팡/지마켓/네이버 스마트스토어/다나와 URL을 스크랩해보니
전부 `ROBOTS_BLOCKED`로 실패했다. 반면 브랜드 자사몰(삼성닷컴, LG트윈스
어패럴샵 등)은 정상 동작한다 - "쇼핑몰이라서" 안 되는 게 아니라, 대형
오픈마켓/가격비교 사이트 쪽이 봇 차단이 유독 강하다는 뜻이다.

다나와 사례가 특히 확인됨: 동일한 User-Agent로 `curl`은 200을 받지만
jsoup(Java)은 403을 받는다 - 단순 UA 체크가 아니라 요청 패턴(TLS/HTTP
클라이언트 핑거프린팅 등)으로 구분하는 것으로 추정된다. 이런 수준의
차단은 jsoup 옵션 조정으로 안정적으로 우회되지 않는다.

**결정: 우회 시도 안 함.** "특정 사이트 하나를 뚫기 위한" 예외 처리는
이 프로젝트가 계속 피해온 방향과 맞지 않고, `robots.txt 우회`를 이미
Non-goals로 명시한 것과도 일치한다. `ROBOTS_BLOCKED`로 정직하게
분류하고 fallback(사용자 직접 입력) 흐름으로 넘어간다. Search Snippet
fallback을 도입하게 되면(아직 근거 부족, 미도입) 이 케이스들이 먼저
혜택을 볼 후보다.

## ExtractionQualityEvaluator - 운영성 보일러플레이트 감지 (2026-07-28)

`ArticleExtractionStrategy`가 길이 조건은 통과하지만 실제로는 본문이
아닌 텍스트(반품/배송 안내, 결제 정책 등 페이지의 "운영 정보" 영역)를
readability4j가 잘못 골라오는 사례를 V1 실사용에서 4건 확인했다
(서로 다른 쇼핑몰 템플릿 2개: KT위즈샵/LG트윈스샵의 "교환 및
반품" 계열, SSG백화점/SSG몰의 "구매혜택/배송정보" 계열). 이 상태로
저장되면 실제 내용과 무관한 다른 스크랩과 embedding이 가까워져서
추천이 조용히 틀려진다(예: 와이셔츠 상품 페이지가 "야구" Island와
0.90으로 매칭 - 둘 다 반품/배송 안내문일 뿐인데 서로 비슷하다고 오판).

**감지 방식은 URL/도메인이 아니라 추출된 텍스트 자체를 본다** -
"배송/교환/반품/환불/쿠폰/적립/상품번호/모델번호/결제/무료배송/택배"
같은 운영 어휘가 본문 앞부분(500자)에 일정 개수(3개) 이상 몰려있으면
"실제 읽을거리가 아니다"로 보고 기존 Open Graph fallback으로
넘긴다. 도메인 화이트리스트나 URL 패턴에 의존하지 않는 이유: 이런
페이지가 나오는 사이트가 무한하고(대형 오픈마켓뿐 아니라 개별
브랜드샵도 포함) 계속 목록을 늘리는 사례별 대응이 되기 쉽다.

이건 "쇼핑몰 지원 기능"이 아니라 **본문 대신 운영성 보일러플레이트가
선택되는 일반적인 실패를 감지하는 품질 평가 개선**으로 남겨둔다 -
나중에 로그인 페이지, 공지사항 템플릿, 에러 페이지 같은 다른 종류의
보일러플레이트에도 같은 원리를 적용할 수 있다.

Round 1의 실제 사용자 URL 25개(전부 쇼핑몰 아님)로 재측정 - 이
가드레일로 인한 오탐(`EMPTY_CONTENT`) 0건, 성공률 하락은 전부
`ROBOTS_BLOCKED`(사이트 쪽의 시점별 차단 변화, 이 변경과 무관)에서만
발생.

**Future Idea (아직 안 만듦): Commerce 전용 Strategy.** 쇼핑몰
상품 페이지는 본문 전체보다 "상품명 한 줄"이 관심사 추론에 더
유용할 수 있다는 아이디어가 나왔다 - GitHub/YouTube가 이미 "최대한
많은 텍스트"가 아니라 "관심사를 표현하는 최소 신호"만 뽑는 것과
같은 결. 다만 GitHub/YouTube는 도메인이 하나뿐이라 라우팅이
간단하지만, 쇼핑몰은 도메인이 무한해서 "이 URL이 커머스 페이지인가"
를 안정적으로 판별하는 문제가 먼저 풀려야 한다(도메인 목록도,
URL 패턴도 완벽하지 않음) - 이 라우팅 문제가 풀리기 전까지는
착수하지 않는다.

## Extraction Failure Taxonomy - Playwright 재검토 근거 (V2 실사용, 2026-08-01/02)

V2 실사용 중 "경제, 재테크" Island에서 Topic 후보가 하나도 안 묶이는
문제를 진단하다가 발견. 처음엔 "Playwright를 도입해야 하나?"로
질문을 세웠는데, 실제 사례를 유형별로 분류해보니 **Extraction 실패가
하나의 원인이 아니라 여러 문제의 조합**이라는 게 드러나서 질문 자체를
정정했다.

경제/재테크 6건 + 여행/바이오 5건(전체 120개 스윕에서 발견, 뒤 섹션
참고), 총 11건을 원인별로 분류:

| 유형 | 원인 | 해결책 | 건수 |
|---|---|---|---|
| A. 정적 골격만 있고 실제 콘텐츠는 JS로만 렌더링 | jsoup이 본문에 아예 도달 못 함 | Playwright | 8건 |
| B. 본문이 짧아 Open Graph로 정상 폴백 | 이미 해결됨(`ExtractionQualityEvaluator`) | 유지 | 1건 |
| C. 본문은 실제로 잡혔지만 구분자 손실로 파편화 | readability4j `getTextContent()`의 블록 경계 처리 방식(추정) | Playwright와 무관, 별도 조사 | 1건 |

**A(8/11) 검증**: `claude-in-chrome`으로 63빌딩(`63building.co.kr`)과
뱅크샐러드 적금 차트를 실제 렌더링해서 jsoup 추출 결과와 직접 비교 -
2/2 전부 jsoup이 놓친 실제 콘텐츠(시설 소개, 상품·금리 목록)가
그대로 존재함을 확인. 페이지 공통 요소(주소/사업자정보/저작권/약관
등)는 정적으로 서빙되고, 페이지 고유 콘텐츠만 JS로 주입되는 구조로
보인다 - 이게 여행/바이오에서 나온 boilerplate 5건(나무위키 편집
정책, 관광공식사이트 쿠키안내, 기관 홈페이지 개인정보방침 등)에도
공통되는 패턴.

**C(1/11) 발견**: "신용카드 추천 발급" 스크랩(아정당)이 jsoup으로는
파편화된 텍스트("최대 86만원KB국민카드 통신/렌탈 할인아정당 우리카드
최대 76만원현대카드...")로 나와서 처음엔 boilerplate로 의심했으나,
실제 렌더링해보니 **같은 카드 혜택 정보가 실제로 존재**함(줄바꿈이
살아있는 정상적인 목록 형태) - 즉 boilerplate가 아니라 "콘텐츠는
잡혔는데 형식이 깨진" 별개의 실패 유형. 처음에는 "jsoup의
`element.text()`를 `wholeText()`/`ownText()`로 바꾸면 해결"로
추정했으나, 이 프로젝트의 `ArticleExtractionStrategy`는 jsoup의
텍스트 메서드를 직접 안 쓰고 **readability4j의
`article.getTextContent()`**를 쓰고 있음을 코드로 확인 - 그러니
readability4j가 블록 요소(div/li 등) 경계를 어떻게 처리하는지부터
조사해야 정확한 해법을 알 수 있다.

**C 조사 결과(2026-08-02)**: `Article`은 `getTextContent()`(공백만
구분) 외에 정제된 본문을 jsoup `Element`로 그대로 반환하는
`getArticleContent()`도 제공한다(`javap`으로 API 확인). 임시 라이브
테스트(`./gradlew liveTest`, 실행 후 즉시 삭제)로 아정당 페이지에
같은 HTML을 놓고 두 방식을 직접 비교:

- 기존(`getTextContent()`): `"최대 86만원KB국민카드 통신/렌탈 할인아정당 우리카드 최대 76만원현대카드..."` - 항목 경계가 안 보임.
- 새 방식(`getArticleContent()`를 직접 순회하며 블록 태그(div/p/li/br/h1~h4/tr 등) 뒤에 개행 삽입): `"최대 86만원 KB국민카드\n통신/렌탈 할인 아정당 우리카드\n최대 76만원 현대카드\n..."` - 카드명/금액이 줄 단위로 분리되고 문장 경계도 살아남.

**결론**: 유형 C는 **Playwright 없이, 텍스트 추출 방식만 바꿔서
해결 가능**하다는 근거 확보. `ArticleExtractionStrategy.
extractMainContent()`에서 `article.getTextContent()` 대신
`article.getArticleContent()`를 받아 블록 경계 인식 텍스트 변환을
적용하는 방향으로 다음에 구현. 비용은 낮음(새 의존성 없음, 순회
로직 하나 추가) - 다만 이 변경이 다른 소스(나무위키/네이버블로그 등
이미 잘 되던 것들)의 포맷을 망가뜨리지 않는지 회귀 확인은 필요.

**핵심 정정**: "Playwright를 넣으면 Extraction 문제가 해결된다"가
아니라 **"Playwright는 유형 A만 해결한다"**가 정확하다. 유형 C는
Playwright를 넣어도 같은 렌더링 텍스트 추출 방식이면 그대로 남을
가능성이 크다 - 문제가 종류별로 분리된 건 오히려 좋은 신호(각각
독립적으로, 더 안전하게 고칠 수 있음).

**트리거 조건은 아직 미정**: 본문 길이 기반 트리거는 이번 조사로
사실상 기각됨 - 유형 A의 boilerplate 중 다수(700~800자)가 기존
`extraction.min-content-length=50` 기준을 훌쩍 넘어서, "짧으면
Playwright" 규칙으로는 대부분을 못 잡는다. 도메인 화이트리스트(정확하지만
계속 추가해야 함) vs 키워드 밀도 기반(`ExtractionQualityEvaluator`의
이커머스 운영 어휘 패턴과 같은 방식이지만 법적/정책 어휘로 확장 -
다만 "개인정보"라는 단어가 있다고 항상 boilerplate는 아니라는 반례
가능성 있음, 예: 개인정보보호법 해설 문서) 중 뭐가 나을지는 추가
조사 필요.

**우선순위 결정(2026-08-02)**: ① 이 분류를 Finding으로 확정(본
섹션) → ② 유형 C(readability4j 텍스트 추출 방식) 조사 - Playwright
없이도 해결 가능성 있고 비용이 낮아 보임(다만 정확한 저비용 여부는
조사 후 확정) → ③ Playwright는 유형 A만 대상으로 설계, "항상
Playwright"가 아니라 "jsoup 실패로 판단될 때만" 폴백하는 구조를
목표로 하되 트리거 조건은 별도 연구.

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

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
| D. 렌더링(정적이든 Playwright든)과 무관하게 readability4j가 "decoy 블록"을 본문으로 고름 | Playwright 문제 아님 - 법적고지/반품안내/리뷰위젯 placeholder/쿠키동의 배너처럼 실콘텐츠보다 짧고 문장처럼 생긴 UI 블록에 낚임. **페이지 카테고리(랜딩/쇼핑/기사)와는 무관함**(아래 Boundary Study 참고) | 표본 부족, 우선 로그로 관찰만(구현 완료 2026-08-02) | 확인 3건(63빌딩/KT위즈샵/나이키) |
| E. Playwright가 원래 jsoup 결과보다 더 나쁜 걸 돌려줄 위험(Fallback Regression) | 봇 차단 페이지/로그인 페이지/빈 SPA shell 등을 "성공"으로 오판할 수 있음 | 봇 차단 시그니처 감지로 예방 조치(구현 완료 2026-08-02, `PlaywrightExtractionStrategy.looksLikeBotBlock()`) | 실사용 재현은 아직 없음(나무위키 조사 중 가능성만 확인, 아래 참고) |

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

**우선순위 결정(2026-08-02)**: ① 이 분류를 Finding으로 확정(본
섹션) → ② 유형 C(readability4j 텍스트 추출 방식) 조사 - Playwright
없이도 해결 가능성 있고 비용이 낮아 보임(다만 정확한 저비용 여부는
조사 후 확정) → ③ Playwright는 유형 A만 대상으로 설계, "항상
Playwright"가 아니라 "jsoup 실패로 판단될 때만" 폴백하는 구조를
목표로 하되 트리거 조건은 별도 연구.

### Trigger Evaluation - 언제 Playwright를 돌릴 것인가 (2026-08-02)

유형 A(8건)를 잡아내되 유형 C(1건, 이미 별도 해결)나 정상 콘텐츠는
건드리지 않는 트리거 조건을 실제 데이터로 비교했다.

| 방법 | 근거 | 결과 |
|---|---|---|
| 본문 길이 (`min-content-length` 확장) | 유형 A 대부분(700~800자)이 이미 기존 임계값(50자)을 훌쩍 넘음 | 재현율 매우 낮음 → 기각 |
| 도메인 화이트리스트 | boilerplate 9건의 실제 도메인을 확인 | 9건 중 8개가 서로 다른 도메인(`pay.naver.com`만 2건) → 유지보수 비용 대비 커버리지 부족 → 기각 |
| 키워드 밀도, threshold=3 (기존 이커머스 패턴 그대로 이식) | `ExtractionQualityEvaluator`의 `COMMERCE_OPERATIONAL_KEYWORDS`/threshold=3 패턴을 법적/정책 어휘로 확장 | 법적 문구는 보통 한 번씩만 등장(링크 텍스트)해서 재현율 2/9로 부족 → 기각 |
| **키워드 밀도, threshold=1 (500자 윈도우)** | 아래 참고 | **현재 최선의 근거로 채택 후보** |

**채택 후보(구현됨, `ExtractionQualityEvaluator.looksLikeLegalBoilerplate()`)**:
본문 앞 500자 윈도우에서 법적/정책 키워드가 1개 이상 매치되면
boilerplate 의심으로 플래그. 키워드 목록: `개인정보처리방침`, `약관`,
`저작권`, `All rights reserved`, `사업자등록번호`, `통신판매업`,
`통신판매중개자`, `Copyright`, `쿠키를`, `쿠키 수집`, `개인정보 처리방침`.
(`쿠키`를 단독으로 넣었더니 "세**쿠키**누맙" 같은 약물 성분명의 부분
문자열에 우연히 매치되는 오탐이 나와서 `쿠키를`/`쿠키 수집`처럼
구체적인 구문으로 교체함 - 단순 `contains()` 매칭의 함정.)

**실험 결과**:
- boilerplate 9건 → 처음엔 8건 탐지(재현율 89%, `이용약관`만 넣었을 때). 유일한 미탐지였던 121번(`card-search.naver.com`)의 원문을 다시 보니 "상품설명서와 **약관**을 읽어보시기 바랍니다"처럼 복합어가 아닌 단독 `약관`이 있었음 - 키워드를 `이용약관` → `약관`으로 넓히자 9/9(100%)까지 올라감.
- 정상 DB 전체(101 + 15건, 사실상 전수 스윕) → `약관`으로 넓힌 뒤에도 오탐 0건.
- 추가로 DB 밖에서 의도적으로 가져온 정상 문서 3건(법률신문 개인정보보호법 개정안 기사, SAS 코리아 GDPR 총정리 블로그, 위키백과 "HTTP 쿠키" 문서)으로 스트레스 테스트 → `약관` 포함 버전으로도 오탐 0건. (위키백과 문서는 본문에 "쿠키를"이 실제로 등장하지만 약 1400자 지점이라 500자 윈도우 밖 - 윈도우 크기 자체가 실질적으로 보호 역할을 하고 있음을 확인.)
- **유보**: `약관`은 다른 키워드보다 오탐 위험이 상대적으로 높다 - 보험약관/여행약관/통신약관처럼 진짜 뉴스·문서에도 흔히 등장하는 일반 단어라서, 표본이 늘어나면 다른 키워드보다 먼저 오탐을 낼 가능성이 있다. 지금까지의 스트레스 테스트에서는 걸리지 않았지만, 운영 중 재관찰이 필요한 항목으로 남겨둔다.

**표본 규모에 대한 유보**: boilerplate 9건 + 정상 120건 + 스트레스
테스트 3건은 프로토타입 단계에서는 의미 있는 근거지만 "항상 맞는다"를
보장할 정도는 아니다. 그래서 이 방식은 "채택"이 아니라 **"현재까지
확보한 데이터 기준 최선의 근거"**로 남긴다 - 반례가 새로 나오면
언제든 갱신될 수 있는 잠정적 결론.

**Known limitation**: 법적/정책 키워드가 아예 없는 JS placeholder
케이스(예: 121번 `card-search.naver.com`)는 이 방식으로 원천적으로
탐지 불가능하다. 이런 케이스를 위한 별도 폴백(예: 본문이 사이트
공통 요소로만 채워졌는지를 판단하는 다른 신호)이 필요하며, 이번
실험은 "Playwright 없이 문제를 해결했다"가 아니라 **"Playwright를
언제 실행할지"**를 좁힌 것뿐이라는 점을 명확히 해둔다.

**설계 방향**: `jsoup 추출 → 500자 윈도우 키워드 검사 → boilerplate
신호 발견 시에만 Playwright로 재추출` 구조. 모든 스크랩에 Playwright를
무조건 돌리는 게 아니라 필요한 경우에만 실행하는 조건을 데이터로
설계했다는 점이 이번 조사의 핵심 성과 - 성능/유지보수 측면에서도
근거가 되는 아키텍처 결정.

### 구현 및 실사용 검증 - 유형 D 발견 (2026-08-02)

`PlaywrightExtractionStrategy` 구현, `ExtractionQualityEvaluator.
looksLikeLegalBoilerplate()` 연결, `ArticleExtractionStrategy`에
Playwright 폴백 분기까지 연결한 뒤 실제 서버를 띄워 63빌딩 URL로
직접 스크랩해서 검증했다.

**1차 시도**: Playwright 트리거는 정상 작동(`Playwright fallback
triggered` 로그 확인)했으나, `Playwright.create()`가 최초 실행 시
Firefox/WebKit 바이너리까지 자동 다운로드(176MB)하면서 15초
타임아웃을 넘겨 실패 - 기존 jsoup 결과(boilerplate)로 그대로
폴백됨. Playwright 자체 로직 문제는 아니라 재시도로 확인.

**2차 시도(다운로드 완료 후 재시도)**: 여전히 같은 136자 boilerplate가
저장됨 - 그런데 이번엔 실패 로그가 없었다. 즉 `renderedResult.
status() == SUCCESS`로 조용히 반환된 것 - Playwright는 성공했는데
결과가 이상하다는 뜻.

**원인 격리**: 임시 라이브 테스트로 (a) Playwright가 실제로 렌더링한
`body.innerText()`와 (b) 같은 렌더링 HTML에 readability4j를 돌린
결과를 나란히 비교:

- `body.innerText()`: 1241자, 실제 콘텐츠(퐁피두센터, 63 스카이
  피크닉, 브랜드 목록 등) 전부 포함 - **Playwright 렌더링은 완전히
  성공.**
- readability4j `getTextContent()`: 여전히 136자, 예전과 똑같은
  법적 고지 문구만 선택.

**결론**: Playwright는 결백하다. 문제는 readability4j가 "가장 문장다운
텍스트 블록"을 본문으로 고르는 알고리즘인데, 63빌딩처럼 Hero/시설
소개/카드/브랜드/배너로 구성된 **랜딩페이지**에는 애초에 "본문(article)"
개념이 약해서, 유일하게 마침표로 끝나는 긴 문단인 법적 고지 문구를
본문으로 오판한다. jsoup이든 Playwright든 렌더링 방식과 무관하게
readability4j 자체의 한계다. 이를 유형 D로 분류(위 표 참고) - 유형
A(8건)에 포함됐던 63빌딩은 사실 A+D 중첩 사례였던 것으로 재해석.

**지금 취하지 않은 조치**: `body.innerText()` 같은 대체 추출 방식을
바로 추가하지 않았다. 표본이 63빌딩 1건뿐이라 "readability4j가
랜딩페이지에서 항상 실패한다"고 일반화하기엔 이르고, 성급하게
폴백을 쌓기 시작하면(readability4j 실패 시 innerText, 그것도
실패하면 다른 라이브러리...) 끝없는 체인이 될 위험이 있다. 대신
`PlaywrightExtractionStrategy`에 로그 한 줄만 추가:
렌더링 성공 후 결과가 여전히 `looksLikeLegalBoilerplate()`에
걸리면 WARN 로그(`Playwright rendered successfully but
readability4j still picked boilerplate`)를 남긴다. 앞으로 Playwright가
트리거될 때마다 이 로그가 얼마나 자주 뜨는지 관찰해서, 표본이
쌓이면(예: 20건 중 다수가 유형 D면) 그때 readability4j를 대체/보완할지
결정한다 - 지금은 근거 없이 전략을 늘리지 않는다.

### Boundary Study - readability4j는 실제로 어디까지 괜찮은가 (2026-08-02)

실사용 중 KT위즈샵/나이키에서도 유형 D를 추가로 발견(둘 다 jsoup
시점부터 이미 실콘텐츠에 접근 가능했는데 readability4j가 반품안내/
리뷰위젯 placeholder를 골랐음 - Playwright 렌더링 여부와 무관하게
readability4j의 선택이 정적/렌더링 양쪽에서 동일했다는 것까지 확인).
이 3건만 보고 "readability4j를 교체해야 한다"로 일반화하기 전에,
**이 3건 자체가 이미 "의심돼서 조사한" 편향된 표본**이라는 문제를
먼저 인식하고, "성공할 것 같은" 카테고리(블로그/기사/기술문서 10건)와
"실패할 것 같은" 카테고리(랜딩/포털/쇼핑 8건)를 실제 DB의 real
scrap URL로 뽑아 Playwright 렌더링 후 `body.innerText()`와
readability4j 결과를 나란히 비교했다.

**결과**: "카테고리가 성공/실패를 가른다"는 가설은 기각됨.
- 성공 예상군(유효 9건): 8건 성공(velog/tistory/GoogleCloud/naver블로그
  2건/더바이오/약업신문/tistory), 1건 실패(**AWS 공식 문서** - 실콘텐츠
  대신 쿠키 동의 배너 문구를 골랐음, 새로운 decoy 유형)
- 실패 예상군(유효 6건): 3건 성공(**롯데월드타워/무신사/K-NIBRT** - 랜딩·쇼핑
  페이지인데도 readability4j가 실콘텐츠를 제대로 골랐음), 1건 부분성공
  (프로그래머스 - 리스트형 진짜 콘텐츠), 2건 실패(KBO 홈페이지, 한국바이오인력개발센터)

**결론**: readability4j는 생각보다 훨씬 넓은 범위에서 잘 작동한다.
문제는 "페이지 카테고리"가 아니라 **"실콘텐츠보다 짧고 문장처럼
생긴 decoy 블록(법적고지/반품안내/리뷰위젯 placeholder/쿠키동의
배너 등)이 있는가"** - 카테고리와 상관없이 발생할 수 있고, 반대로
카테고리가 위험해 보여도(랜딩페이지, 쇼핑몰) decoy만 없으면 잘 된다.
**readability4j를 교체할 근거는 없다** - 오히려 유지할 근거가 쌓였고,
문제 범위가 "extractor 전체 교체"에서 "decoy 실패 감지와 안전한
폴백"으로 좁혀졌다.

### 나무위키 봇 차단 조사 - 정정 (2026-08-02)

위 Boundary Study 중 나무위키 URL을 Playwright(헤드리스 Chromium)로
렌더링했을 때 실제로 Cloudflare류 봇 차단 페이지("Why have I been
blocked?")가 반환되는 걸 확인했다. 이미 유형 A로 분류된 26번(제주신화월드)
스크랩이 실제로 법적 키워드("저작권")에 걸려 있어, **프로덕션에서
Playwright 폴백이 트리거되면 기존 jsoup 결과보다 더 나쁜 결과(봇
차단 페이지)를 저장할 위험**을 확인 - 처음엔 이걸 "실제 발생한
회귀"로 기록하려 했다.

**재검증 결과 정정**: 같은 URL로 실제 스크랩 API를 다시 호출해서
확인하려 했으나, jsoup의 최초 정적 요청 자체가 이미 403으로 막혀
있어서(같은 세션에서 이 URL을 반복 요청한 영향으로 추정) Playwright
폴백 단계까지 도달하는 E2E 재현에는 실패했다. 즉:
- ❌ "새 방어 코드가 실패했다"는 증거 없음
- ❌ "Playwright fallback까지 실제로 도달했다"는 증거 없음(이번 재검증에서는)
- ✅ namu.wiki가 헤드리스 브라우저를 차단한다는 사실 자체는 확인됨(최초 발견 시점)
- ✅ 방어 로직(`PlaywrightExtractionStrategy.looksLikeBotBlock()` -
  봇 차단 시그니처 문자열 감지 시 `ROBOTS_BLOCKED`로 실패 처리,
  `ArticleExtractionStrategy`가 자동으로 jsoup 결과 유지)은 코드
  리뷰 + 컴파일 확인 수준으로 반영 완료

**정확한 표현**: "나무위키 Playwright fallback 회귀가 실제 발생했다"가
아니라, **"Playwright 환경에서 봇 차단 페이지가 반환될 수 있음을
확인했고, 이에 대한 예방적 방어 로직을 추가했다"**가 맞다. E2E
회귀 재현은 못 했지만, 방어 로직 자체는 실제 관찰(봇 차단 페이지
텍스트)에 근거한 것이라 유지한다 - namu.wiki를 더 붙잡고 재검증을
기다리지는 않기로 함.

**설계 원칙 정리**: 이번 조사로 얻은 가장 큰 결론은 **"Playwright는
무조건적인 upgrade가 아니라, jsoup과 별개인 또 하나의 추출 소스"**라는
점이다. 봇 차단 페이지 외에도 로그인 요구 페이지, 빈 SPA shell,
광고/쿠키 오버레이 등 Playwright 쪽이 오히려 더 나쁠 수 있는 경우가
앞으로도 나올 수 있다 - 그래서 `ArticleExtractionStrategy`는
"Playwright 결과가 명확히 SUCCESS일 때만 채택, 그 외엔 무조건 기존
jsoup 결과 유지"라는 보수적 기본값을 계속 지킨다(품질 점수를 매겨
"더 나은 쪽 선택"하는 정교한 비교 로직은 아직 근거 부족 - 지금은
`ExtractionResult`에 소스/차단여부 메타데이터를 추가하는 것도
보류: 이미 있는 WARN 로그 2줄(decoy 탐지, 봇 차단 탐지)만으로도
Playwright 성공률/폴백 빈도를 관찰하는 목적은 충분히 달성됨 -
다운스트림 계약을 건드리는 새 데이터 클래스는 근거 없이 안 만든다).

### 유형 D의 첫 프로덕션 재현 - 삼성바이오로직스 (2026-08-03)

PR #100 머지 후 실사용(야구/가구/패션/바이오 등에 스크랩 다수 추가)
중 삼성바이오로직스(`samsungbiologics.com/kr`)가 실제 운영 로그에서
유형 D를 재현했다:

```
INFO  Playwright fallback triggered - url=https://samsungbiologics.com/kr, reason=boilerplate_keyword
WARN  Playwright rendered successfully but readability4j still picked boilerplate - url=..., contentLength=1270
```

저장된 content는 회사 소개가 아니라 **쿠키 정책 설명문**("쿠키가
무엇인가요? ... Google Analytics ... 쿠키 설정, 확인 및 거부 방법")
전체였다. 이건 **어제(2026-08-02) 진단 테스트로만 확인했던 유형 D가
처음으로 실제 프로덕션에서, 새로 추가한 WARN 로그를 통해 그대로
재현·관측된 사례**다.

**확정된 사실이 바뀐 지점**: "Playwright를 붙이면 해결될 수도 있다"
(가설) → **"Playwright는 렌더링에 성공해도 readability4j가 decoy를
고르는 경우가 실제 운영에서도 발생한다"**(운영 데이터로 확정). 또한
쿠키 동의/정책 문구가 decoy로 뽑힌 사례가 어제 AWS 공식문서에 이어
**두 번째(삼성바이오로직스)** 나와서, "쿠키 정책이 readability를
속인다"는 하위 패턴 자체는 어느 정도 신뢰할 수 있게 됐다. 다만
63빌딩(법적고지)/KT위즈샵(반품안내)/나이키(리뷰위젯)/삼성바이오(쿠키정책)
네 사례의 공통점이 "실콘텐츠보다 짧고 문장처럼 생김" 정도로만
설명되고, readability4j가 **왜** 특정 블록을 고르는지 알고리즘
차원의 설명은 아직 없다 - 지금 단계에서 새 감지 로직이나 alternative
extractor를 설계하기엔 근거가 아직 부족하다고 판단.

**결정**: 지금은 코드를 더 추가하지 않는다. `PlaywrightExtractionStrategy`의
WARN 로그(`readability4j still picked boilerplate`) 빈도만 계속
관찰한다 - 100건 스크랩 중 WARN이 2건이면 구조를 안 바꿔도 되고,
18건이면 그때 decoy들의 공통 구조를 분석해서 extractor 개선을
검토한다는 기준. 이번 조사에서 가장 중요한 변화는 "문제를 해결하는
코드"가 아니라 **"문제를 실제 운영에서 안정적으로 관찰할 수 있는
체계가 생겼다"**는 것 - 앞으로의 개선은 추측이 아니라 운영 로그
데이터에 기반해 진행할 수 있다.

### Type D 사례 정리 및 관찰 모드 전환 (2026-08-03)

같은 날 실사용을 더 이어가며 대원제약(`daewonpharm.com`)에서 5번째
Type D 사례를 확인했다 - 저장된 content 전체가 이용약관 전문("제
1 장 총 칙 제 1 조 (목적) 이 이용약관...")이었다("약관" 키워드
매치 확인).

**Type D 대표 사례 5건** (같은 근본 원인의 서로 다른 표면):

| 사이트 | decoy로 뽑힌 것 |
|---|---|
| 63빌딩 | 법적 고지(주소/사업자정보) |
| KT위즈샵 | 반품/배송 안내 |
| 나이키 | 리뷰 위젯 placeholder |
| 삼성바이오로직스 | 쿠키 정책 |
| 대원제약 | 이용약관 전문 |

표면적으로는 전부 다른 문구(법적고지/반품/리뷰위젯/쿠키/약관)라
처음엔 별개 문제처럼 보였지만, 공통점은 **"실제 본문보다 UI/정책성
텍스트를 readability4j가 더 높은 점수로 선택한다"**는 한 가지다.
즉 문제의 본질은 특정 키워드 카테고리가 아니라 readability4j의
본문 선택 알고리즘 자체.

**반례도 충분히 쌓임**: Google Cloud, Microsoft Learn, 씨젠,
롯데바이오로직스, 한미약품, 연합뉴스, 무신사, 롯데월드타워, K-NIBRT,
대웅제약(OG fallback으로 정직하게 처리됨) 등 - "기업 홈페이지는
다 실패한다"는 가설은 이미 기각됐고(Boundary Study와 일관), Type D는
예외적으로 발생하는 패턴이지 지배적인 패턴이 아니다.

**여기서 조사를 마무리하고 관찰 모드로 전환**: 오늘 억지로 더
같은 종류의 사이트를 찾아 사례를 채우지 않는다. 대신 앞으로는
자연스럽게 스크랩하다가 WARN 로그가 뜨면 그때만 사례를 하나씩
추가하는 방식으로 - "오늘 20개까지 채우자"가 아니라 "실사용 중
새 유형이 나오면 누적"이 운영 데이터의 신뢰도도 높고 개발 속도도
지킨다. Extraction 조사는 여기서 일단락하고, 스크랩/Topic 기능
개발로 돌아간다.

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

# V1 Design: AI Recommends, User Confirms

> Phase 1/2 연구 결과(`docs/research_phase_1_summary.md`,
> `docs/research_phase_2_summary.md`)를 제품 설계로 옮기는 문서.
> V0(Validation)의 검증이 끝난 뒤 처음 쓰는 설계 문서 - `anchor_model.md`
> 가 V0 알고리즘의 상세 설계였다면, 이 문서는 V0에서 배운 것을 바탕으로
> V1(Genesis)이 실제로 무엇을 만들지 정의한다.

## Design Principle

> AI가 사용자의 조직 방식을 혼자서 복원할 수는 없다. 하지만 사용자의
> 행동 맥락을 조금 받으면 AI 추천의 품질은 개선된다. (Finding P2-003)

V0가 처음 꿈꿨던 것은 "스크랩 → 완전 자동 분류"였다. Phase 2 전체
(Measurement Family, Objective Discovery, Information Discovery)의
결론은 이게 현재 기술로는 안 된다는 것이다 - Mechanism/Topic/Neutral/
Relation/Retrieval 어떤 objective도, 얕은 저장 이유를 더해도 완전
자동화의 벽을 못 넘었다(Finding P2-002). 진짜 behavioral context를
줘야 방향성 있는 개선이 있었지만(Finding P2-003) 그것만으로도
불충분했다.

그래서 V1은 **"스크랩(+선택적 맥락) → AI 추천 → 사용자 확인"** 구조로
간다. `ai_rules.md` Rule 1("AI는 이해하고, 알고리즘은 결정한다")을
그대로 유지하되, 최종 확정 권한을 "알고리즘의 threshold 판단"에서
"사용자의 확인"으로 한 단계 옮긴다 - 이건 원칙을 어기는 게 아니라,
V0 연구가 밝힌 "알고리즘 혼자로는 threshold를 신뢰할 만큼 정확하게
못 정한다"는 사실을 반영하는 것이다.

## Scrap Flow

1. 사용자가 URL을 스크랩한다.
2. **Content Extraction** - 본문을 최대한 확보한다(실패할 수 있음,
   아래 "Open Engineering Risk" 참고).
3. **(선택, 저마찰)** 한 줄 맥락을 물어볼 수 있다 - "왜 저장했나요?"
   같은 placeholder, 건너뛰기 가능. Round 1.5는 4개 질문(purpose/
   time_horizon/trigger/importance)을 썼지만, 실제 제품에서 스크랩할
   때마다 4개를 묻는 건 마찰이 너무 크다 - **최대 1개 자유 입력
   필드로 압축**한다(가장 정보량이 컸던 trigger 계열을 유도하는
   문구로).
4. 알고리즘이 후보 Island를 좁힌다 - Phase 1에서 확립한 Two-stage
   architecture(Experiment #48/#51) 그대로: cosine similarity로
   top-3 후보를 추리는 Recall 단계.
5. LLM pairwise judge가 그 top-3를 재정렬한다(Precision 단계) -
   objective는 **Neutral**을 기본값으로 쓴다(Phase 2에서 가상·실제
   데이터 양쪽에서 가장 일관되게 검증된 Semantic Relatedness family
   대표, Experiment #55/#56/#57). 사용자가 맥락을 입력했다면
   content_summary와 함께 넣는다(Experiment #59 방식).
6. UI는 추천 Island를 **강제가 아니라 제안**으로 보여준다 - 사용자가
   확인하거나, 다른 기존 Island를 고르거나, 새 Island를 만들 수
   있다.
7. 사용자의 정정은 기록만 해둔다(V1 스코프에서는 재학습에 안 씀 -
   "이 정정을 다음 추천에 어떻게 반영할지"는 Adaptive Resolution류의
   질문이라 의도적으로 범위 밖에 둔다).

## Open Engineering Risk: Content Extraction

V0 연구는 "분류 알고리즘"에 집중했기 때문에 content 확보가 전처리
단계처럼 취급됐지만, 실제로는 **AI 추천보다 먼저 풀어야 하는 별도의
엔지니어링 문제**다. Round 1(Experiment #56 준비 과정)에서 실제 URL
25개 중 WebFetch로 원문을 직접 가져온 건 9개뿐이었다 - naver
blog·namu.wiki 같은 흔한 플랫폼 다수가 스크래핑을 막았고, 15개는
검색 스니펫으로 대체, 1개는 완전히 실패했다. 이건 LLM의 이해력
문제가 아니라 **"어떤 URL이 들어와도 요약 가능한 텍스트를 얼마나
안정적으로 확보할 수 있는가"**라는 별개의 병목이고, AI 추천 파이프라인
전체보다 여기에 더 많은 엔지니어링 시간이 들어갈 가능성이 있다.

고려해야 할 경우들 - 각각 추출 방식이 다르다:
- 원문 직접 추출 성공 (정적 HTML)
- robots 정책으로 차단
- JS 렌더링이 필요한 페이지 (SPA)
- 로그인 필요 / Paywall
- 네이버 블로그, 브런치, 나무위키처럼 봇을 막는 국내 플랫폼
- 유튜브 (영상 - 자막/설명 활용?)
- PDF
- GitHub, Notion 공개 페이지처럼 구조화된 소스

**아직 답 없음 - V1 구현 전 결정 필요**:
- 추출 라이브러리/서비스 선택
- JS 렌더링 대응 여부(헤드리스 브라우저를 쓸지, 어디까지 포기할지)
- 추출 실패 시 fallback 전략(검색 스니펫? 사용자에게 직접 요약 요청?)
- Open Graph 같은 메타데이터 활용 여부
- 플랫폼별 개별 처리(YouTube, GitHub 등)가 필요한 범위

## Open Engineering Risk: Recommendation Pipeline Scaling

2026-08-07, 장시간 사용 시 추천 파이프라인이 느려지지 않을지 논의(사용자
질문 + GPT 검토 두 라운드). 브루트포스 cosine similarity를 쓰는 곳이
`recommend()` 안에 두 군데 있는데, 늘어나는 축이 달라서 위험도가 다르다:

- **Island 탐색**(`IslandRecallService.recall`) - `O(Island 개수)`.
  Island는 "개발"/"AI"처럼 넓은 주제 단위라 개수가 아주 느리게 늘어난다
  (지금 9개). 수백 개가 돼도 cosine 비교 자체는 가벼울 것으로 보인다
  (미측정 - LLM 호출 1회가 초 단위인 것에 비해 훨씬 작을 것이라는
  추론일 뿐, 실제 프로파일링 전까지는 가정으로만 취급).
- **섬 내부 대표 스크랩 탐색**(`RecommendationService.representativeText`)
  - `O(추천 후보로 뽑힌 각 섬의 스크랩 개수)`, 스크랩 저장할 때마다
  (`POST /scraps`) 매번 실행된다. 이쪽이 실제로 걱정할 만한 축 -
  섬 하나가 오래 쓰이며 스크랩을 아주 많이 모으면 커질 수 있다.
  계산량 자체보다 `findByIslandId`가 매번 embedding(1536차원, TEXT
  컬럼 JSON 직렬화)을 포함한 전체 행을 DB에서 읽고 역직렬화하는
  I/O 비용이 먼저 체감될 가능성이 높다고 봄(역시 미측정 추론).

**명시적으로 하지 않기로 한 것 - `representativeText`에 LIMIT/캐시로
정확성을 깎는 최적화**:
- 최근 N개로 LIMIT: `representativeText`의 목적은 "최근 글"이 아니라
  "새 스크랩과 가장 비슷한 기존 글"을 찾는 것이라, 오래전에 저장된
  진짜 비슷한 글이 후보에서 사라져 알고리즘의 의미 자체가 바뀐다.
- `Island.representativeScrapId`처럼 대표 스크랩 하나를 고정해두고
  갱신하는 캐싱: 섬 하나에 여러 소주제가 섞여 있으면(예: "여행" 섬
  안에 맛집/캠핑/해외여행이 공존) 대표가 한쪽으로 굳어버려서, 다른
  소주제의 새 스크랩이 실제로 비슷한 글이 섬 안에 있어도 그 글과
  비교를 못 받고 점수가 부당하게 낮게 나온다. 이건 PR #68에서 "가장
  최근 스크랩"을 비교 대상으로 썼다가 겪은 것과 본질적으로 같은
  drift 문제(사용자가 "마지막 스크랩만 따라가면 전체 주제와
  동떨어질 수 있다"고 반박했던 바로 그 이유) - 대표를 "최근 것"에서
  "한 번 뽑힌 것"으로 바꾼 것뿐, 같은 실패 패턴이 재발할 수 있다.

**단계별 대응 순서(확정 로드맵 아님, 실제 병목이 측정되면 그때 순서대로 검토)**:
1. **현재 유지** - 지금 규모(Island 수십 개, 섬당 스크랩 수십~수백 개)에서는
   가장 단순하고 정확하다. 미리 바꿀 근거 없음.
2. **프로파일링으로 실제 병목 확인** - CPU(cosine 계산)인지 I/O(DB
   조회+역직렬화)인지부터 실측. 이 프로젝트가 계속 지켜온 "측정 →
   병목 확인 → 필요한 만큼만 개선" 원칙 그대로 적용.
3. **후보(우선순위 아님, 병목 종류에 따라 다른 걸 고를 수 있음)**:
   - I/O가 병목이면: 섬별 스크랩 embedding을 애플리케이션 메모리에
     캐싱(비교 로직/정확성은 그대로, DB 왕복+JSON 파싱만 없앰). 이
     프로젝트 규모에서 캐시 무효화가 실제로는 단순할 가능성이 큼 -
     `Scrap`은 update/delete API가 아예 없고, 유일한 변경 경로인
     confirm()도 재확정을 막는 가드가 없어 이론상 islandId가 한 번
     더 바뀔 수 있는 정도(순수 append가 아니라 "재확정 시 섬 이동"
     정도만 처리하면 됨). 여러 인스턴스 동기화 문제도 이 프로젝트가
     단일 인스턴스 개인용 V1이라 해당 없음. 단, 이건 여전히 후보일
     뿐 - 실제로 만들 땐 이 가정(재확정 경로 실사용 여부 등)부터
     다시 확인.
   - 계산량 자체가 병목이면(가능성 낮음): pgvector/HNSW 같은 ANN
     인덱스 - 수만~수십만 개 벡터 규모에서나 근거가 생기는 선택지.

## Out of Scope (V1) - 문서 근거 있는 항목만

- **자동 완전 분류** (Finding P2-002/P2-003) - AI 추천 + 사용자 확인
  구조로 대체됨.
- **스크랩마다 3~4개 구조화된 질문 강제** - Round 1.5는 연구용으로
  4개를 썼지만, 실제 제품은 최대 1개 자유 입력으로 압축한다. 마찰이
  정보량보다 더 큰 비용이다.
- **전역 고정 threshold 튜닝** (Finding #014, Measurement Family) -
  Neutral을 기본값으로 삼되, 도메인마다 다르게 튜닝해야 할 가능성은
  열어둔다(Adaptive Resolution 방향).
- **사용자 정정을 이용한 개인화(calibration)** - 정정은 기록만 하고
  재학습에는 안 씀(Adaptive Resolution 방향, 범위 밖).
- **Adaptive Resolution 계열 전반** - RQ10-1 이후로 명시적으로
  미룬 연구 방향.
- **Island merge/split 등 고도화된 재조직화** - Roadmap상 V2
  (Evolution) 이후 문제.

## V1 구현 시 남는 질문 (아직 답 없음)

- "추천에서 고르기 vs 새로 만들기" UI/UX 구체 설계
- 추천 confidence가 낮을 때(top-3 후보 점수가 다 낮을 때) 사용자에게
  어떻게 보여줄지 - cold start 취급?
- Content Extraction 실패율이 실제로 얼마나 될지, 그게 제품 경험에
  얼마나 영향을 줄지(Open Engineering Risk 절 참고)

# V2 Design (Evolution) — Topic

> **V2는 Topic을 새로 제안하는 프로젝트가 아니다. V0에서 이미 존재했던
> Topic 개념을, V0의 연구 결과를 반영한 새로운 UX로 되살리는 프로젝트다.**

## 용어 주의

이 프로젝트에서 "Topic"은 두 군데서 쓰인다 - 서로 무관하다.

1. **이 문서의 Topic** - `prototype/world.py`의 `Topic` 클래스, Island
   내부의 하위 구조(건물). 이 문서 전체는 이 뜻으로만 쓴다.
2. **`docs/v1_design.md`의 Topic** - LLM Pairwise Judge의 objective
   이름(Mechanism/**Topic**/Neutral/Relation/Retrieval, V0 Phase 2
   연구 산물). V1의 `LlmPairwiseJudgeClient`가 그중 Neutral만 포팅했다.
   Island 배정 추천에 쓰이는 프롬프트 종류일 뿐, 아래 내용과는 무관.

## Background

### V0의 원래 모델

`prototype/world.py`가 실제로 구현했던 계층 구조:

```
Island (identity_vector - 절대 갱신 안 함)
 └── Topic (center_vector - EMA로 갱신)
      └── Scrap
```

새 스크랩은 먼저 어느 Island인지(`island_threshold`), 그다음 그 Island
**안에서** 어느 Topic인지(`topic_threshold`) 순으로 배정됐다. Island가
둘로 쪼개지는 개념은 원래 없었다 - Island는 정체성으로서 영속적이고,
Topic이 그 안에서 늘어나는 게 성장이었다(README 로드맵의 "시각적 티어
Seed→Islet→Village→City, Topic 분화"도 이 그림과 일치).

`prototype/label_generator.py`/`generate_topic_labels.py`를 보면 Topic도
Island처럼 AI가 사람이 읽을 한국어 라벨을 붙이도록 설계돼 있었고, 실제
생성된 라벨을 사람이 붙인 정답 라벨(Spring/JPA, Kafka, Redis, LLM, RAG,
Baseball, Football 등)과 나란히 비교하는 검증 스텝까지 있었다 - **Topic은
처음부터 내부 자료구조가 아니라 사용자에게 보여줄 제품 개념**이었다.

### 왜 실패했는가

`docs/algorithm_limitations.md` Finding #005/#006: Night Batch가 Topic
단위로 자동 재구성(Merge/Split/Union-Find Graph/HDBSCAN)을 시도했지만,
표본이 너무 적은 단위(Topic당 평균 3개 미만)에서 embedding noise가
그대로 드러나 전부 실패했다. purity 기반으로 "의심스러운 Island만
선택적으로 재평가"하는 정교한 버전(`selective_night_batch`)까지 만들어
검증했지만, 파라미터를 아무리 바꿔도 "전부 1개로 뭉침"과 "9개인데 8/9
중복"을 오갈 뿐이었다.

**실패한 건 Topic이라는 개념이 아니라 "Topic 생성/배정을 알고리즘이
자동으로 결정하게 만드는 것"이었다.** Finding #012는 오히려 잘 설계된
신호(Pairwise LLM Judgment)가 실제로 뚜렷한 판별력을 보인다는 걸
확인했다 - 문제는 신호의 유무가 아니라 그 신호에 임계값을 매겨 **AI가
스스로** 나누게 둔 것.

### V1은 왜 다시 안 다뤘는가

V1은 Topic을 의도적으로 배제하기로 결정한 적이 없다 - `docs/v1_design.md`에
"Topic"이 언급되는 유일한 곳은 위 용어 주의에 적은 대로 Pairwise Judge
objective 이름뿐이다. V1은 Genesis(Scrap→Island 추천+확인 루프)를
최소로 증명하는 데 집중했고, 그 범위 안에 Island 내부 구조는 그냥
없었다 - 명시적 배제라기보다 다뤄지지 않은 것.

### 왜 지금 다시 Topic인가

V1을 실사용하면서 하나의 Island 안에서도 추천 관련 점수 편차가 크게
나타나는 사례를 관찰했다(Finding V1-003, "여행" Island 0.25~0.75).
이건 Island 배정 자체가 잘못됐다는 신호가 아니라, **하나의 정체성
안에서 서로 다른 관심사가 공존하기 시작했다는 신호**였다. 따라서
V2의 질문은 "Island를 나눌 것인가?"가 아니라 **"Island 내부의 다양성을
어떻게 표현할 것인가?"** - 그리고 그 답은 이미 V0에 있었던 Topic
구조였다.

## Problem Statement

V2는 Topic을 다시 도입한다. 단, V0가 실패한 "자동 생성/자동 배정"은
다시 시도하지 않는다.

## Design Principle

- **AI는 Topic의 가능성을 보여주고, 사용자가 Topic을 만든다.** V1의
  "AI는 추천하고 사용자가 확정한다"(Island 배정)를 한 단계 더 사용자
  쪽으로 옮긴 것 - Topic 생성 여부, 이름, 구성 전부 사용자 결정.
- **Island는 정체성으로 유지된다.** Topic 형성은 Island 내부에서만
  일어난다 - 스크랩이 Island를 벗어나 다른 Island로 옮겨가는 일은 없다
  (이미 V1에서 지켜온 "기존 Island는 절대 안 움직임" 원칙의 연장).
- AI가 Topic 이름을 제안할 수는 있다(V0 `label_generator.py`의
  presentation 계층 역할과 동일) - 채택 여부는 사용자 몫.
- **Topic은 사용자의 이해를 돕기 위한 표현 계층이지, 알고리즘이
  확정하는 정답이 아니다.** 발견되는 것이지 계산되는 것이 아니다.

## Candidate Signals

아래 지표들은 Topic 생성을 결정하기 위한 기준이 아니라, **사용자가
Island를 이해하도록 돕는 관찰 정보**다 - "이 값을 넘으면 자동으로
Topic을 만든다"는 threshold 사고방식은 V0에서 이미 실패한 접근이라
(Finding #005/#006) 여기서 반복하지 않는다.

새 인프라 없이 기존 데이터로 계산 가능한 것부터.

- **Intra-Island cosine variance** - 같은 Island 안 스크랩들의 embedding이
  서로 얼마나 흩어져 있는가. **PR #78로 실제 노출해서 검증한 결과,
  이 신호는 "혼재도(noisiness)" 정도만 반영하고 Topic 존재 여부와는
  약하게만 상관됨이 드러났다** - 제주/부산으로 뚜렷하게 갈린 "여행"
  Island(0.0156)보다 특별한 하위 그룹이 알려지지 않은 "야구" Island
  (0.0236)의 variance가 오히려 더 높았다(콘텐츠 장르 혼입이 더 크게
  기여하는 것으로 추정). Island 건강도 참고 지표로는 유지하되, Topic
  후보를 찾는 신호로는 쓰지 않는다.
- **Override rate** - 이 Island로 추천됐다가 다른 Island로 확정되거나,
  반대로 이 Island로 확정됐지만 추천 1순위가 아니었던 비율
  (`Scrap.recommendedIslandId`/`islandId`/`wasCorrected()`로 이미 계산
  가능, PR #71 `/scraps/stats`와 같은 재사용 패턴).
- **Mechanism Pairwise Judge** - V0의 pairwise judge objective 중
  "Mechanism"(같은 구체적 하위 주제/대상을 다루는지 명시적으로 묻는
  프롬프트, Finding #012의 AUC 0.82~0.94 신호 그대로)을 재사용해 Island
  내부 스크랩 쌍을 비교한다. 실제 "여행" Island(24개, 제주/부산/기타)로
  검증: 다른 지역 쌍(50개) 평균 0.000, 같은 지역 쌍(50개) 평균 0.248 -
  콘텐츠 장르(블로그/나무위키/공식 사이트)가 같아도 지역이 다르면
  전부 0.000으로, 장르 혼입에 흔들리지 않았다(raw embedding cosine
  variance와 정반대). **Topic 후보 생성의 근거 신호로 채택** - 아래
  "다음 단계" 참고.

스크랩 개수(Island 크기) 자체는 신호에서 제외한다 - "세계는 완성되지
않는다"/"성장은 체감 가능해야 한다"는 Product Principle과 충돌 위험이
있다(크다 = 나쁘다로 읽힐 수 있음).

## Out of Scope

- 자동 Topic 생성
- 자동 Island 분열(애초에 이 프로젝트의 모델에 없는 개념)
- threshold 기반 자동 분화
- Night Batch류 자동 재구성

## 다음 단계

**PR #78(신호 노출)과 Mechanism Pairwise Judge 실험(2026-07-28,
`experiments/v0_validation.md` 참고)을 거치며 순서가 바뀌었다.** 원래는
"신호 → 수동 Topic 생성 → AI 그룹 제안"이었지만, 수동 Topic 생성을
독립 기능으로 만들 이유가 약하다는 게 드러났다 - 스크랩을 사용자가
전부 직접 골라 묶는 수준이면 애초에 AI 추천이 필요한 이유가 없다.
대신 이미 검증된 Mechanism Pairwise Judge를 바로 "후보 제안" 재료로
쓴다.

1. **Mechanism Pairwise Judge로 Island 내부 Topic 후보를 생성한다.**
   AI가 하는 일은 여기까지 - 후보를 "찾아서 보여주는" 것.
2. **사용자는 후보를 승인/이름 변경/병합/삭제할 수 있다.** AI는 이
   결정에 관여하지 않는다.
3. **승인된 후보만 Topic이 된다.** 승인 전까지는 어떤 것도 확정되지
   않는다 - Scrap이 Island를 벗어나는 일도 없다(Design Principle
   "Island는 정체성으로 유지된다" 그대로).
4. Topic 이름은 AI가 초안을 제안할 수 있지만(V0 `label_generator.py`의
   presentation 계층 역할), 최종 이름은 항상 사용자가 정한다.

이 구조가 Finding #005(자동 재구성 실패)와 Finding #012(Mechanism
신호 자체는 강함)를 동시에 만족시킨다 - 신호가 약해서가 아니라 "AI
혼자 최종 결정"이라는 구조가 실패했었기 때문에, 신호는 그대로 쓰되
결정권만 사용자에게 둔다.

구현은 여전히 가장 작은 단위부터 - 다음 PR 범위는 별도로 논의한다.

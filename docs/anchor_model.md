# Anchor Model

Finding #006(Greedy + EMA + Threshold는 계층과 무관하게 같은 방식으로
실패한다) 이후 Night Batch v0~v3(Merge/Split/Topic Graph/HDBSCAN/
Selective, `hybrid_architecture.md`)를 대체하는 통합 설계다. v0~v3는
전부 "Greedy가 만든 구조는 대체로 맞고, 그걸 고친다"는 전제를 갖고
있었다 — 이 전제 자체가 틀렸다는 게 오늘 확인됐다(AI Researcher의 Topic
하나가 30개 스크랩, 8개 실제 주제를 이미 섞은 채로 만들어져 있었다).

## 핵심 원칙

> **Greedy Online은 UX(Preview)만 담당한다. 확정(Truth)은 오직 Night
> Batch에서만 일어난다.**

Online 단계에서 만들어지는 Topic/Island는 **Provisional**이다 — 사용자에게
즉시 보여주기 위한 임시 상태일 뿐, 다음 Night Batch가 그대로 승인한다는
보장이 없다. Night Batch는 Greedy의 결과를 "고치는" 게 아니라, 그 주기
동안 쌓인 새 스크랩을 **Greedy가 어디 배치했는지는 무시하고** 원점에서
다시 클러스터링(scrap-level HDBSCAN, Experiment #12/#22에서 검증된
방법)한다.

## Confirmed = Anchor

Night Batch가 한 번이라도 승인한 Topic/Island를 **Anchor**라고 부른다.
Anchor는 이후의 routine Night Batch에서:

- **움직이지 않는다** — identity_vector, id, 좌표가 전부 불변.
- **쪼개지지 않는다** — Split 대상이 아니다.
- **하지만 Context로는 계속 쓰인다** — 새 스크랩을 어디에 붙일지 판단할
  때 Anchor의 identity_vector/center_vector/Label을 참고 기준으로
  사용한다.

새로 들어온(아직 Confirmed 안 된) 데이터만 매 Night Batch마다 새로
클러스터링되고, 그 결과가 기존 Anchor와 충분히 가까우면 그 Anchor에
편입되며, 아니면 새로운 Anchor가 된다.

## Lifecycle (Topic과 Island가 동일한 구조를 공유한다)

```
Scrap 저장
  ↓
Provisional Topic (Online, 현재 Greedy+EMA+threshold 그대로) — 즉시 체감
  ↓  (Night Batch)
Confirmed Topic = Anchor (identity_vector 고정, Label 생성)
  ↓
Provisional Island (Online, 같은 방식)
  ↓  (Night Batch)
Confirmed Island = Anchor
```

Topic과 Island는 같은 Lifecycle(Online=Provisional, Offline=Confirmed)을
공유한다 — Finding #001(Island)과 Finding #006(Topic)이 사실 같은
계층적 문제였다는 것과 대칭을 이룬다.

## Night Batch 알고리즘 (Anchor 기준)

**입력**: `confirmed_topics`(Anchor 목록) + `new_scraps`(마지막 Night
Batch 이후 쌓인, 아직 Confirmed 안 된 스크랩)

```
candidate_clusters = HDBSCAN(new_scraps)   # Greedy 배치는 참고하지 않는다

for cluster in candidate_clusters:
    nearest_anchor = 가장 가까운 confirmed anchor 찾기
    if similarity(cluster, nearest_anchor) >= threshold:
        attach(cluster, nearest_anchor)     # Anchor 자체는 안 바뀜, 소속만 늘어남
    else:
        create_new_anchor(cluster)          # 새 Confirmed Topic/Island
```

**출력**: 기존 Anchor(변경 없음) + 새로 생긴 Anchor. Island 레벨에서는
이 과정이 Topic Anchor들을 입력으로 반복된다(Topic이 먼저 Confirmed된
뒤에야 Island Night Batch가 그 위에서 실행된다 — Step 5.25 → Step 5.5
순서와 일치).

## Immutability의 예외 — Migration Event

Anchor는 **routine Night Batch에서는** immutable이다. 하지만 이걸
절대화하면 장기적으로 개념 드리프트(concept drift)에 대응할 수 없다 —
예를 들어 2026년의 "LLM" Topic이 2년 뒤에는 Reasoning/Agents/MCP/World
Models까지 포괄하는 훨씬 큰 영역으로 자연스럽게 성장했어야 할 수도
있다.

그래서 두 계층으로 나눈다:

- **일상적인 Night Batch**: Anchor는 절대 불변. 새 데이터만 원점에서
  재계산해서 기존 Anchor에 붙이거나 새로 만든다.
- **Migration Event(신설, 예외적)**: 알고리즘 버전 업그레이드, 대규모
  재색인, 사용자의 명시적 재구성 요청 같은 경우에만 전체 재구성을
  허용한다. Migration Event는 routine Night Batch와 명확히 구분되는
  별도 트리거를 가져야 한다(자동으로 조용히 발동되면 안 됨 — "세계는
  안정적이어야 한다" 원칙을 해치지 않으려면 사용자가 인지할 수 있는
  이벤트여야 한다).

## Product Principle과의 대응

| Principle | Anchor Model에서의 구현 |
|---|---|
| 세계는 안정적이어야 한다 | Anchor는 routine Night Batch에서 절대 안 움직인다 |
| 성장은 즉시 체감 가능해야 한다 | Provisional 단계가 즉시 반영되고, 새 Anchor 생성도 눈에 보이는 성장이다 |
| Minimum Change Principle | candidate cluster는 항상 기존 Anchor 편입을 우선 시도한다 |
| 좌표는 영속 상태 (`map_layout.md`) | Anchor의 identity_vector(=좌표 대용)는 불변 |

## Research Question #0 — 최종 답 (Finding #006 이후)

> Online에서 확정되는 계층이 존재해야 하는가?

**없다.** Greedy Online(Topic이든 Island든)은 전부 Provisional(Preview
UX)이고, 확정은 오직 Night Batch(Anchor 형성)에서만 일어난다.

## Research Question #1 (신설)

> Offline 단계에서 Greedy 결과를 얼마나 재사용해야 하는가?

**새로 들어온(미확정) 데이터에 대해서는 재사용하지 않는다** — Greedy가
어디 배치했었는지 무시하고 scrap 레벨에서 원점 재계산한다. **이미
Confirmed된 Anchor는 Context로만 참고하고 routine 상황에서는 절대
수정하지 않는다.** 오늘 시도했던 Night Batch v0~v3(Merge/Split/Topic
Graph/HDBSCAN/Selective)가 전부 실패했던 공통 원인이 "Greedy 결과를
입력으로 재사용하려 했다"는 것이었다는 게 이 질문에 대한 실험적 근거다.

## Open Questions (아직 미해결)

0. **제품 목표(Purity + Duplication)를 가장 잘 근사하는 목적함수는
   무엇인가?** (Research Question #3, 확장판, 최우선) — 처음엔 "Anchor는
   무엇으로 표현되어야 하는가"(representation,
   Research Question #2)로 좁게 물었으나, Experiment #31에서 top-k 멤버
   평균을 실제 attach 판단 기준으로 써봤더니 Duplication Rate는 낮아졌지만
   Purity도 함께 낮아지는 식으로 같은 Precision-Fragmentation Trade-off
   곡선 위의 다른 지점으로 이동했을 뿐 해결되지 않았다(Research Insight
   #002). **Experiment #32(Assignment Matrix Analysis)에서 그 이유에 대한
   구조적 단서가 나왔다**: 같은 배치 안에서 서로 다른 candidate가 1등으로
   같은 Anchor를 두고 경쟁하는 경우가 Backend 94%(17/18), AI Researcher
   96%(25/26)에 달했다 - 경쟁이 예외가 아니라 기본 상태다(Research
   Insight #003). attach를 candidate마다 독립적인 binary 판단으로
   모델링하는 지금 구조(Experiment #28~31이 전부 이 구조 위에서 점수
   함수만 바꿔온 것) 자체가 문제를 온전히 표현 못 할 수 있다 - attach는
   본질적으로 assignment problem일 가능성이 있다.
   - **증명된 것 (Experiment #32)**: 경쟁(같은 배치의 여러 candidate가 같은
     1등 Anchor를 두고 겹치는 것)은 예외가 아니라 기본 상태다.
   - **증명된 것 (Experiment #33, Objective v0)**: "같은 Anchor에 서로 다른
     candidate를 몰아넣는 것"에 비용을 매기는 목적함수(pairwise
     dissimilarity penalty, λ>0)를 하나 넣으면, Greedy 배정에서 지역
     탐색만으로도 candidate의 35~40%가 재배정되고 목적함수 값이 꾸준히
     개선됐다 - **Greedy는 적어도 하나의 합리적인 목적함수에 대해 전역
     최적이 아니다**(존재증명). 단, 이건 "Global Search가 필요하다"가
     아니라 "Global Search를 고려할 이유가 있다"까지만 증명한 것이다.
   - **아직 증명 안 된 것**: Objective v0(pairwise dissimilarity penalty)가
     좋은 목적함수인지 자체가 미검증 - J가 커졌다고 실제 Purity가
     좋아졌는지/Duplication이 줄었는지/사용자 경험이 나아지는지는 한
     번도 측정 안 됐다. λ 값도 최적값을 찾은 게 아니라 탐색용 실험
     파라미터일 뿐이다. 아직 시도 안 한 목적함수 항: entropy penalty,
     purity estimate, anchor confidence, new-anchor cost 등.
   - **표현(representation) 후보** (Research Question #2, 전부 미검증):
     identity_vector(현재), nearest member, top-k averaging(Experiment
     #30/#31에서 시도, Trade-off만 이동시킴), distribution representation,
     prototype set.
   - **증명된 것 (Experiment #34)**: Objective v0를 실제로 적용해서 Day1→7→30
     전체를 돌려보니, Backend User는 Purity·Duplication 둘 다 개선됐지만
     (0.437→0.634, 66.7%→55.6%) AI Researcher는 Purity만 개선되고
     Duplication은 오히려 악화됐다(88.9%→100.0%, Island 수도 13→22로
     급증) - **"J가 커지는 것"과 "제품이 원하는 방향으로 좋아지는 것"은
     동일하지 않다**(Research Insight #005). 이 차이를 "Backend는 되고 AI
     Researcher는 안 된다"는 페르소나 차이로 단정하지 않는다 - Virtual
     User가 페르소나당 1개뿐이라 일반화 근거가 부족하고, 더 안전한
     해석은 "지배적 메가토픽이 있고 Topic 간 중첩이 적은 구조"와 "여러
     주제가 조밀하게 얽힌 구조"라는 **데이터의 구조적 차이**다. 지금
     목적함수(pairwise dissimilarity penalty 하나뿐)는 사실상 Purity
     쪽으로 편향된 근사치이고 Duplication을 전혀 반영하지 못한다는 것도
     함께 드러났다.
   - **연구 계층이 두 번 분리됨**: Experiment #28~32(Research Insight
     #004)에서 Similarity Function → Objective Design으로 한 번 이동했고,
     Experiment #34(Research Insight #005)에서 **Product Metric →
     Objective → Optimization**으로 한 겹 더 늘어났다 - Optimizer의
     성능보다 "그 Objective가 Product Metric을 얼마나 잘 근사하는가"가
     더 근본적인 연구 대상이 됐다.
   - **시도했지만 근거가 무너짐 (Experiment #35)**: Duplication을 직접
     반영하는 Fragmentation Penalty(서로 비슷한 candidate가 다른
     Anchor/신규로 갈라지면 벌점)를 설계하려 했으나, 그 근거가 될
     pairwise similarity 자체가 "같은 실제 주제 쌍"과 "다른 실제 주제
     쌍"을 거의 구분하지 못한다는 게 확인됐다(Backend는 같은 주제 쌍의
     최댓값이 다른 주제 쌍 상위 10% 지점보다 낮음) - Research Insight
     #006("Pairwise Similarity Is Not a Reliable Proxy for Topic
     Identity"). Margin(Experiment #29)이 attach 정확도의 신호가
     아니었던 것과 같은 계열의 결론이다. λ2(Fragmentation Penalty
     세기) 스윕은 입력 신호 자체가 약해서 지금 하지 않는다 - 신호를
     세게/약하게 쓰는 것만으로는 Experiment #28의 threshold sweep처럼
     또 다른 Trade-off 지점만 찾을 가능성이 높다.
   - **Research Question #4: "Duplication은 어떤 신호로 근사할 수 있는가?"
     — Closed (Experiment #36)**. 구조적 신호(top-k Anchor Overlap, Score
     Vector Correlation)를 시도했지만 Direct Similarity(Experiment #35)
     보다도 판별력이 없었다(분리도가 거의 0이거나 음수) - Score Vector
     Correlation은 절댓값이 0.96~0.98에 달해, 소수의 "허브" Anchor가
     모든 candidate의 선호 순위를 지배하고 있음을 보여줬다. Margin(#29)
     /Representation(#30-31)/Direct Similarity(#35)/구조적 신호(#36) 네
     가지 독립적 접근이 전부 실패 → **`docs/algorithm_limitations.md`
     Finding #008(Embedding Similarity Encodes Semantic Relatedness, Not
     Topic Identity)로 승격, 이 연구 축(similarity-derived signal로
     Duplication 근사)은 여기서 종료한다.**
   - **Research Question #5: "Similarity만으로 Topic Identity를 만들 수
     있는가?" — Answered(Experiment #37~39): 증거는 강하게 "아니오"를
     가리킨다.** 태그 추출(freeform, Experiment #37/38)은 Precision은
     좋았지만 Recall이 낮았고 - Error Analysis 결과 원인은 추상화 수준
     불일치였다. 이를 고치려 한 Hierarchical Tag Extraction(LEVEL1/LEVEL2,
     Experiment #39)조차 실패했다 - "가장 넓은 상위 폴더 이름"을 명시적
     으로 요청해도, 같은 실제 Topic인 문서 8개의 LEVEL1이 8개 중 6개가
     서로 달랐다. **원인은 프롬프트 설계가 아니라 구조적이다**: 문서를
     독립적으로(서로를 못 보는 채) 처리하는 한, "이 문서들이 같은 폴더에
     들어가야 한다"는 정보 자체가 판단 과정에 존재하지 않는다 -
     Document Understanding(문서 하나의 핵심)과 Corpus Taxonomy(여러
     문서를 어떻게 묶을까)는 다른 문제다. `docs/algorithm_limitations.md`
     **Finding #009**(Independent Document Understanding Cannot Produce
     a Shared Topic Identity)로 승격, Experiment #29~#39를 하나의 연구
     축("문서별 독립 신호로 Topic Identity를 근사할 수 있는가")으로
     마무리한다.
   - **Research Question #6: "Topic Identity는 개별 문서의 속성인가,
     여러 문서에 걸친 관계적 속성인가?" — 잠정 종료(Experiment #40)**.
     Batch LLM 같은 직접 구현으로 가기 전에, "관계 정보가 실제로 존재
     하는가"부터 순수 그래프 관찰(임베딩/LLM 판단 추가 없이, Experiment
     #37 태그의 co-occurrence만)로 확인했다 - 태그 co-occurrence 그래프의
     작은 Connected Component(크기 3~8)는 대체로 단일 실제 Topic으로
     순수했다(**관계 정보 자체는 의미가 있다는 긍정적 신호**). 하지만
     소수의 "허브" 태그가 서로 무관한 지역들을 전부 하나의 거대
     Component로 묶어버렸다(Backend User 태그 209개 중 88개, 42%가 7개
     서로 다른 실제 Topic을 뒤섞음) - Finding #004(Pairwise Threshold
     Graph Chaining)와 정확히 같은 패턴이 태그 그래프에서 재현됐다.
     `docs/algorithm_limitations.md` **Finding #010**(Local Connectivity
     Is Not Topic Identity)로 승격 - Finding #004와 Experiment #40을
     하나로 묶어 일반화("연결 기준이 무엇이든, naive connectivity 규칙
     자체가 체이닝에 취약하다"). Community Detection(Louvain/Leiden) 같은
     더 정교한 그래프 알고리즘으로 바로 넘어가지 않는다 - edge weight를
     cosine 기반으로 정의하면 Finding #008을 다시 만날 위험이 있어서다.
   - **Research Question #7(신설, 최우선): "Topic Identity는 애초에
     복원(recover)해야 하는 대상인가, 아니면 시스템이 시간이 지나며
     형성(emerge)하는 대상인가?"** Document Similarity(#008) → Tag
     String(#009) → Tag Graph Connectivity(#010)까지, "Scrap 하나 또는
     Scrap들 사이의 지역적 관계"에서 Topic Identity를 즉시 복원하려는
     시도가 전부 구조적 한계에 부딪혔다 - 관점을 "정적으로 이미 존재하는
     정체성을 찾는 문제"에서 "누적/안정화 과정을 거쳐 형성되는 개체"로
     바꿔야 하는지가 다음 질문이다. 아직 가설도 설계도 없음.
   - Hungarian algorithm/ILP 같은 실제 Optimizer 구현은 Research Question
     #7에 대한 답이 나온 뒤로 미룬다.
1. **Attach 판단 기준(threshold)** — candidate cluster와 Anchor 사이의
   유사도를 어떻게 계산할지는 Question #0에 종속된 질문이 됨. Experiment
   #28에서 attach_threshold 단독 조정만으로는 Precision-Fragmentation
   Trade-off를 못 깬다는 게 확인됨(Research Insight #001), Experiment
   #31에서 표현 방식을 바꿔도 마찬가지라는 게 추가로 확인됨(Research
   Insight #002).
2. **여러 candidate가 같은 Anchor를 두고 경쟁**할 때 처리 방법.
3. **Migration Event의 정확한 트리거 조건** — 완전히 수동(사용자 요청)인지,
   일정 기준(예: Provisional 데이터가 너무 오래 Anchor에 안 붙는 경우)이
   되면 자동으로 제안하는지.
4. **Provisional 상태를 사용자에게 보여줄지** — "이 건물은 아직 형성
   중입니다"를 노출하는 게 "세계가 살아있다"는 느낌을 주는 좋은 UX일지,
   아니면 불안정해 보일지. 아직 결정 안 됨.
5. **Migration Event 동안 Growth Point/역사를 어떻게 이관할지** — Growth
   Point 자체가 아직 미구현(Step 7 보류)이라 이 질문은 Step 7 이후로
   미룬다.

## 기존 코드와의 관계

`world.py`의 Night Batch v0~v3(`night_batch`, `find_split_candidates`/
`apply_split`, `run_night_batch`, `topic_graph_reconstruct*`,
`selective_night_batch`)는 삭제하지 않는다 — Finding #003~#005의 근거로
남긴다. Anchor Model을 실제로 구현할 때는 이 함수들의 부품(특히
scrap-level HDBSCAN 호출, Invariant 유지 로직)을 재사용하되, "Greedy
결과를 입력으로 반복 수정"하는 구조는 버리고 "새 데이터만 원점 재계산 +
기존 Anchor는 Context"라는 새 구조로 다시 짠다 — 아직 구현 전이다.

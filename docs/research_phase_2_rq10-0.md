# Research Question 10-0: Ontology of Semantic Resolution

> Does semantic resolution exist independently of the measurement method?
> Semantic Resolution은 데이터에 내재한 속성인가, 아니면 측정 방법이
> 만들어내는 산물인가?

이 문서는 연구 결과 문서가 아니라 **연구 프로토콜(Research Protocol)**이다.
아직 결론이 없는 상태에서 "무엇을 어떻게 검증할 것인가"만 정의한다.
`anchor_model.md`(설계 문서, "지금 시스템이 어떻게 동작하는가")나
`research_phase_1_summary.md`(연구 결과 문서, "무엇을 검증했고 무엇을
알게 됐는가")와는 역할이 다르다.

## Phase 1 → Phase 2: Resolution의 재정의

Phase 1에서는 Resolution을 **Mechanism / Topic / Domain이라는 판단
레벨의 차이**로 이해했다 — LLM 프롬프트가 "구체적 기법까지 같아야
하는가" 아니면 "넓은 주제만 같으면 되는가"를 지정하는 하나의 선택지
문제였다(Finding #012~#014).

Phase 2에서는 Resolution을 **텍스트 사이의 의미 관계를 생성하는
잠재 구조(latent semantic structure) 자체의 성질**로 재정의한다.
즉 "Mechanism이냐 Topic이냐"라는 레이블 선택이 아니라, 애초에 그
의미 관계가 트리(Tree)인지, 연속 거리공간(Metric space)인지, 아니면
다중 조상을 허용하는 그래프(Graph/DAG)인지를 묻는, 세계관(world model)
자체의 선택이 됐다.

또한 Phase 1의 평가 틀(`MECHANISM_LABELS`, Case A/B/C 분류)은 이미
암묵적으로 H1(계층)을 전제하고 만들어졌다는 점도 짚어둔다 — RQ10-0은
그 전제 자체를 검증 대상으로 되돌리는 질문이다.

## Candidate Latent Models

| 가설 | 잠재 모델 | Resolution의 의미 | Resolution을 고른다는 것 |
|---|---|---|---|
| H1 (Hierarchy) | Tree | LCA(최소공통조상)까지의 깊이 | 트리를 어느 깊이에서 수평으로 자를지 고른다 (cut depth) |
| H2 (Metric) | 연속 거리공간 | 거리 | 반지름/컷오프를 고른다 (radius) |
| H3 (Graph) | 다중 조상을 허용하는 DAG | 조상 집합의 중첩 정도 | 어느 조상 집합까지 포함할지 고른다 (ancestor set) — 스칼라 하나로 안 줄어들 수 있음 |

## Observable Predictions

잠재 구조는 직접 관측할 수 없다. 우리가 관측할 수 있는 것은 LLM
judgment score, embedding similarity 같은 대리 신호뿐이다. 각 가설이
그 대리 신호에 대해 서로 다른, 구분 가능한 예측을 내야 실험 가능한
이론이 된다.

| | H1 (Tree) | H2 (Metric) | H3 (Graph) |
|---|---|---|---|
| Ultrametric violation rate | 낮음 | 높음(자연스럽게 발생) | H1보다 높지만 무작위는 아님 |
| Cophenetic correlation (덴드로그램 적합도) | 높음 | 낮음 | 중간, 그러나 체계적 잔차가 남음 |
| MDS/metric embedding stress | 상대적으로 높음(트리를 저차원 거리공간으로 억지로 펴면 왜곡됨) | 낮음 | 트리로도 거리공간으로도 설명 안 되는 잔차가 체계적으로 남음 |
| 비교 기준점(anchor)을 바꿔도 순서가 유지되는가 | 유지됨 | 유지됨(거리 공리상 당연) | **유지 안 됨** — H3의 결정적 signature |

## Evaluation Strategy

- **점수 분포 대신 triplet consistency를 본다.** 분포 모양(연속/이산)은
  프롬프트의 출력 습관(calibration)에 크게 오염된다 — H1이 맞아도
  확률적 판단이면 연속 분포가 나올 수 있고, H2가 맞아도 프롬프트가
  이산적 판단을 유도하면 몰린 분포가 나올 수 있다. 반면 세 점 사이의
  상대적 순서(triplet)는 이 오염에 상대적으로 강건하다.
- **측정 방법 간 교차검증으로 "측정 독립성"을 직접 검사한다.** 같은
  삼각관계를 embedding cosine / LLM Mechanism 프롬프트 / LLM Topic
  프롬프트, 세 가지 서로 다른 도구로 쟀을 때 순서 관계가 유지되는지
  본다. 유지되면 Resolution은 데이터에 내재한 것이고, 도구마다
  뒤집히면 우리가 측정 방식으로 만들어낸 좌표계에 가깝다는 뜻이다.

## Expected Outcome

RQ10-0 does not attempt to solve Adaptive Resolution. Instead, it
determines whether Adaptive Resolution is fundamentally

- hierarchical,
- metric, or
- graph-structured.

RQ10-1 will only be formulated after RQ10-0 identifies the correct
latent model — 트리 cut / 거리 threshold / 그래프 traversal은 완전히
다른 실험 설계로 이어지기 때문에, 그 갈림길 이전에 구현으로 먼저
들어가지 않는다.

아직 실험은 설계되지 않았다. 이 문서는 이론 정의 단계의 기록이다.

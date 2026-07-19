# Research Question 10-0: Ontology of Semantic Resolution

> Does semantic resolution exist independently of the measurement method?
> Semantic Resolution은 데이터에 내재한 속성인가, 아니면 측정 방법이
> 만들어내는 산물인가?

**Status: 🟡 Provisionally Answered** (단일 데이터셋 AI Researcher,
단일 모델 기준 — 상태 표기는 ✅ Answered / 🟡 Provisionally Answered /
🔄 Re-opened 세 단계를 쓴다. Backend User 등 다른 도메인에서 반증되면
🔄 Re-opened로 되돌린다.)

이 문서는 연구 결과 문서가 아니라 **연구 프로토콜(Research Protocol)**이다.
아직 결론이 없는 상태에서 "무엇을 어떻게 검증할 것인가"만 정의한다.
`anchor_model.md`(설계 문서, "지금 시스템이 어떻게 동작하는가")나
`research_phase_1_summary.md`(연구 결과 문서, "무엇을 검증했고 무엇을
알게 됐는가")와는 역할이 다르다.

## Why was Phase 2 reframed?

> Originally, Phase 2 aimed to discover an adaptive semantic resolution.
> Experiments #52-53 demonstrated that resolution is not an independent
> quantity. It emerges from the semantic objective used to compare
> documents. Therefore the primary research question shifted from "How
> do we adapt resolution?" to "What semantic objective should define
> identity?"

원래 Phase 2는 "해상도를 도메인마다 어떻게 자동으로 맞출 것인가"를
풀려고 시작했다. 그런데 Experiment #52~53은 해상도가 독립적인 값이
아니라, 문서를 비교할 때 쓰는 semantic objective(질문 자체)의 결과로
나온다는 걸 보여줬다. 그래서 핵심 질문이 "해상도를 어떻게 적응시킬
것인가"에서 **"Identity를 정의해야 할 semantic objective는 무엇인가"**
로 옮겨갔다. 이 전환의 근거는 아래 "Experiment #53 Results"에 있다.

### Revision History

| | Framing |
|---|---|
| Previous (RQ10 kickoff, PR #39) | Phase 2: Adaptive Resolution |
| Current (Experiment #52-53 이후) | Phase 2: Semantic Objective Discovery |

**Reason**: Phase 2 experiments showed that semantic resolution is
largely a consequence of the semantic objective chosen. Adaptive
resolution therefore becomes an implementation problem that follows,
rather than precedes, objective discovery.

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

## Stage A/B Results (Experiment #52)

> Semantic resolution exhibits partial measurement invariance.

**Stage A — Measurement Invariance**

| 비교 | Odd-one-out agreement | Kendall's τ |
|---|---|---|
| Embedding vs Mechanism | 39.9% | 0.202 |
| Embedding vs Topic | 51.0% | 0.274 |
| Mechanism vs Topic | 65.4% | 0.457 |

(우연 수준 33.3%) 세 modality 모두 우연보다 agreement가 높다 — Resolution은
completely measurement artifact는 아니다. 그러나 agreement가 높지 않다 —
completely objective도 아니다. Embedding은 두 LLM 프롬프트보다 확실히
다른 종류의 신호로 분리된다.

**Stage B — Latent Geometry**

| Modality | Ultrametric violation | Cophenetic(avg/ward) | MDS stress |
|---|---|---|---|
| Embedding | 53.0% | 0.708 / 0.585 | 40.17 |
| Mechanism | 0.8% | 0.921 / 0.595 | 86.86 |
| Topic | 21.5% | 0.769 / 0.727 | 32.99 |

Mechanism 프롬프트는 극단적으로 Tree에 가깝게 행동한다(거의 완벽한
ultrametric, 저차원 거리공간으로는 안 펴짐). Embedding does not exhibit
strong tree structure, and is not well explained by a low-dimensional
metric representation — Finding #008("Similarity는 Relatedness를
포착하지, Identity는 아니다")을 기하학적으로 재확인한 것에 가깝다.

**Interim Conclusion**

> Different measurement methods do not observe the same latent geometry.
> They partially agree on local semantic relationships, but induce
> different global geometries.

세 measurement family가 드러났다:

- Embedding → semantic proximity (관계적 유사도)
- Mechanism prompt → hierarchical decomposition (Tree에 가까움)
- Topic prompt → semantic abstraction (그 사이)

These are observations about the behavior of the measurement methods,
not yet claims about the underlying latent structure.

즉 지금 관측된 차이는 Tree/Metric/Graph라는 세계관의 경쟁이 아니라,
**측정 방법이 서로 다른 기하학을 유도한다**는 더 근본적인 사실로 대부분
설명된다. H3(Graph)는 아직 기각되지 않았지만, 현재 데이터를 설명하는 데
필수적이지도 않다.

**H3 status**: H3 remains a viable hypothesis, but current evidence does
not require it.

**Open sub-question — Mechanism Tree Effect: Prompt Artifact or Model
Prior?** Mechanism 프롬프트가 왜 이렇게 Tree처럼 행동하는가 — LLM이
원래 갖고 있는 semantic hierarchy 때문인가(M2), 아니면 prompt wording이
hierarchy를 강제로 유도한 것인가(M1)? 후자라면 우리는 잠재 구조를
관측한 게 아니라 측정기를 설계한 것이다. 이 둘을 분리하는 것이 다음
실험이다.

## Experiment #53 Results — Mechanism Tree Effect: Prompt Artifact or Model Prior?

같은 36개 표본, 같은 630개 pair를 "같은 구체적 기법인가"를 요구하지
않는 두 프롬프트(Neutral: "얼마나 밀접하게 관련되어 있는가", Relation:
"함께 공부할 가치가 있는가")로 다시 채점했다.

| Modality | Ultrametric violation | Cophenetic(avg/ward) | MDS stress |
|---|---|---|---|
| Mechanism | 0.8% | 0.921 / 0.595 | 86.86 |
| Neutral | 56.6% | 0.743 / 0.683 | 34.45 |
| Relation | 55.2% | 0.562 / 0.495 | 10.54 |

"같은 구체적 기법인가"라는 요구를 빼는 순간 Tree 적합도가 붕괴한다
(violation 0.8%→55~57%, cophenetic 0.921→0.5~0.7대). 동시에 MDS
stress는 86.86→34.45→10.54로 단조 감소한다 — 위계적 판단을 덜 요구할수록
저차원 연속 공간에 더 매끈하게 펴진다. Neutral의 수치(violation 56.6%,
MDS stress 34.45)는 Experiment #52의 Embedding(53.0%, 40.17)과 상당히
근접하다.

### Finding P2-001: Prompt Objectives Determine the Observable Semantic Geometry

> Prompt wording selects which latent geometry becomes observable.
> Hierarchical prompts induce tree-like semantic organization, whereas
> relational prompts recover a continuous relatedness space.

M1(Prompt Artifact)이 M2(Model Prior)보다 현재 가장 설명력이 높은
가설이다 — 다만 "M1 채택, M2 기각"이라고 확정하지는 않는다(AI Researcher
데이터셋 하나, 모델 하나에서 나온 결과). LLM 자체가 원래 Tree 구조를
갖고 있어서가 아니라, 프롬프트가 관측하려는 기하학 좌표계 자체를
고르는 것으로 보인다. Neutral과 Embedding이 비슷한 프로파일을 보인다는
것도 이를 뒷받침한다 — Embedding이 Relatedness를 보고, Neutral 프롬프트를
받은 LLM도 Relatedness를 본다. Mechanism 프롬프트만 Hierarchy를 본다.
이건 Finding #008을 다른 방식으로 재현한 것에 가깝다.

> **Revision (Experiment #53 반영)**: Stage A/B의 Interim Conclusion을
> "Different measurement methods do not observe the same latent
> geometry"에서 아래로 강화한다 — 관측되는 지오메트리가 그냥 다른 게
> 아니라, 프롬프트가 어느 지오메트리를 관측할지를 **적극적으로
> 선택(construct)**한다는 것이 Experiment #53의 핵심 발견이기 때문이다.

> Different measurement methods actively select different latent
> geometries to observe.

## RQ10-1 (Next Question, 아직 실험 설계 전)

> Which semantic objective best predicts human organizational behavior
> — and does that answer itself vary by domain or user?

RQ10-0이 "Resolution이 데이터에 내재하는가"에 답하려다 "Objective가
Geometry를 만든다"는 걸 발견했다면, RQ10-1은 그 Objective 자체를 정면
으로 묻는 질문이다. Finding #014(적정 해상도는 도메인마다 다르다)의
교훈을 그대로 계승한다 — "고정된 하나의 정답 Objective가 있다"는
전제로 퇴행하지 않기 위해, 질문 자체에 도메인/사용자 의존성을
포함시켰다. "Mechanism이 만든 Tree가 사용자 체감 관심사 구조와
맞는가"(Experiment #53 직후 처음 떠올렸던 질문)는 이 RQ10-1의 특수
사례로 흡수된다.

**Candidate Objectives**

Observed candidates (이미 간접 증거 있음 — Experiment #45~53에서
프롬프트로 테스트됨):
- Mechanism similarity
- Topic similarity
- Conceptual relatedness (Neutral/Relation 프롬프트)

Speculative candidates (완전 미탐색, 실험 설계도 없음):
- Learning dependency
- Task substitutability
- Temporal co-occurrence
- User navigation (day/topic/text만 있는 현재 Virtual User Dataset
  스키마에 없는 행동 로그가 필요 — 실험 설계 이전에 데이터 스키마부터
  다시 설계해야 하는 별도 작업)

RQ10-1은 아직 이론 정의도 실험 설계도 없다. 이 문서(`research_phase_2_
rq10-0.md`)는 RQ10-0 전용으로 남기고, RQ10-1이 H1/H2/H3 같은 정식
protocol을 갖추면 RQ10-0처럼 별도 파일로 분리한다.

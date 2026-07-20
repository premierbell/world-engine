# Research Question 10-0: Ontology of Semantic Resolution

> Does semantic resolution exist independently of the measurement method?
> Semantic Resolution은 데이터에 내재한 속성인가, 아니면 측정 방법이
> 만들어내는 산물인가?

**Status: 🟢 Strongly Supported** (AI Researcher + Backend User 두
데이터셋에서 핵심 패턴 재현, Experiment #52/#54/#55 — 상태 표기는
✅ Answered / 🟢 Strongly Supported / 🟡 Provisionally Answered /
🔄 Re-opened 네 단계를 쓴다. 🟢는 "2개 이상 독립 데이터셋에서 재현"을
뜻하고, 3개 이상 도메인·다른 모델까지 확인되기 전에는 ✅로 올리지
않는다. 반증되면 🔄 Re-opened로 되돌린다.)

다만 이 판정은 균일하지 않다 — "Semantic Relatedness family(Topic/
Neutral/Relation)는 서로 유사한 geometry를 만든다"는 2개 데이터셋에서
재현되어 🟢지만, "Mechanism은 독립된 Hierarchical family다"는 아직
Experiment #53 하나·단일 데이터셋에서만 나온 결과라 **🟡 Provisionally
Answered**로 따로 남긴다("Measurement Families" 절 참고).

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

## Probe 0: Existing Topic Reconstruction (RQ10-0의 마지막 sanity check)

> Which semantic objective best reconstructs the existing Topic labels?

**아직 다루지 않는 질문**: "어떤 semantic objective가 사람의 실제
관심사 조직 방식을 가장 잘 설명하는가?"(RQ10-1의 질문). Ground truth가
여전히 가상 데이터셋의 수작업 Topic 레이블이라, 이 Probe는 아직 human
organization을 다루지 않는다. RQ10-1의 첫 실험이 아니라 **RQ10-0을
닫는 마지막 조각**이다 — Stage A는 "도구마다 다르다"를, Stage B는
"기하학이 다르다"를, Experiment #53은 "그 차이는 Objective에서
온다"를, 이 Probe는 "그 Objective가 현재 데이터셋의 Ground Truth와
어떻게 정렬되는가"를 보여준다.

새 LLM 호출 없음 — Mechanism/Topic/Neutral/Relation 네 캐시 재사용
(같은 36개 표본, 같은 630개 pair, `experiment_rq10_1_probe0.py`).

| Objective | ROC-AUC | Precision@0.5 | Recall@0.5 | F1@0.5 | Cohen's d |
|---|---|---|---|---|---|
| Mechanism | 0.730 | 0.857 | 0.111 | 0.197 | 2.037 |
| Topic | 0.944 | 0.490 | 0.870 | 0.627 | 3.242 |
| Neutral | 0.922 | 0.494 | 0.741 | 0.593 | 2.586 |
| Relation | 0.893 | 0.124 | 1.000 | 0.220 | 1.334 |

**두 층으로 읽는다.**

- **Layer 1 (Ranking, AUC 기준)**: Topic(0.944) ≈ Neutral(0.922) >>
  Relation(0.893) >> Mechanism(0.730). Topic과 Neutral의 차이(0.022)는
  36개 표본 수준에서 강하게 구분하기 어렵다 — 사실상 같은 family에
  가깝다.
- **Layer 2 (Calibration, Precision/Recall@0.5)**: Mechanism은 매우
  보수적(Precision 0.857, Recall 0.111), Relation은 매우 관대
  (Precision 0.124, Recall 1.000), Neutral/Topic은 그 중간. AUC는
  순위 능력을, Precision/Recall은 채점기의 관대함/보수성을 본다 —
  둘을 objective 간 서열 매기기에 같이 쓰면 안 된다.

**핵심 발견은 "Topic이 이겼다"가 아니라 "Neutral이 거의 다 했다"는
것이다.**

> The virtual Topic labels appear to be substantially aligned with
> general semantic relatedness. Explicit topic prompting provides only
> a modest improvement over a neutral relatedness judgment.

아무 위계도, 아무 주제 프레이밍도 요구하지 않은 Neutral 프롬프트가
0.922를 기록했다 — 이 가상 데이터셋의 Ground Truth Topic 레이블이
"Hierarchy"보다 "General Relatedness"에 훨씬 가까운 정의로 만들어졌을
가능성을 시사한다.

**Mechanism 최하위에 대한 해석**: Tree geometry 자체가 틀렸다고
결론짓지 않는다. Mechanism은 Precision은 높고(0.857) Recall만 극단적
으로 낮다(0.111) — 같은 Topic이지만 다른 Mechanism인 쌍 대부분을
"다르다"고 채점했다. 이건 Experiment #52/53에서 Mechanism이 가장
Tree-like했던 것(violation 0.8%)과 일관된다 — 다만 그 Tree의 분기가
Topic 레이블보다 더 세밀했을 가능성이 높다.

> Tree geometry itself is not rejected. Rather, its induced partition
> is finer than the evaluation labels.

### RQ10-0 Interim Conclusion (Probe 0 반영)

Stage A는 측정 도구마다 다르다는 것을, Stage B는 그 차이가 기하학
수준이라는 것을, Experiment #53은 그 기하학을 LLM이 아니라 Prompt
Objective가 고른다는 것을, Probe 0은 그 Objective가 현재 데이터셋의
Ground Truth와 어떻게 정렬되는지를 보여줬다. RQ10-0 — "Resolution은
데이터에 내재하는가, 측정법의 산물인가" — 에 대한 이 데이터셋 범위의
답은 여기서 일단락한다: 완전히 데이터 내재적도 아니고 완전히 임의적인
측정 artifact도 아니다. Objective가 Geometry를 만들고, 그 Geometry가
특정 Ground Truth 정의와 얼마나 잘 정렬되는지는 그 Ground Truth
자체가 어떤 개념(Hierarchy vs Relatedness)에 더 가깝게 만들어졌는지에
달려 있다.

## Experiment #55 — Probe 0 Replication on Backend User

Probe 0(Experiment #54)은 AI Researcher 데이터셋 하나에서만 나온
결과였다. 같은 평가 체계·같은 파이프라인으로 도메인만 바꿔서
재현한다(Mechanism 축은 제외 — Backend에는 mechanism 주석이 없고,
지금 확인하려는 건 Topic≈Neutral의 일반성이기 때문).

| Objective | AI Researcher (AUC) | Backend (AUC) |
|---|---|---|
| Topic | 0.944 | 0.923 |
| Neutral | 0.922 | 0.950 |
| Relation | 0.893 | 0.935 |

순위는 뒤집혔다(AI Researcher: Topic>Neutral>Relation, Backend:
Neutral>Relation>Topic) — 그러나 범위는 두 도메인 모두 0.89~0.95로
좁다. **"누가 1등이냐"는 재현되지 않았지만, "셋 다 거의 비슷하게
잘 된다"는 재현됐다.** Backend는 세 objective 모두 Precision@0.5가
AI Researcher보다 높다(Topic 0.490→0.556, Neutral 0.494→0.589,
Relation 0.124→0.243) — Calibration이 전반적으로 더 타이트하다는 뜻,
Finding #014(Backend는 Topic 간 거리가 원래 넓다)와 일관된다.
(방법론 차이: Backend 표본은 mechanism 주석이 없어 `curated_sample`
대신 단순 topic별 무작위 샘플링을 썼다 — Topic/Neutral/Relation
비교엔 mechanism 로직이 관여하지 않아 비교 자체엔 영향 없음.)

### Measurement Families

Topic/Neutral/Relation을 서로 경쟁하는 objective로 적어온 지금까지의
구성을 재검토한다. 두 도메인 모두에서 이 셋 사이의 AUC 격차보다, 이
셋 전체와 Mechanism 사이의 격차가 훨씬 크다 — 그렇다면 이 셋은
경쟁자가 아니라 같은 family로 묶는 게 더 정확하다.

| Family | Objectives | Geometry (Experiment #52/53) |
|---|---|---|
| Semantic Relatedness | Topic, Neutral, Relation | 서로 유사, Tree도 순수 Metric도 아닌 relatedness-like |
| Hierarchical Decomposition | Mechanism | 강한 Tree(ultrametric violation 0.8%) |

> Different measurement families induce different latent geometries.

> **Revision (Finding P2-001 정교화, Experiment #55 반영)**: 원래
> 문구("Prompt wording selects which latent geometry becomes
> observable")는 유지하되, 단위를 "프롬프트 하나하나"가 아니라
> "measurement family"로 명시한다 — Semantic Relatedness family
> 안에서는 프롬프트 문구가 달라도(Topic/Neutral/Relation) geometry와
> Topic 복원력이 두 도메인 모두에서 거의 같았다. Mechanism만 별도
> family였다.

**세부 확신도**: RQ10-0 전체는 🟢 Strongly Supported로 올리지만,
"Mechanism이 정말 독립된 Hierarchical family인가"는 아직 Experiment
#53 하나·단일 데이터셋에서만 나온 결과라 🟡 Provisionally Answered로
따로 남긴다 — Backend에서 Mechanism 축을 재현하려면 mechanism
주석부터 새로 만들어야 한다(아직 하지 않음).

### RQ10-0 Closed (for now) — Known Limitation / Future Work

RQ10-0은 여기서 일단 닫는다. Semantic Relatedness family(Topic/
Neutral/Relation)의 도메인 간 일반성은 2개 데이터셋에서 확인됐고,
지금 연구 전체의 병목은 더 이상 여기가 아니다.

> **Known limitation**: Mechanism family has only been validated on
> AI Researcher. Cross-domain validation remains future work.

Mechanism의 Backend 교차검증을 지금 하지 않는 이유는 단순히 "비용이
비싸서"가 아니다 — RQ10-1이 Ground Truth 자체("Topic 레이블 = 실제
관심사 조직"이라는 가정)를 다시 정의할 수도 있는데, 그러면 Mechanism을
평가하는 기준 자체가 바뀐다. 지금 Topic 레이블 기준으로는 Mechanism의
Recall이 낮았지만(Probe 0), 새 Ground Truth에서는 오히려 Mechanism이
더 나은 objective가 될 수도 있다. 즉 지금 Backend에서 Mechanism을
검증해도 RQ10-1 이후 다시 해야 할 가능성이 있다 — 순서를 뒤집는 게
비용 대비 정보 이득이 크다. 필요해지면 RQ10-1 도중에 재방문한다.

## RQ10-1 (Next Question, 아직 실험 설계 전)

> Which semantic objective best predicts human organizational behavior
> — and does that answer itself vary by domain or user?

**RQ10-1의 진짜 전환은 "어떤 Objective가 맞는가"가 아니라 "무엇을
정답으로 삼을 것인가"다.** Phase 1 내내, 그리고 Phase 2 전반부
(Stage A/B, Experiment #53, Probe 0, Experiment #55)까지도 계속 Topic
레이블을 Ground Truth로 신뢰해왔다. RQ10-1은 처음으로 그 신뢰 자체를
연구 대상으로 삼는다 — **Topic labels ≠ Human organization**일 수
있다는 가능성을 직접 다룬다. 이건 지금까지의 "어느 Objective가
이겼나" 물음과는 철학적으로 다른 질문이다.

RQ10-0이 "Resolution이 데이터에 내재하는가"에 답하려다 "Objective가
Geometry를 만든다"는 걸 발견했다면, RQ10-1은 그 Objective 자체를 정면
으로 묻는 질문이다. Finding #014(적정 해상도는 도메인마다 다르다)의
교훈을 그대로 계승한다 — "고정된 하나의 정답 Objective가 있다"는
전제로 퇴행하지 않기 위해, 질문 자체에 도메인/사용자 의존성을
포함시켰다. "Mechanism이 만든 Tree가 사용자 체감 관심사 구조와
맞는가"(Experiment #53 직후 처음 떠올렸던 질문)는 이 RQ10-1의 특수
사례로 흡수된다. Probe 0 + Experiment #55에서 본 Topic≈Neutral≈
Relation 근접(2개 도메인 재현)은 RQ10-1이 실제 사용자 데이터로
검증해야 할 첫 단서다 — 지금 이 가상 데이터셋들에서만 그런 것인지,
실제 사용자 관심사 조직에서도 "위계"보다 "관련성"이 더 본질적인지는
아직 모른다.

**Ground Truth Redesign이 RQ10-1의 첫 하위 과제다.** 지금까지 쓴
"Topic 레이블"은 가상 유저를 만들 때 수작업으로 부여한 것이라, 실제
사용자의 관심사 조직 방식의 근사치일 뿐이다. 이 근사치를 넘어서는
새로운 신호가 무엇일 수 있는지(예: persona가 직접 스크랩을 재분류한
결과, 시간에 따른 재구성, 여러 명이 같은 스크랩 세트를 조직했을 때의
일치도)는 아직 이론도 실험 설계도 없다 — 여기서부터 시작해야 한다.

### Ground Truth Redesign 설계 (실행 전, 데이터 수집 대기 중)

네 가지 후보를 검토했다 — Self-consistency re-labeling(동일 페르소나
재분류), Multi-rater agreement(여러 페르소나 간 합의도), Task-oriented
retrieval grouping(검색/회수 목적 기준 그룹화), 실제 사용자 데이터.
앞의 셋은 여전히 시뮬레이션 안에서 도는 방법이고, 넷째만 시뮬레이션을
벗어난다 — **실제 사용자 데이터를 중심에 두고, 나머지 셋은 보조
검증으로 쓴다.** 지금까지 모든 연구가 "Virtual User → Ground Truth →
Evaluation"이었다면, 여기서 처음으로 "Real User → Organization →
Ground Truth"로 방향이 뒤집힌다.

**새로 열린 질문**: 지금까지는 "정답 Topic이 무엇인가"를 물었지만,
실제 사람은 관심사를 taxonomy(분류 체계)가 아니라 workflow(용도) 
기준으로 조직할 수도 있다 — 예를 들어 Redis/Kafka/RabbitMQ를 "Message
Queue"로 묶는 사람도 있지만, "Backend Interview 준비"로 묶는 사람도
있다. 둘 다 틀리지 않았다. Phase 1/Phase 2 전반부는 전부 "정확한
Topic을 찾는 연구"였다면, 여기서부터는 **"무엇을 정답으로 볼 것인가를
정의하는 연구"**로 성격이 바뀐다.

**Stage 0 — Real Human Organization Collection** (데이터 수집 대기 중,
`experiments/real_user_organization/round1.json`): 사용자 본인의 실제
스크랩 20~30개를 모으고(평소에 발견할 때마다 조금씩), 카테고리를
미리 정하지 않은 채 자유롭게 그룹화 → 그룹 이름 → 그룹화 이유 한 줄
→ 중복 소속 허용. 이게 새로운 Ground Truth가 된다.

**Stage 1** — Mechanism/Topic/Neutral/Relation 네 objective(Measurement
Families)가 이 실제 Ground Truth를 얼마나 설명하는지 본다. 여기서
처음으로 "어떤 objective가 실제 사람의 조직 방식을 가장 잘 설명하는가"
를 말할 수 있게 된다.

**Stage 2** — 어떤 objective도 잘 설명하지 못하면, 그때 새로운
objective(Adaptive Objective, Graph Objective 등)를 고민한다.

표본이 20~30개로 작다는 것과, 사용자 한 명(N=1)이라는 것은 명확한
한계로 남긴다 — 그럼에도 지금까지의 모든 결론이 가상 데이터 안에서만
성립했다는 근본적 한계를 정면으로 다루는 첫 시도라는 점이 값지다.

**Candidate Objectives**

이제 Topic/Neutral/Relation을 서로 다른 후보로 나열하지 않는다 —
"Measurement Families" 절(Experiment #55)에서 이 셋은 하나의 family로
묶였다.

Observed candidates (이미 간접 증거 있음):
- **Semantic Relatedness family** (Topic/Neutral/Relation) — 🟢
  2개 도메인(AI Researcher, Backend)에서 서로 유사한 geometry·Topic
  복원력 확인
- **Hierarchical Decomposition family** (Mechanism) — 🟡 1개 도메인
  (AI Researcher)에서만 확인, 독립된 family인지 아직 Provisional

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

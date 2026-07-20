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

## RQ10-1 (Next Question)

> Which semantic objective best predicts real-world personal
> organization? — and does that answer itself vary by domain or user?

> **Revision (Experiment #56 Stage 1 Pilot 반영)**: 원래 문구
> ("...human organizational behavior")에서 "real-world personal
> organization"으로 좁혔다 — Stage 1 Pilot에서 Ground Truth가 가상
> 데이터의 Topic 레이블과 실제 개인 스크랩 조직 사이에서 서로 다른
> objective를 요구한다는 게 드러났기 때문에, 어느 쪽을 말하는지
> 질문 자체에서 명시할 필요가 있었다.

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

**Stage 0 — Real Human Organization Collection: 완료.** 사용자 본인의
실제 스크랩 25개(`experiments/real_user_organization/round1.json`,
로컬 전용 - 개인 데이터라 커밋 안 함)를 모으고, 카테고리를 미리
정하지 않은 채 자유롭게 그룹화(13개 그룹, 그 중 6개는 단독 항목) →
그룹 이름·이유 → 중복 소속 허용 방식으로 완료. 각 scrap은
`content_summary`(실제 URL 내용 요약, 150~300자)와 `personal_reason`
(저장 당시 이유)을 분리해서 기록 - 이후 Stage 1에서 "내용만" vs
"내용+저장 이유"를 각각 평가에 써서 비교하기 위함. 데이터 품질도
`fetch_status`로 표시: 25개 중 9개는 원문 직접 fetch, 15개는 원문
접근이 막혀(naver blog·namu.wiki의 봇 차단) 검색 스니펫으로 대체,
1개는 완전히 실패해 note만 신뢰 가능 - 균일하지 않은 데이터 품질을
Stage 1 해석 시 감안해야 한다.

**Stage 1 Pilot 완료(Experiment #56)** — Mechanism/Topic/Neutral/
Relation 네 objective를 content_summary만으로 채점(personal_reason은
Ground Truth를 직접 노출하는 leakage 위험이 있어 제외 - "공부용/
공부용"처럼 저장 이유가 그대로 겹치면 내용이 아니라 이유를 읽고
맞힐 수 있음), 실제 그룹화(N=24, same-group 19쌍/276쌍) 대비 ROC-AUC:

| Objective | ROC-AUC | mean same-group | mean diff-group |
|---|---|---|---|
| Mechanism | 0.500 | 0.000 | 0.000 |
| Topic | 0.723 | 0.239 | 0.012 |
| Neutral | **0.918** | 0.200 | 0.038 |
| Relation | 0.903 | 0.413 | 0.182 |

**해석**:
- **Mechanism = 0.500은 실패가 아니라 적용 범위 밖(narrow domain of
  applicability)이다.** AI Researcher(Transformer/Attention/Flash
  Attention)처럼 단일 기술 도메인 안에서만 "같은 구체적 메커니즘"이
  성립한다 - 백엔드/야구/여행/건강/투자/쇼핑이 뒤섞인 이 데이터에는
  애초에 그런 쌍이 존재하지 않는다. Measurement Family 자체가
  틀렸다는 뜻이 아니라, Hierarchical Decomposition family가 정의되는
  전제조건(도메인 내부 밀집도)이 여기서 충족되지 않았다.
- **Topic(0.723)이 Neutral(0.918)/Relation(0.903)보다 뚜렷이 낮다.**
  가상 데이터셋(Probe 0, Experiment #55)에서는 Topic≈Neutral≈Relation
  이었는데(0.89~0.95 범위), 여기서 갈라졌다. 원인 후보: 사용자의 실제
  그룹("여행, 이동용" = 전주 여행+여수 맛집+아쿠아리움+강남 맛집,
  "건강용" = 다이어트 음식+거북목 스트레칭+헬스 루틴)은 **같은 Topic
  이 아니라 같은 task bundle**(나중에 같이 참고할 것)로 묶여 있다 -
  Topic이 묻는 "같은 상위 주제인가"는 이 조직 원리와 어긋나고,
  Neutral/Relation이 묻는 "관련 있는가/같이 볼 가치 있는가"가 더
  가깝다.
- Relation은 same-group 평균(0.413)이 가장 높지만 diff-group
  평균(0.182)도 가장 높다 - AUC는 좋지만 threshold 설정이 여전히
  까다롭다(Experiment #52/#55에서 반복된 calibration 패턴).

**한 줄 요약**: 가상 데이터에서는 Topic-based objective가 충분했지만,
실제 개인 스크랩에서는 Topic보다 Task/Usage relatedness가 사용자의
조직 방식을 더 잘 설명했다.

**Stage 2a(Experiment #57) — 질문을 Ground Truth와 정렬**: "사용자가
나중에 함께 다시 찾아볼 가능성이 높은가"로 재정렬한 새 프롬프트
(`retrieval` mode, content_summary만 사용)를 Neutral/Relation과
나란히 비교.

| Objective | ROC-AUC | mean same-group | mean diff-group |
|---|---|---|---|
| Neutral | 0.918 | 0.200 | 0.038 |
| Relation | 0.903 | 0.413 | 0.182 |
| Retrieval | 0.913 | 0.366 | 0.144 |

세 값이 0.90~0.92에 몰려 있다 - N=19 positive 규모에서는 사실상
구분 불가. **질문 재정렬 자체는 뚜렷한 개선을 주지 않았다** - Topic처럼
엄격한 매칭만 아니면(Semantic Relatedness family 안이면) 구체적 문구는
중요하지 않다는 쪽으로 해석이 좁혀진다.

**Stage 2b(Experiment #58) — personal_reason을 컨텍스트로 추가**:
Neutral 하나만 대표로 써서(Measurement Family는 이미 충분히 검증됐다고
보고), content_summary만 vs content_summary+personal_reason 비교.

| Condition | ROC-AUC | mean same-group | mean diff-group |
|---|---|---|---|
| content only | 0.918 | 0.200 | 0.038 |
| content + reason | 0.921 | 0.239 | 0.052 |

AUC 차이는 노이즈 수준. Error analysis(가장 심하게 틀린 pair들의
before/after)에서도 뚜렷이 고쳐진 사례가 없었다 - 가장 심한 false
negative(s12-s15, 여수 맛집 vs 롯데월드 아쿠아리움)도 0.10→0.15,
가장 심한 false positive(s1-s5)는 0.75→0.75로 그대로.

### Finding P2-002: Prompt Engineering Is Not the Bottleneck for Real Organization

> Within the current dataset, neither prompt wording nor coarse
> personal reasons substantially improve prediction of human
> organization. The bottleneck appears to be missing behavioral
> context rather than prompt formulation.

Round 1에서 두 축을 이미 건드렸다 - 질문을 바꿨고(Neutral/Relation/
Retrieval), 입력을 늘렸다(content+personal_reason). 둘 다 거의 같은
결과로 수렴했다. "더 좋은 prompt를 찾으면 풀린다"는 가설은 이 지점에서
꽤 강하게 기각된다.

**왜 personal_reason이 안 통했는가**: 지금 있는 `personal_reason`은
대부분 content에서 이미 추론 가능한 정보였다 - "도커 입문" 글에
"공부용"이라고 적어봐야 LLM도 content만 보고 그 정도는 이미 짐작한다.
진짜 새로운 정보가 되려면 content에서 절대 추론 불가능한 것이어야
한다 - "이번 프로젝트 끝나고 적용하려고", "여행 갈 때 여자친구랑
보려고", "이사하면 살 예정" 같은, content 밖에 있는 **행동 맥락
(behavioral context)**. 지금 personal_reason은 이런 의미의 metadata가
아니라 content의 요약에 더 가까웠다.

### Round 1 종료 (N=25 Pilot)

**확인된 것**:
- Mechanism family는 실제 개인 스크랩(여러 인생 영역이 섞인 데이터)에는
  적용 범위 밖 (Experiment #56)
- Semantic Relatedness family(Neutral/Relation/Retrieval)는 서로 거의
  동일하게 작동 (Experiment #57)
- Prompt wording을 더 정교하게 바꿔도 영향이 거의 없음 (Experiment #57)
- 현재 수준의 personal_reason도 영향이 거의 없음 (Experiment #58,
  Finding P2-002)

**확인되지 않은 것**:
- 사용자의 실제 조직 원리는 아직 복원되지 않았다.

**가장 중요한 산출물**: "LLM이 사용자 조직을 못 맞춘다"가 아니라,
**"현재 스크랩 데이터(content_summary + 짧은 저장 이유)만으로는 사용자
조직을 복원할 만큼의 정보가 애초에 없다"**는 것 - 이건 objective를
더 찾는 문제가 아니라 정보 자체가 부족한 문제다.

새 personal_reason(진짜 behavioral context)을 만들려면 사용자가 25개를
다시 보면서 "왜/언제/어떤 상황에서 다시 볼지"를 새로 적어야 한다 -
사실상 Round 1.5(새 데이터셋 제작)이므로, 지금 바로 하지 않고 Round 1은
여기서 닫는다. 표본이 25개(N=1 사용자)라는 한계도 명확히 남긴다.

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

### Objective Discovery → Information Discovery

Round 1(Finding P2-002)을 거치며 RQ10-1의 질문 자체가 한 단계
올라갔다.

- 처음: **Which semantic objective explains human organization?**
- 지금: **What information is actually used by humans when
  organizing personal knowledge?**

Round 1은 "질문(objective)을 바꾸는 축"을 거의 다 시도했고 전부 비슷한
천장(AUC ~0.90~0.92)에 부딪혔다. 남은 변수는 질문이 아니라 입력
(content_summary + 얕은 personal_reason)이 애초에 사용자의 조직 원리를
담고 있지 않다는 것 - 그래서 다음 질문은 "어떤 objective가 맞는가"가
아니라 **"사용자 조직을 복원하려면 어떤 정보를 새로 수집해야 하는가"**
(예: 진짜 behavioral context - 언제/누구와/어떤 상황에서 다시 볼
것인지)이다.

Phase 1은 Resolution을 찾았고, RQ10-0은 Measurement Family를 찾았고,
RQ10-1 Round 1은 정보 부족을 발견했다 - 각 단계가 앞 단계의 한계를
이어받는 구조다. **Round 1.5의 목적은 새 알고리즘이 아니라, 사람의
조직 방식을 설명하는 행동 정보가 무엇인지 규명하는 것이다.**

### Round 1.5 설계 (실행 전, 데이터 수집 대기 중)

Round 1의 `personal_reason`(예: "도커 공부용")이 안 통했던 이유는
대부분 content에서 이미 추론 가능한 정보였기 때문이다(Finding
P2-002). Round 1.5는 content에서 절대 추론 불가능한, 진짜
behavioral context를 25개 스크랩 각각에 대해 새로 받는다. 질문을
많이 만들지 않고 4개로 제한한다:

1. **왜 저장했는가?** (purpose)
2. **언제 다시 볼 것인가?** (time horizon)
3. **무슨 상황에서 다시 찾을 것인가?** (trigger/reuse scenario) -
   가장 중요하게 보는 축. 예: 전주 여행 스크랩의 Topic은 "여행"이지만
   Trigger는 "전주 가기 직전"; 강남 맛집은 "강남 갈 때"; 냉장고는
   "이사하면". 지금 데이터에는 이 정보가 없다.
4. **못 찾으면 얼마나 곤란한가?** (importance) - pairwise 비교
   프롬프트에 자연스럽게 안 들어가는 개별 속성이라, 수집은 하되
   Stage 1.5에서 pairwise 입력으로 쓸지 별도 분석 축으로 둘지는
   결과를 보고 나중에 결정한다.

**Stage 1.5 실험**: content_summary만 vs content_summary+behavioral
context(위 4개, 최소 1~3번)로 Neutral(Round 1에서 검증된 대표
objective) 채점을 비교, 실제 그룹 복원력(AUC)을 본다. 여기서 의미
있게 개선되면 **"사람은 semantic similarity보다 behavioral context를
더 많이 사용해 지식을 조직한다"**는 강한 결론을 낼 수 있다.

아직 데이터 수집 전이다. 이 문서(`research_phase_2_rq10-0.md`)는
RQ10-0·RQ10-1 Round 1/1.5 전용으로 남기고, Information Discovery가
H1/H2/H3 같은 정식 protocol을 갖추면 별도 파일로 분리한다.

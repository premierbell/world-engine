# V0 Validation Log

## Experiment #1 (Pilot)
날짜: 2026-07-16
목적: OpenAI 임베딩의 유사도 분포를 관찰한다.
데이터: 3개 (Spring Boot 성능 튜닝 / Redis 캐싱 / 손흥민 골)
결과:
- Spring Boot 성능 튜닝 vs Redis 캐싱: 0.2879
- Spring Boot 성능 튜닝 vs 손흥민 골: 0.1732
- Redis 캐싱 vs 손흥민 골: 0.2420
결론: 데이터가 너무 적어 threshold를 결정하기 어렵다. 절댓값이 예상보다 낮은 좁은 대역(0.17~0.29)에 몰려 있음 — 다음 실험에서는 카테고리별 10~20개의 샘플을 사용한다.

## Experiment #2
날짜: 2026-07-16

### Hypothesis
카테고리(Backend/Sports/AI) 내부 유사도가 카테고리 간 유사도보다 높을 것이다.

### Data
Backend 8개, Sports 6개, AI 6개 (총 20개, pairwise 190쌍)

### Result
- 카테고리 내부 평균: Backend 0.2800(0.1029~0.6017, N=28), Sports 0.2839(0.1484~0.4005, N=15), AI 0.2342(0.1418~0.3206, N=15)
- 카테고리 간 평균: Backend↔Sports 0.0926(0.0119~0.2461, N=48), AI↔Backend 0.1816(0.0621~0.2737, N=48), AI↔Sports 0.1402(0.0458~0.2543, N=36)

### Insight
평균으로는 카테고리 내부 > 카테고리 간이라 가설은 지지된다. 하지만 Backend 내부 범위(0.10~0.60)가 매우 넓고, 그 최솟값(0.10)이 AI↔Backend 카테고리 간 평균(0.18)보다도 낮다 — 즉 "같은 Backend인데 안 닮은 쌍"이 "다른 카테고리인데 좀 닮은 쌍"보다 유사도가 낮은 역전이 존재한다.

이는 Backend가 단일 클러스터가 아니라 Spring/JPA, Redis/Kafka, Docker/Kubernetes, MySQL 같은 여러 하위 토픽으로 이미 나뉘어 있다는 뜻으로 해석된다 — `growth_rules.md`의 "Building은 클러스터 형성 시 생긴다" 규칙이 데이터로 뒷받침된 첫 사례.

**결론 수정**: "단일 Threshold는 어렵다"가 아니라, **단일 Threshold만으로는 Island 편입과 Topic(Building) 분리를 동시에 결정할 수 없다**로 정정. 향후 Island Threshold와 Topic Threshold를 분리할 필요가 있을 가능성이 높다.

부가 관찰: AI↔Backend(0.18)가 다른 카테고리 간 쌍보다 상대적으로 높음 — LLM/Vector DB/MCP 같은 개념이 Backend와 실제로 연결되어 있다는 신호. V3의 Bridge 설계와 연결해 계속 관찰할 가치가 있음.

### Next Experiment
같은 내용을 제목 / 제목+요약 / 본문 수준으로 각각 임베딩해, 텍스트 길이가 같은 Topic끼리의 유사도를 얼마나 강하게 모으는지 확인한다 (Experiment #3).

## Experiment #3
날짜: 2026-07-16

### Hypothesis
텍스트 길이가 늘어나면 같은 Topic끼리 더 잘 모일 것이다.

### Data
Spring/JPA 2편, Redis 2편(그중 1편은 제목에 "Spring Boot"가 섞인 edge case) × title/summary/body 3단계

### Result
| Input | Same Topic | Cross Topic | Gap |
|---|---|---|---|
| Title | 0.529 | 0.312 | 0.217 |
| Summary | 0.631 | 0.326 | 0.306 |
| Body | 0.683 | 0.314 | 0.369 |

### Insight
텍스트를 늘려도 Cross Topic은 거의 변하지 않는다. 대신 Same Topic만 크게 증가한다. 즉, 정보량이 늘어날수록 관련 있는 것만 더 강하게 묶인다.

Same Topic 평균(0.53~0.68)이 Experiment #2의 Backend 카테고리 내부 평균(0.28)보다 훨씬 높은 것도 의미가 있음 — 여기서 "같은 Topic"은 좁은 하위 주제(JPA N+1 vs Fetch Join)이고 #2의 "Backend"는 Island 수준(여러 하위 토픽 혼합)이라 스케일이 다르다. Island 유사도와 Topic 유사도가 실제로 다른 대역에 있다는 것을 재확인.

### Product Decision
V1에서는 제목만 임베딩하지 않는다. 최소한 요약(Summary) 수준 이상의 텍스트를 확보하여 임베딩한다.

### Next Experiment
Title→Summary Gap 개선폭(+41%)에 비해 Summary→Body 개선폭(+20%)이 줄어드는 것으로 보임 — Quality(Gap) vs Cost(토큰 수) vs Latency를 정량적으로 측정해 Summary가 실제로 비용 대비 최적점인지 확인한다 (Experiment #4).

## Evaluation Metric Update #1: Average Efficiency → Marginal Efficiency
날짜: 2026-07-16

### Problem
Experiment #4에서 처음 정의한 지표 `Gap / Total Tokens`(평균 효율)를 계산했더니 Title(17.712)이 Summary(4.810), Body(2.117)보다 압도적으로 높게 나왔다. 이는 Summary가 가성비 최적일 것이라는 가설과 정반대로 읽힌다.

원인을 보면, 이 지표는 "0 토큰부터 지금까지의 평균 기울기"라서 분모가 작은 쪽(Title)이 구조적으로 항상 유리하다 — 모델이나 데이터의 특성이 아니라 **지표 자체의 결함**이다.

### Fix
`Gap / Total Tokens`(평균 효율) 대신 `ΔGap / ΔTokens`(한계 효율, Marginal Efficiency)를 사용한다. 이는 한 입력 단계에서 다음 단계로 텍스트를 늘릴 때, 추가로 쓴 토큰이 얼마나 값어치를 했는지를 측정한다.

### Impact
이 지표 교체가 Experiment #4의 Product Decision #001 근거를 뒷받침한다. 앞으로 "비용 대비 효율"을 다루는 모든 실험은 평균이 아니라 한계 효율 기준으로 측정한다 (`docs/evaluation_metrics.md` 참고).

## Experiment #4: Summary vs Body Efficiency
날짜: 2026-07-16

### Hypothesis
Summary가 Body보다 토큰 비용 대비 효율적인 선택일 것이다.

### Data
`length_comparison.json` 동일 데이터(Title/Summary/Body × 4편). tiktoken으로 토큰 수 측정.

### Result
| Input | Gap | Avg Tokens |
|---|---|---|
| Title | 0.2170 | 12.2 |
| Summary | 0.3054 | 63.5 |
| Body | 0.3689 | 174.2 |

**Marginal Efficiency (ΔGap / ΔTokens):**
- Title → Summary: +0.0884 gap / +51.3 tokens ≈ **1.72** gap/1K tokens
- Summary → Body: +0.0635 gap / +110.7 tokens ≈ **0.57** gap/1K tokens

(Latency는 N=4·1회 측정이라 노이즈가 커서 이번 실험에서는 신뢰할 수 있는 신호로 채택하지 않음.)

### Insight
전형적인 수확 체감(Diminishing Returns) 곡선. Title→Summary 구간의 한계 효율이 Summary→Body 구간보다 3배 가까이 높다 — Summary까지는 텍스트를 늘릴 가치가 뚜렷하지만, Body까지 더 늘리는 추가 투자는 효율이 급감한다.

### Product Decision #001
**Embedding의 기본 입력은 Summary를 사용한다.**

이유:
- Title보다 같은 Topic 분리(Gap)가 크게 향상된다 (Experiment #3).
- Full Body보다 토큰 비용 대비 한계 효율이 높다 (Experiment #4).
- Body는 추가 개선은 있지만 한계 효율이 낮아 기본값으로 정당화하기 어렵다.

## Experiment #5: Threshold Sweep (v1 — 데이터셋 결함 발견)
날짜: 2026-07-16

### Hypothesis
Island Threshold와 Topic Threshold를 분리해서 Precision/Recall을 sweep하면 각각의 적정 구간을 찾을 수 있다.

### Data
`golden_dataset/threshold_dataset.json` — 기존 카테고리 데이터에 island/topic 라벨을 붙인 20개 키워드 수준 텍스트("Spring Boot JPA", "MySQL Index" 등).

### Result
| Island Threshold | Precision | Recall |
|---|---|---|
| 0.30 | 1.000 | 0.276 |
| 0.35~0.60 | 1.000 | 0.155 → 0.017 (감소) |

| Topic Threshold | Precision | Recall |
|---|---|---|
| 0.50~0.55 | 1.000 | 0.143 |
| 0.60 | 1.000 | 0.071 |
| 0.65~0.80 | nan | 0.000 |

### Insight
Topic Threshold sweep이 사실상 무력화됨 — `config.yaml` 초기값(0.65)에서 Recall이 0. 그런데 이건 모델/알고리즘의 실패가 아니라 **실험 데이터가 제품과 불일치하는 문제**로 해석해야 한다: `threshold_dataset.json`의 텍스트는 2~3단어 키워드 수준인데, Product Decision #001은 이미 "Embedding 기본 입력은 Summary"로 정해뒀다. 즉 실제 제품이 받을 입력(Summary)보다 훨씬 정보량이 적은 텍스트로 실험한 셈이라, 실험이 제품을 검증하지 못하고 있었다.

Island Threshold는 스윕한 구간(0.30~0.60) 전체에서 Precision이 1.000으로 유지돼, 아직 Precision이 무너지는 지점을 찾지 못함 — 스윕 범위를 더 낮게 확장해야 한다.

### Decision
1. Threshold Dataset을 Product Decision #001에 맞춰 Title/Summary 두 티어로 재구성한다 (`golden_dataset/threshold/title/`, `golden_dataset/threshold/summary/`).
2. Island Threshold sweep 범위를 0.10~0.30 구간은 0.02 단위로 촘촘하게, 0.30~0.60은 기존 0.05 단위로 확장한다.
3. Topic Threshold는 지금 결론 내리지 않고, 새 데이터로 재검증할 때까지 보류한다.

이 실험 자체는 "실패"가 아니라 V0가 알고리즘뿐 아니라 실험 설계·데이터셋 품질까지 함께 검증하고 있다는 신호로 기록한다.

## Experiment #6: Threshold Sweep (v2 — Title/Summary 티어, 확장 범위)
날짜: 2026-07-16

### Hypothesis
Threshold Dataset을 Product Decision #001에 맞춰 Summary 수준으로 바꾸고, Island Threshold sweep 범위를 0.10까지 넓히면 Precision이 무너지는 지점을 찾을 수 있다.

### Data
`golden_dataset/threshold/title/dataset.json`, `golden_dataset/threshold/summary/dataset.json` (동일 20개, Title/Summary 두 버전)

### Result

**Island Threshold Sweep**
| Threshold | Title P/R | Summary P/R |
|---|---|---|
| 0.10 | 0.347 / 1.000 | 0.331 / 1.000 |
| 0.18 | 0.483 / 0.966 | 0.446 / 1.000 |
| 0.20 | 0.544 / 0.966 | 0.514 / 0.983 |
| 0.22 | 0.568 / 0.862 | 0.567 / 0.948 |
| 0.24 | 0.629 / 0.759 | 0.590 / 0.845 |
| 0.30 | 0.735 / 0.431 | 0.652 / 0.517 |
| 0.40 | 1.000 / 0.086 | 0.909 / 0.172 |

F1 최고 구간: Title 0.20~0.24 (F1≈0.68~0.70), Summary 0.22 (F1≈0.71) — 사실상 동률.

**Topic Threshold Sweep (같은 Island 내부)**
| Threshold | Title P/R | Summary P/R |
|---|---|---|
| 0.50 | 1.000 / 0.214 | 1.000 / 0.143 |
| 0.60 | 1.000 / 0.071 | 1.000 / 0.071 |
| 0.65+ | 1.000→nan / 0.071→0.000 | nan / 0.000 |

### Insight
**Island Threshold는 이제 근거를 갖췄다.** Precision이 0.10(≈0.33)에서 0.40(1.000)까지 뚜렷하게 상승하는 곡선을 확인했고, F1 기준 최적 구간은 0.20~0.24. Title과 Summary가 이 구간에서 거의 동일한 성능을 보인 것은 Experiment #3과 모순이 아니라 **관찰 대상이 다르기 때문**으로 해석: Island는 Backend/Sports/AI처럼 의미적으로 크게 다른 거친 구분(Macro Semantic Space)이라 Title만으로도 충분히 구분되지만, Topic은 Spring/Redis/Kafka처럼 미세한 구분(Micro Semantic Space)이라 정보량(Summary)이 더 중요하다. 즉 **Island와 Topic은 서로 다른 난이도의 분류 문제**이며, 이는 World Engine의 계층 구조(Island → Topic)를 데이터로도 뒷받침하는 결과다.

**Topic Threshold는 여전히 결론 낼 수 없다.** 이번에도 Recall이 낮게 나왔지만(최대 0.214), same-topic pair가 13개뿐이라(대부분의 Topic이 1개 항목이라 pair 자체가 안 생김) 통계적으로 신뢰할 수 없다. Title이 Summary보다 근소하게 높게 나온 것도 이 작은 표본(N=13)의 노이즈로 보인다 — 통제된 설계였던 Experiment #3이 훨씬 신뢰할 만하다.

### Decision
- Recall이 낮다고 곧바로 threshold를 낮추지 않는다 — 대신 "이 데이터셋이 Topic을 검증하기에 적절한가"부터 되묻는다.
- Island Threshold는 후보(0.20~0.24)를 찾았지만 아직 **확정하지 않는다** — Topic 검증 과정에서 전처리/입력이 바뀌면 Island 결과도 달라질 수 있어, Topic 검증을 먼저 마친 뒤 마지막에 확정한다.
- `config.yaml`에는 확정값이 아니라 "후보(candidate)"임을 주석으로 명시한다.

### Next Experiment
Topic 전용 golden dataset을 새로 만든다 — 토픽당 최소 5개씩, 여러 Topic(Backend: Spring/Redis/Kafka, AI: RAG/LLM, Sports: Football/Baseball)에 걸쳐 구성해 same-topic pair 표본을 충분히 확보한다 (Experiment #7).

## Experiment #7: Topic 전용 Golden Dataset + F1/PR Curve
날짜: 2026-07-16

### Hypothesis
Topic Threshold의 최적점은 이전 스윕 범위(0.50~0.80) 바깥, 더 낮은 구간에 있을 것이다 (Island 때와 같은 패턴).

### Data
`golden_dataset/threshold/topic/dataset.json` — 7개 Topic(Spring/JPA, Redis, Kafka, RAG, LLM, Football, Baseball) × 5개씩, 35개. Topic당 표본이 충분해 same-topic pair가 70개로 늘어남(기존 13개 대비).

### Result

**Island Threshold (topic_focused 데이터셋)** — F1 최고 0.671 @ 0.26

**Topic Threshold (topic_focused 데이터셋)**
| Threshold | Precision | Recall | F1 |
|---|---|---|---|
| 0.35 | 0.575 | 0.657 | 0.613 |
| 0.38 | 0.672 | 0.614 | 0.642 |
| 0.40 | 0.736 | 0.557 | 0.634 |
| 0.42 | 0.822 | 0.529 | **0.643** ← 최고 |
| 0.45 | 0.889 | 0.457 | 0.604 |
| 0.50 | 0.913 | 0.300 | 0.452 |

PR 커브 6장을 `experiments/plots/`(island_pr_*.png, topic_pr_*.png, 티어별 3개씩)에 저장.

### Insight
가설이 정확히 맞았다 — 진짜 최적점(F1 0.643 @ 0.42)은 이전 스윕(0.50~)이 놓친 구간에 있었다. Island 때와 동일한 함정(스윕 범위가 최적점을 못 담음)을 Topic에서도 겪었고, 똑같은 방식(범위 확장)으로 해결했다.

Island 최고 F1(0.67~0.71)과 Topic 최고 F1(0.64)의 격차가 처음 추정했던 것보다 크지 않다 — "Topic이 더 어렵다"는 방향은 맞지만, 제대로 튜닝하면 극단적인 차이는 아니다. Island(0.22~0.26) < Topic(0.38~0.42)라는 계층 구조는 유지된다.

### Baseline Decision
`island_threshold: 0.24`, `topic_threshold: 0.42`를 **baseline**으로 채택한다 (validated/확정이 아니라 "V0 실험에서 얻은 초기 기준값"). 세 개의 독립된 데이터셋(categories/length_comparison/topic 전용)에서 threshold sweep + PR curve로 근거를 확보했지만, 지금까지 검증한 도메인이 Backend/AI/Sports로 좁다는 한계가 있다 — 투자/여행/요리/영화 같은 더 다양한 도메인과 "LLM을 이용한 주식 분석" 같은 경계 사례는 아직 검증 못 함.

### Next (Backlog, V0 완료를 막지 않음)
`golden_dataset/general_topics/`에 15개 안팎의 다양한 도메인(금융/여행/요리/영화/건강/역사/과학/디자인/사진/언어 등, 도메인당 5~10개, 총 100~150개)을 추가해 **Threshold를 찾기 위한 실험이 아니라 회귀 테스트(Regression Dataset)**로 운용한다. 목적은 새 값을 찾는 게 아니라, 앞으로 임베딩 모델/threshold/클러스터링 로직이 바뀔 때마다 "이전보다 좋아졌는가"를 계속 확인하는 것.

## Step 5 — 실제 Island/Topic 편입 로직 (build_world.py)
날짜: 2026-07-16

`golden_dataset/threshold/topic/dataset.json`(35개, 정답 라벨 있음)을 무작위 순서로 하나씩 흘려보내 실제 Island/Topic 편입 로직(`world.py`)을 검증. Topic 분류는 Kafka 5/5, RAG 5/5, Spring/JPA 5/5로 거의 완벽했지만, Island이 35개 전부 하나로 뭉쳐버림(기대: Backend/AI/Sports 3개).

**진단(Instrumentation)**: `assign_scrap()`이 매 결정을 `AssignmentTrace`로 반환하도록 확장해 Island별 유사도, threshold 비교, center drift를 전부 로그로 남김.
- 버그 없음 — threshold 비교는 로그 전체에서 정확했다.
- Threshold가 다소 낮았다 — 최저 병합 유사도 0.2533(threshold 0.24를 겨우 0.013 차이로 통과, Sports 항목).
- **EMA Drift가 결정적**: Island의 origin(최초 벡터) 대비 현재 center의 유사도가 0.99 → 0.52까지 떨어짐(35개 처리 후). 게다가 "가장 가까운 Island 유사도"의 전체 평균(0.444)이 threshold(0.24)보다 훨씬 높게 유지됨 — 섬이 다양해질수록 center가 "이도저도 아닌 평균"이 되어 오히려 다음 항목을 더 쉽게 흡수하는 자기강화(runaway) 구조였다.

**Fix — Identity/Growth 분리**: `Island`이 `identity_vector`(생성 시 고정, 절대 갱신 안 함 — Island 편입 판단 기준)와 `growth_vector`(EMA, 판단에는 안 씀)를 분리해서 갖도록 재설계. `identity_stability = cosine(identity_vector, growth_vector)`를 Identity Drift 모니터링 지표로 채택(`evaluation_metrics.md`의 "Island Stability" TODO를 이걸로 채움).

**재실행 결과**: Sports가 정확히 분리됨(Island 1, 10개 = 축구5+야구5 정확히 일치). 평균 유사도도 0.444 → 0.328로 감소(runaway 해소). 다만 Backend+AI는 여전히 하나로 뭉침 — 이건 이제 drift 버그가 아니라, threshold=0.24에서 Precision이 애초에 ~0.6이었다는 Experiment #6/#7 예측과 일치하는 정상 범위의 오차.

## Experiment #8: Online Island Threshold Sweep
날짜: 2026-07-16

### Hypothesis
Identity/Growth 분리로 알고리즘이 바뀌었으니, island_threshold를 0.24에서 점진적으로 올리면(0.26→0.34) Backend와 AI가 분리되는 지점을 찾을 수 있다.

### Data
`golden_dataset/threshold/topic/dataset.json`, 동일 shuffle(seed=42). 임베딩은 threshold와 무관하므로 한 번만 계산해 재사용.

### Result
| Threshold | Islands | Composition 요약 |
|---|---|---|
| 0.24 | 2 | Backend+AI 뭉침 / Sports 분리 |
| 0.26 | 4 | Sports도 쪼개짐, 3개 도메인 섞인 섬 등장 |
| 0.28 | 5 | Backend/AI/Sports 전부 부분적으로 쪼개짐 |
| 0.30 | 7 | |
| 0.32 | 9 | |
| 0.34 | 10 | |

### Insight
"언더분리(2개) → 정확히 3개 → 오버분리" 순서가 아니라 "언더분리 → 바로 오버분리"로 건너뛴다. 정확히 3개(Backend/AI/Sports)로 갈리는 안정적인 threshold 구간이 스윕 범위 안에 없었다. → `docs/algorithm_limitations.md` Finding #001의 첫 번째 근거.

## Experiment #9: Order Sensitivity Test
날짜: 2026-07-16

### Hypothesis
Experiment #8의 결과는 threshold 문제가 아니라 Greedy Online Assignment의 입력 순서 의존성 때문일 것이다.

### Data
동일 데이터셋, island_threshold를 0.24와 0.28로 고정하고 입력 순서만 5가지(random seed 1~5)로 바꿔서 실행.

### Result
- `island_threshold=0.24`: Island 개수 **2~4개**로 요동. 어떤 도메인끼리 섞이는지도 매번 다름(seed 1: Sports+AI+Backend 혼합, seed 4: Sports+AI 혼합).
- `island_threshold=0.28`: Island 개수 **5~6개**로 요동, 마찬가지로 구성이 매번 다름.

### Insight
같은 threshold, 같은 데이터인데 입력 순서만 바꿔도 Island 개수와 구성이 달라진다 — 가설이 확인됨. Threshold를 더 세밀하게 찾는 것은 이 시점부터 의미가 크게 줄어든다.

### Decision
알고리즘 구조 자체(단일 Global Threshold + Greedy Online Nearest-Neighbor)의 한계를 `docs/algorithm_limitations.md` Finding #001로 문서화. 후속 방향(주기적 재클러스터링 / 밀도 기반 offline / Online 생성 + 배치 Merge·Split)은 아직 미결정 — 다음 세션에서 논의.

## Experiment #10: Order Sensitivity v2 (Pairwise F1 정량화)
날짜: 2026-07-16

### Hypothesis
Experiment #9는 Island 개수/구성만 봤다. 실제 정답 라벨 대비 Pairwise F1을 계산하면 순서 의존성의 크기를 정량적으로 보여줄 수 있고, "가장 유리한 순서(도메인별로 묶어서 넣기)"로도 안정적인 3분할이 안 되는지 확인할 수 있다.

### Data
동일 데이터셋(35개), island_threshold=0.24(baseline) 고정. 4가지 순서 비교:
- Backend→AI→Sports (그룹 순서)
- Sports→Backend→AI (그룹 순서, 반대)
- Shuffle(seed=42)
- Shuffle(seed=777)

Pairwise F1: 모든 쌍(595쌍)에 대해 "예측이 같은 Island인가"와 "실제로 같은 도메인인가"를 비교한 Precision/Recall/F1.

### Result
| Order | Islands | Precision | Recall | F1 |
|---|---|---|---|---|
| Backend→AI→Sports | 4 | 0.632 | 0.590 | 0.610 |
| Sports→Backend→AI | 4 | 0.685 | 0.636 | 0.660 |
| Shuffle(seed=42) | 3 | 0.489 | 0.549 | 0.517 |
| Shuffle(seed=777) | 3 | 0.653 | 0.733 | **0.691** |

### Insight
F1이 **0.517~0.691**로, 순서만 바꿔도 17%p 가까이 흔들린다. 더 중요한 발견: **가장 유리한 조건(도메인별로 묶어서 순서대로 넣기)으로도 정확히 3개로 안 갈렸다** — Backend→AI→Sports, Sports→Backend→AI 둘 다 4개 Island가 나왔고, AI가 매번 여러 Island에 걸쳐 흩어졌다. 이는 문제가 "입력 순서가 나빠서"가 아니라, 그리디 Nearest-Neighbor 알고리즘이 가장 이상적인 조건에서도 3-도메인 구조를 복원하지 못한다는 더 강한 증거다.

### Decision
`docs/algorithm_limitations.md` Finding #001에 이 정량적 근거(F1 스프레드, 그룹 순서로도 실패)를 추가한다.

## Experiment #11: Greedy 개선 시도 - Topic-First Assignment
날짜: 2026-07-17

### Hypothesis
Experiment #9/#10에서 확인한 순서 의존성이 "이 Greedy 구현(Island identity_vector 하나와만 비교)이 나빠서"라면, 판단 기준을 더 세밀한 단위(Topic)로 바꾸면 나아질 것이다. 반대로 순서 의존성이 Online Incremental Clustering이라는 접근 자체의 성질이라면, 비교 기준을 바꿔도 나아지지 않을 것이다.

### Data
`assign_scrap`(기존 Greedy) 옆에 `assign_scrap_topic_first`(신규 변형)를 추가했다 — Island identity_vector와 비교하는 대신, 세상에 존재하는 모든 Island의 모든 Topic과 먼저 비교해서 가장 유사한 Topic이 topic_threshold를 넘으면 그 Island로 바로 병합하고, 못 넘으면 기존처럼 Island identity_vector 기준으로 폴백한다.

같은 데이터셋(35개, Backend/AI/Sports), island_threshold=0.24 baseline 고정. 두 알고리즘을 그룹 순서 2가지(Backend→AI→Sports, Sports→Backend→AI) + 랜덤 셔플 30가지(seed 1~30), 총 32가지 순서로 나란히 실행하고 Pairwise F1과 Island 개수를 비교(`order_sensitivity_v3.py`).

### Result
| Algorithm | F1 mean | F1 std | F1 min | F1 max | Island 개수 최빈값 |
|---|---|---|---|---|---|
| Greedy (assign_scrap) | 0.595 | 0.085 | 0.459 | 0.829 | 3개 (32번 중 14번) |
| Topic-First | 0.647 | 0.084 | 0.515 | 0.825 | 2개 (32번 중 12번) |

F1 평균과 최악의 경우는 개선됐지만, **표준편차는 0.085→0.084로 사실상 그대로**다. Island 개수 최빈값도 3개(정답)에서 2개(언더분리)로 이동했다 — 그룹 순서 2가지 모두 Topic-First는 2개로 뭉쳤다(정답은 3개).

### Insight
F1보다 std가 더 중요한 지표다. World Engine의 Product Principle("세계는 안정적이어야 한다")은 "같은 데이터 → 같은 세계"를 요구하고, std가 바로 그 원칙을 측정한다. Island 판단 기준을 (identity_vector 하나 → 모든 Topic)으로 완전히 바꿨는데도 std가 그대로였다는 것은, 문제가 "무엇과 비교하는가"가 아니라 "언제, 어떤 순서로 결정을 내리는가"에 있다는 뜻이다. Topic-First는 병합 문턱을 사실상 낮춰서 오버분리 편향을 언더분리 편향으로 바꿨을 뿐, 근본 원인은 건드리지 못했다.

**순서 의존성은 특정 Greedy 구현의 결함이 아니라, Online Incremental Clustering(데이터를 하나씩 받아 그때그때 지역적으로 결정하는 방식) 자체의 성질일 가능성이 높다** — Finding #001의 가설을 한 단계 더 일반화하는 증거.

### Decision
`docs/algorithm_limitations.md` Finding #001에 Evidence 4로 추가하고, Root Cause/Implication을 이 일반화된 해석으로 갱신한다. 다음 실험(#12)은 같은 데이터셋·같은 embedding으로 offline 밀도 기반 클러스터링(HDBSCAN 등)을 돌려 Greedy와 비교한다 — 비교 대상이 없었던 지금까지와 달리, 이제부터는 실험 결과가 아키텍처(후보 A~D)를 고르게 한다.

## Experiment #12: Offline HDBSCAN vs Greedy
날짜: 2026-07-17

### Hypothesis
Experiment #11은 "순서 의존성은 특정 Greedy 구현이 아니라 Online Incremental Clustering 접근 자체의 성질"이라는 추정까지 나갔다. 이걸 직접 검증하려면 Online이 아닌 계열(offline, 전체 데이터를 한 번에 보고 결정)과 비교해야 한다. HDBSCAN을 같은 데이터셋에 돌리면 이론적으로 입력 순서와 무관해야 한다(F1 std = 0) — 가정이 아니라 실측으로 확인한다.

### Data
같은 데이터셋(35개, Backend/AI/Sports), 같은 embedding 재사용. `min_cluster_size`만 스윕했더니(2~15) 6 이상에서 전부 noise로 무너지는 현상 발견 — `min_samples`(밀도 조건)를 같이 낮추지 않으면 `min_cluster_size`를 올릴수록 조건이 같이 빡빡해지기 때문. `min_cluster_size`(2~15) x `min_samples`(1~3) 2차원 스윕으로 재탐색해서 baseline(`min_cluster_size=5, min_samples=1`, F1=0.721)을 찾았고, 이 설정으로 Experiment #11과 동일한 32가지 순서(그룹 2 + 랜덤 셔플 30)에 대해 Greedy와 나란히 실행(`experiment_hdbscan.py`).

### Result
| Algorithm | F1 mean | F1 std (order sensitivity) | Islands (mode/range) | Avg runtime |
|---|---|---|---|---|
| Greedy (assign_scrap) | 0.595 | 0.0840 | 3 (14/32) / 2-5 | 20.65ms |
| HDBSCAN (mcs=5, ms=1) | 0.721 | **0.0000** | 3 (32/32) / 3-3 | 4.60ms |

32가지 순서 전부에서 HDBSCAN은 항상 동일한 3개 Island, 동일한 F1을 냈다(std=0.0000). 다만 이 3개 Island의 실제 구성을 까보니: Sports(10개)는 깨끗이 분리됐지만, **Backend(15개 중복 포함)와 AI(9개)는 하나의 cluster로 뭉쳤고 AI 1개는 noise로 singleton 처리**됐다. F1 0.721이라는 숫자는 "3개 도메인을 정확히 갈라서"가 아니라 "Sports만 분리하고 Backend/AI는 항상 똑같이 뭉쳐서" 나온 값이다.

### Insight
두 가지를 분리해서 봐야 한다.
1. **Order Sensitivity는 완전히 해결됐다.** Greedy에서 Topic-First로 판단 기준을 바꿔도 그대로였던 std가, Online → Offline으로 접근 자체를 바꾸자 정확히 0이 됐다. 이는 Finding #001의 원인이 "Online Incremental Clustering이라는 접근 방식 자체"라는 것을 추정이 아니라 실측으로 확정한다.
2. **Domain Separation(Backend vs AI)은 알고리즘과 무관하게 실패했다.** Greedy(Experiment #8), Topic-First(Experiment #11), HDBSCAN(이번) 세 가지 서로 다른 계열의 알고리즘 전부에서 Backend와 AI가 뭉쳤다. 판단 로직이 완전히 다른 세 알고리즘이 같은 실패를 반복한다는 것은, 문제가 알고리즘이 아니라 embedding/데이터셋(Experiment #2에서 이미 나왔던 "Backend 내부 유사도 범위가 카테고리 간 평균과 겹친다"는 관찰과 연결) 쪽에 있다는 강한 신호다.

### Decision
Finding #001을 "해결(Resolved by Offline Clustering)"로 갱신하고, Backend/AI 문제는 원인이 다른 별도 이슈이므로 **Finding #002(Domain Separation, Open)**로 분리해서 `docs/algorithm_limitations.md`에 기록한다. 후보 A(현행 유지)는 폐기, 남은 결정은 후보 C(offline 완전 전환)와 D(Online 생성 + Night Batch) 중 하나 — `vision.md`/`principles.md`의 "세계는 안정적이어야 한다"에 비춰보면 C도 재계산 시점마다 섬이 움직일 수 있다는 새로운 불안정성을 만들 수 있어, 현재는 D 쪽에 무게가 실리지만 아직 프로토타입으로 검증하지 않았다. Finding #002는 알고리즘이 아니라 golden dataset의 Backend/AI 샘플을 사람이 다시 읽는 것부터 시작해야 하는 별도 조사로 남긴다.

## Experiment #13: Backend-AI Continuum Test
날짜: 2026-07-17

### Hypothesis
D(Hybrid) 프로토타입으로 바로 넘어가기 전에, Finding #002의 전제부터 의심해봐야 한다: "Backend와 AI가 계속 뭉치는 건 정말 오분류인가, 아니면 이 두 도메인이 embedding 공간에서 실제로 연속적(continuum)이기 때문인가?" golden dataset을 다시 확인해보니 경계 사례(Vector DB, Spring AI 등)가 하나도 없었다 — Backend는 Spring/JPA·Redis·Kafka, AI는 LLM·RAG뿐. 그런데도 계속 뭉친다면 순수 콘텐츠끼리도 이미 가깝다는 뜻이다.

### Data
같은 golden dataset(35개, 7개 Topic), 같은 embedding 재사용. Experiment #2와 같은 방법론(내부/교차 평균 Pairwise Cosine Similarity)을 이번엔 Topic 단위(7x7 매트릭스)로 재실행하고, Island 단위로도 요약(`experiment_domain_gap.py`).

### Result
| Pair | 평균 유사도 |
|---|---|
| AI 내부 | 0.3829 |
| Backend 내부 | 0.3559 |
| Sports 내부 | 0.3246 |
| AI ↔ Backend | 0.2779 |
| AI ↔ Sports | 0.2057 |
| Backend ↔ Sports | 0.1911 |

AI↔Backend 교차 유사도가 AI↔Sports·Backend↔Sports보다 뚜렷하게 높고, "내부-교차" 간격도 Backend-AI 쌍에서만 유독 좁다(Sports 대비 절반 수준). Topic 단위로는 더 뚜렷하다: **Redis-RAG(0.290) > Redis-Spring/JPA(0.286)** — Redis가 같은 Backend Topic보다 AI Topic에 더 가깝다.

### Insight
경계 사례 없이 순수 콘텐츠만으로도 이 결과가 나왔다는 게 핵심이다. 게다가 Experiment #2(카테고리 유사도), Threshold Sweep(#8), HDBSCAN(#12), 이번 Pairwise/Topic 분석(#13)까지 서로 완전히 다른 방법론 5개가 전부 같은 방향을 가리켰다 — 우연으로 보기 어렵다. Redis-RAG 결과는 실제로 말이 된다(Redis가 Vector Search/Semantic Cache로 자주 쓰임) — embedding이 우리가 붙인 "Backend"라는 이름표보다 기술 스택의 실제 사용 맥락을 학습하고 있는 것으로 보인다.

**중요한 절제**: 이 결과를 "golden dataset이 틀렸다"로 결론 내리지 않는다. Golden dataset은 진실이 아니라 평가 기준(하나의 관점)이다. 대신 평가를 두 층으로 분리한다 — Canonical Taxonomy(회귀 테스트용, 기존 라벨 유지)와 Semantic Evaluation(embedding이 실제로 만드는 구조를 관찰, 신설). 두 층은 경쟁이 아니라 보완 관계다.

### Decision
- `docs/algorithm_limitations.md` Finding #002를 "Domain Separation Failure"에서 **"Semantic Boundary Ambiguity"**로 개명 — "분리를 못 한다"가 아니라 "분리해야 한다는 전제 자체가 의심스럽다"로 프레이밍 변경. Evidence 3(이번 실험)와 재구성된 Root Cause 추가.
- `docs/evaluation_metrics.md`에 "Evaluation Layers: Canonical Taxonomy vs Semantic Evaluation" 절 신설.
- 향후 실험 백로그에 **Human Labeling Study**(여러 사람에게 같은 스택을 직접 분류시켜서 inter-rater agreement를 확인 — 사람들끼리도 갈리면 F1이 절대 지표가 될 수 없다는 게 실증됨) 추가.
- D(Hybrid) 프로토타입은 이 재구성 이후로 순서를 미룬다 — 다음 세션은 알고리즘이 아니라 Finding #002(경계 자체)를 계속 파거나 Human Labeling Study 설계로 이어간다.

## Experiment #15: Semantic Atlas — Observation: Programming Domains Form a Large Semantic Cluster
날짜: 2026-07-17

### Hypothesis
Finding #002는 지금까지 Backend-AI 두 도메인에서만 관찰됐다. 사람 실험(Human Labeling Study)은 참가자 모집이 어려워 먼저, 도메인 수를 8개로 늘려서 "Backend-AI 현상이 두 도메인만의 특수 사례인지, 아니면 더 넓게 반복되는 패턴인지"부터 관찰하기로 했다. 목표는 정답을 맞히는 것이 아니라 라벨 없이 embedding이 자연스럽게 만드는 구조를 그대로 관찰하는 것이다.

### Data
8개 도메인(AI/Backend/Cloud/Database/Security/Sports/Finance/Science) x 12개, 총 96개 신규 golden dataset(`golden_dataset/semantic_atlas/dataset.json`) 구성. 각 도메인은 4개 Topic x 3개로 구성하고, 15개는 의도적으로 경계 사례로 작성(Redis 벡터 검색, RAG+Redis, MCP로 백엔드 API 노출, VectorDB 전체, AI Security 전체, Crypto 인프라, Fintech/AI Trading 전체, Biology의 AlphaFold/유전체 ML). Sports는 순수 대조군으로 유지(경계 사례 없음). Island x Island 평균 pairwise 유사도 매트릭스 + heatmap(`experiments/plots/semantic_atlas_island_heatmap.png`), 그리고 HDBSCAN(min_cluster_size/min_samples 스윕, 관찰용 — F1 없이 자연 클러스터 개수만 확인)을 실행(`experiment_semantic_atlas.py`).

### Result
**확인된 사실 (Evidence):**
- Programming 계열 5개 도메인(AI/Backend/Cloud/Database/Security)이 HDBSCAN(mcs=3, ms=1)에서 하나의 클러스터로 뭉쳤다 — Cloud 12/12, Security 12/12, Backend 11/12, AI 10/12, Database 10/12가 같은 클러스터(전체 96개 중 50개)에 들어갔다.
- Island 단위 평균 유사도에서도 이 5개 도메인은 서로 0.26~0.30대로 고르게 묶이는 반면 Science(0.21~0.26)·Sports와는 뚜렷하게 갈렸다.
- 서로 다른 도메인(Science/Finance) 소속의 경계 사례 두 개(Biology의 AlphaFold/유전체 ML, Finance의 Fintech/AI Trading)가 하나의 작은 클러스터로 묶였다 — Redis↔RAG 패턴이 도메인을 넘어 재현됨.
- Sports 6개 + Finance 5개가 같은 클러스터에 들어갔다.

**Hypothesis (원인 미확정):** Sports+Finance 병합 원인은 register(뉴스 기사체) / vocabulary overlap / embedding model bias 중 하나 또는 복합일 가능성이 있다. 이 데이터셋의 Sports/Finance 텍스트가 둘 다 뉴스 리포트 톤이라는 게 눈에 띄지만, 이건 관찰된 상관관계이지 검증된 원인이 아니다.

### Insight
Backend-AI 현상은 두 도메인만의 특수 사례가 아니라 **Programming 생태계 전체(AI/Backend/Cloud/Database/Security)에서 반복되는 패턴**이었다. 게다가 Biology↔Fintech/AI Trading처럼 완전히 다른 두 "상위 도메인"에 속한 경계 사례가 서로를 찾아간 것은, "AI가 응용된 콘텐츠"라는 공통점이 원래 도메인 소속보다 더 강한 인력으로 작용할 수 있다는 뜻이다. 이는 Finding #002를 뒷받침하는 여러 독립 관찰 중 가장 넓은 범위의 증거다.

반면 Sports+Finance 병합은 원인이 아직 불확실하다는 점을 분명히 해야 한다 — 결론(Conclusion)이 아니라 발견(Finding)만 기록하고, 원인 규명은 별도 실험(Experiment #16)으로 미룬다. 문체 혼입이 실제로 원인이더라도 이건 "나쁜 결과"가 아니다 — 실제 사용자 스크랩도 뉴스/블로그/문서/README/논문이 섞여 있으므로, Controlled Corpus(문체 통제)와 Natural Corpus(문체 혼합, 실사용 환경에 가까움) 평가를 구분해야 한다는 인사이트로 이어진다.

### Decision
- `docs/algorithm_limitations.md` Finding #002에 Evidence 4로 추가(제목은 단정적 결론이 아니라 "Observation"으로 표현), Root Cause에 "여러 도메인에서 반복되는 패턴"이라는 더 강한 근거로 반영.
- `docs/evaluation_metrics.md`에 "Corpus Design: Controlled Corpus vs Natural Corpus" 절 신설.
- 백로그에 **Experiment #16(Register Control)** 추가: 같은 내용을 뉴스/블로그/위키/요약문 register로 다시 써서 Sports+Finance 클러스터가 유지되는지 확인 — register가 원인인지 실제 의미적 근접성인지 가려낸다. 아직 실행하지 않음.
- Experiment #14(Human Semantic Clustering Study)는 백로그에 그대로 유지 — 참가자 모집 난이도 때문에 Experiment #15/#16(알고리즘·데이터만으로 가능한 실험)을 먼저 진행하기로 순서를 조정.

## Experiment #16: Register Control
날짜: 2026-07-17

### Hypothesis
Experiment #15는 Sports+Finance 병합의 원인을 Hypothesis(register 때문일 수도, 실제 의미적 근접성일 수도)로만 남겼다. 같은 내용을 서로 다른 register로 다시 써도 병합이 유지되는지 확인하면 원인을 좁힐 수 있다 — 뉴스 기사체에서만 붙고 다른 register에서는 떨어지면 register가 원인, 모든 register에서 계속 붙으면 register만으로는 설명되지 않는다.

### Data
Sports 12개 + Finance 12개, 총 24개 "사실(fact)"을 뉴스 기사체/블로그체/위키 서술체/요약문체 4가지 register로 각각 다시 써서 96개(24×4) 코퍼스 구성(`golden_dataset/register_control/dataset.json`). register별로 Sports 내부/Finance 내부/Sports↔Finance 교차 평균 pairwise 유사도와 HDBSCAN(min_cluster_size=3, min_samples=1) 결과를 비교(`experiment_register_control.py`).

### Result
| Register | Sports 내부 | Finance 내부 | Sports↔Finance | Gap | HDBSCAN |
|---|---|---|---|---|---|
| news | 0.299 | 0.270 | 0.242 | 0.028 | 병합됨 |
| blog | 0.325 | 0.317 | 0.257 | 0.061 | 병합됨 |
| wiki | 0.260 | 0.244 | 0.212 | 0.032 | 병합됨 |
| summary | 0.352 | 0.316 | 0.296 | 0.020 | 병합됨 |

4개 register 전부에서 병합됨. Gap이 가장 작은 register는 news(0.028)가 아니라 summary(0.020)였고, 감정·시제가 없는 wiki에서도 여전히 병합됐다. Gap 편차는 register 전체에서 0.020~0.061로 크지 않다.

### Insight
"Sports-Finance clustering is primarily caused by writing style(register)"라는 가설이 Experiment #16으로 기각(Rejected)됐다 — register를 뉴스→블로그→위키→요약문으로 완전히 바꿔도 4/4 병합이 유지됐다. **단, 이 실험이 증명한 범위는 "register만으로는 설명되지 않는다"까지다.** "그래서 실제로 의미적으로 가깝다"까지 결론 내리는 건 과도하다 — 경쟁/순위/예측/통계/시장분석/시즌성 같은 구체적인 공유 구조가 원인일 가능성은 여전히 검증되지 않은 Hypothesis로 남는다.

이번 실험은 V0에서 가장 깔끔한 가설 반증(falsification) 사례 중 하나로 평가한다 — Threshold를 찾는 데서 시작해 EMA Drift → Identity/Growth 분리 → Greedy 한계 → Offline 비교 → Semantic Boundary Ambiguity로 원인을 계속 좁혀온 흐름의 연장선.

### Decision
- `docs/algorithm_limitations.md` Finding #002에 **Evidence 5**(Register-independent Sports-Finance Clustering)와 **Rejected Hypothesis #1**(Register Contamination, Status: Rejected) 섹션 추가. Root Cause/Status를 "문체 축은 닫혔고, 왜 의미적으로 가까운지가 남은 질문"으로 갱신.
- `docs/evaluation_metrics.md`의 Experiment #16 백로그 항목을 완료로 갱신.
- 후속 질문("Sports-Finance가 정확히 무엇을 공유하는가")은 아직 구체적인 실험으로 설계하지 않음 — 백로그에 미설계 상태로 남김.

## Experiment #17: Semantic Factor Probe
날짜: 2026-07-17

### Hypothesis
Experiment #16으로 "문체 축"은 닫혔지만 "왜 Sports-Finance가 의미적으로 가까운가"는 여전히 미검증이다. 경쟁/순위/예측/통계/시장분석/시즌성 6개 후보를 도메인 중립적인 문장(probe)으로 표현해서, `golden_dataset/semantic_atlas/dataset.json`의 8개 도메인 centroid와 비교하면 어느 후보가 Sports+Finance에 특이적으로 가까운지 확인할 수 있다.

### Data
6개 후보 각각을 스포츠/금융 어휘 없이 순수한 구조로 서술한 probe 문장 1개씩(N=1). 8개 도메인 centroid(semantic_atlas 96개에서 island별 평균 벡터)와 cosine similarity 비교, Specificity Gap = min(Sports,Finance 유사도) - max(다른 6개 도메인 유사도)로 계산(`experiment_semantic_factor_probe.py`).

### Result
| Probe | Specificity Gap |
|---|---|
| 순위(Rank) | +0.031 |
| 경쟁(Competition) | -0.006 |
| 통계(Statistics) | -0.020 |
| 예측(Prediction) | -0.034 |
| 시장분석(Market Analysis) | -0.097 |
| 시즌성(Time-series) | -0.125 |

6개 중 "순위(Rank)"만 양수 Gap을 보였다. 나머지는 오히려 다른 도메인(주로 Database, Science)에 더 가까웠다 — 예: "시장분석" probe는 Science(0.486)·AI(0.461)에 더 가까움.

### Insight
"순위(Rank)"가 유일하게 Sports+Finance 특이적인 신호를 보였지만 Gap이 +0.031로 크지 않고, probe가 단 하나(N=1)라 재현성이 없다.

### Decision
Finding #002 Evidence로 승격하지 않는다 — Candidate Hypothesis(Needs Replication)로만 표시. 다음 실험(#18)에서 Rank corpus를 N=20으로 확장해 재현성을 검증하기로 함.

## Experiment #18: Rank Corpus Replication + Rank Family Comparison
날짜: 2026-07-17

### Hypothesis
Experiment #17의 "Rank" 신호(N=1, +0.031)가 우연이 아니라면, 같은 개념을 여러 phrasing(N=20)으로 반복해도 평균 Gap이 유의하게 양수로 유지될 것이다. 추가로 Rank와 연관된 하위 개념군(Score/League/Standings/Leaderboard/Top N/Rating/Ranking/Index)도 같이 비교하면 "Rank" 자체보다 더 강한 개념이 있는지 탐색할 수 있다.

### Data
Rank 개념 20가지 phrasing + Rank Family 8개 개념 x 5개씩(총 60개, `golden_dataset/rank_family/dataset.json`). 각 probe의 Specificity Gap을 계산하고 Rank corpus는 평균/표준편차/95% CI, Rank Family는 개념별 평균 Gap으로 비교(`experiment_rank_family.py`).

### Result
**Rank Corpus 재현성 (N=20):**
- Mean Specificity Gap: -0.0076
- 95% CI: [-0.0360, +0.0207] — **0을 포함**
- 양수 비율: 11/20

**Rank Family 비교 (Mean Gap 순):**
| Concept | N | Mean Gap | 양수 비율 |
|---|---|---|---|
| Rating | 5 | +0.0768 | 4/5 |
| Leaderboard | 5 | +0.0082 | 4/5 |
| Score | 5 | -0.0006 | 3/5 |
| Standings | 5 | -0.0054 | 2/5 |
| League | 5 | -0.0076 | 2/5 |
| Rank | 20 | -0.0076 | 11/20 |
| TopN | 5 | -0.0180 | 2/5 |
| Ranking | 5 | -0.0580 | 0/5 |
| Index | 5 | -0.0681 | 1/5 |

### Insight
**"Rank" 가설은 재현에 실패했다.** N=1의 +0.031은 N=20에서 평균 -0.0076, 95% CI가 0을 포함하는 수준으로 사라졌다 — Threshold sweep 범위가 좁아서 최적점을 놓쳤던 Experiment #6→#7의 교훈과 같은 패턴(단일/소규모 관측을 과신하지 않기)이 재확인됐다.

반면 Rank Family를 넓게 비교하던 중 **"Rating"(평점/레이팅)이 8개 중 가장 강한 신호(+0.0768, 4/5 양수)**로 나타났다. "Rank"(정적 순위표)와 "Ranking"(순위를 매기는 행위, -0.058/0/5)이 반대 방향으로 갈린 것도 흥미롭다 — 같은 어원의 개념이라도 명사형/동사형에 따라 embedding이 다르게 반응할 수 있다는 뜻이다.

**단, Rating도 N=5뿐이다.** Rank가 방금 겪은 함정(N=1→N=20 재현 실패)을 그대로 반복할 위험이 있으므로, Rating을 Evidence로 승격하기 전에 반드시 더 큰 표본(N≈20~30)으로 재현성을 확인해야 한다.

### Decision
- `docs/algorithm_limitations.md` Finding #002에 **"Candidate Hypotheses (Unvalidated)"** 절 신설: Rank는 Status: Rejected(재현 실패)로, Rating은 Status: UNVALIDATED(N=5, 재현 필요)로 명시. 둘 다 Evidence로는 올리지 않음.
- 다음 실험(#19, 미실행): Rating corpus를 N≈20~30으로 확장해 재현성 검증 — 재현되면 Evidence로 승격, 재현 안 되면 Rating도 기각하고 Rank Family 밖의 새로운 의미 축을 탐색.

## Experiment #19: Rating Corpus Replication
날짜: 2026-07-17

### Hypothesis
Experiment #18에서 Rating이 N=5로 가장 강한 신호(+0.0768, 4/5 양수)를 보였다. Rank가 N=1→N=20에서 겪은 재현 실패를 반복하는지, 아니면 이번엔 실제로 재현되는지 N=25로 확인한다.

### Data
Rating 개념을 25가지 domain-neutral phrasing으로 작성(`golden_dataset/rating_replication/dataset.json`). 각 probe의 Specificity Gap을 semantic_atlas 8개 도메인 centroid 기준으로 계산하고 mean/std/95% CI 산출(`experiment_rating_replication.py`).

### Result
| Concept | N | Mean Gap | 95% CI | 판정 |
|---|---|---|---|---|
| Rank (Experiment #18) | 20 | -0.0076 | [-0.0360, +0.0207] | 재현 실패 |
| Rating (Experiment #19) | 25 | +0.0063 | [-0.0105, +0.0231] | 재현 실패 |

N=5의 +0.0768이 N=25에서 +0.0063으로 거의 0에 수렴했다. 양수 비율은 17/25로 절반은 넘지만, 95% CI가 0을 포함해 통계적으로 유의하지 않다.

### Insight
**Rank에 이어 Rating도 재현에 실패했다.** 두 개의 독립적인 "Rank Family" 후보가 연달아 같은 패턴(소규모 표본 신호 → 대규모 표본에서 소멸)을 보이면서, "Sports-Finance를 잇는 단일 latent concept이 존재할 것"이라는 실험 설계 자체를 의심할 시점이 됐다. OpenAI 임베딩은 1536차원이라 의미가 보통 하나의 축이 아니라 수백~수천 차원에 나뉘어 표현되므로, Sports-Finance 근접성이 여러 미세한 요소(순위/추세/확률/기록/성장·하락 등)가 합쳐진 결과라면 단일 개념 probe로는 애초에 유의미한 신호가 잡히지 않을 수 있다.

이와 별개로, 지금까지의 실험(Experiment #2/#8/#12/#13/#15/#16)이 반복적으로 보여준 건 "Programming 5개 도메인이 하나로 뭉친다"와 "Sports-Finance도 반복적으로 가깝다"는 관찰 자체는 매우 견고하다는 것이다. "왜 붙는가"를 계속 파는 것과 별개로, "이 현상을 제품에서 버그로 볼지 발견으로 볼지"는 아직 논의하지 않은 질문으로 남아 있다.

### Decision
- `docs/algorithm_limitations.md` Finding #002의 Rating 항목을 **Status: Rejected**로 갱신.
- **Concept Probing(단일 개념 probe로 원인을 찾는 방법론)을 잠정 중단**하고, 대안으로 **Lexical Ablation**(실제 문장에서 단어를 하나씩 제거하며 유사도 변화를 관찰하는 방법)을 백로그에 추가(아직 미설계).
- **Product Question 신설**: "Finding #002는 고쳐야 할 결함인가, World Engine 철학(카테고리 재현이 아니라 관심사 연결 발견)이 실제로 작동하고 있다는 증거인가?" — 다음 세션에서 연구가 아니라 제품 관점으로 논의하기로 함. 원인 탐색(Lexical Ablation, Human Labeling Study)은 이 논의 이후에도 필요하면 이어가는 것으로 우선순위를 낮춤.

## Product Decision #002: Programming 생태계를 하나의 상위 의미 공간으로 취급 허용
날짜: 2026-07-17

Finding #002의 Product Question(버그인가 발견인가)에 대한 결론. 결과는 둘로 나뉜다 — Programming과 Sports-Finance는 증거의 "종류"가 다르기 때문이다(아래 Research Principle #001 참고).

**Decision**: World Engine은 Programming 생태계(AI/Backend/Cloud/Database/Security)를 하나의 상위 의미 공간(Island)으로 취급하는 것을 허용한다. "AI와 Backend는 하나다"가 아니라 "AI와 Backend를 억지로 분리하려 하지 않는다"는 뜻이다.

**근거**:
- Experiment #2(카테고리 유사도)/#8(Threshold Sweep)/#12(HDBSCAN)/#13(Topic 분석)/#15(8도메인 Atlas) — 서로 다른 방법론 5개가 모두 같은 방향을 가리켰고, 원인도 인과적으로 설명 가능하다(Redis→RAG 벡터 검색, MCP→백엔드 API 노출 등).
- "정확히 N개 도메인으로 갈려야 한다"는 canonical taxonomy 전제 자체가 V1 설계에서는 틀렸을 수 있다 — 이걸 억지로 갈라놓으려면 사람이 만든 규칙(온톨로지, 수동 override)이 필요한데, 이는 "AI는 이해, 알고리즘은 결정" 원칙과 충돌한다.
- **Growth Rule과의 연결**: `growth_rules.md`의 City 형성 트리거("크기가 아니라 밀도 — 다양성×연결성")가 Programming Island 내부에서 실제로 관찰되는 Topic 다양성(Spring/Redis/Kafka/RAG/LLM/MCP…)과 정확히 일치한다. Finding #002는 이 Growth Rule을 실험적으로 뒷받침하는 첫 사례다.

**한계**: 이 결정은 절대 진리가 아니라 현재 실험 범위(8개 도메인)에서 반복 관찰된 현상이다. Design/DevOps/Math/GameDev/Embedded/CAD/Robotics 같은 도메인이 추가되면 Programming Island가 다시 둘 이상으로 갈라질 수 있다 — 그건 실패가 아니라 World Engine이 "정해진 섬을 유지하는 시스템"이 아니라 "데이터가 보여주는 섬을 발견하는 시스템"이라는 증거다.

## Watch Metric #001: Sports-Finance 근접성
날짜: 2026-07-17

**Decision**: 현재는 제품 설계에 반영하지 않는다. Programming과 달리 결과는 반복되지만(Experiment #2/#8/#12/#13/#15/#16) 원인은 설명되지 않는다(Experiment #17~19, Concept Probing 2회 실패, 95% CI가 매번 0을 포함) — "결과 반복 + 설명 가능"과 "결과 반복 + 설명 불가"는 제품이 신뢰할 근거로 다르게 취급해야 한다.

**다음 액션**: V1 출시 후 실제 사용자 데이터에서도 동일 패턴이 반복되는지 지속 관찰한다. synthetic golden dataset의 결과만으로 제품 동작을 결정하지 않는다.

## Research Principle #001: 실험 결과를 제품 결정으로 승격시키는 기준
날짜: 2026-07-17

V0 전체를 관통하는 원칙으로 명문화한다: **World Engine은 사람이 미리 정의한 카테고리를 재현하는 것이 아니라, 반복적으로 관찰되는 의미 구조를 발견하고 이를 제품에 반영한다.**

단, "반복 관찰"만으로는 충분하지 않다 — Product Decision #002(Programming)와 Watch Metric #001(Sports-Finance)의 차이가 그 기준을 보여준다:
- 여러 독립적인 방법론에서 같은 결과가 나오고 그 원인까지 인과적으로 설명 가능할 때 → Product Decision으로 승격.
- 같은 결과가 반복되지만 원인이 설명되지 않을 때(재현 가능한 probe로도 원인을 못 찾음) → Watch Metric으로 보류, synthetic 데이터만으로 제품에 반영하지 않음.

이 기준 자체가 V0의 실험들(Threshold 튜닝 → EMA Drift → Greedy 한계 → Offline 검증 → Semantic Boundary Ambiguity → Register/Rank/Rating 가설 반증)이 축적되며 자연스럽게 도출된 결과다.

## Experiment #20: Virtual User Growth Simulation (Longitudinal)
날짜: 2026-07-18

### Hypothesis
지금까지의 모든 golden dataset은 "정적 스냅샷"이었다 — 미리 정해둔 항목을 한 번에(또는 순서만 바꿔서) 넣고 결과를 봤다. 실제 사용자는 시간에 걸쳐 관심사를 점진적으로 쌓는다. Product Decision #002가 예측한 "Programming Mega Island"가 한 명의 사용자가 자연스럽게 성장하는 과정에서도 나타나는지, 아니면 Online-only Greedy의 순서 의존성(Finding #001)이 장기 성장에서 다른 문제(같은 관심사의 분열)로 나타나는지 확인한다.

### Data
Virtual User "backend_developer"(`experiments/virtual_users/backend_developer.json`, 71개) — 3년차 백엔드 개발자가 Spring/JPA로 시작해 Redis/Kafka/Docker를 거쳐 AWS/Kubernetes/MCP/RAG/LLM까지 관심사를 넓혀가는 30일 궤적(Day 1: 5개, Day 7: 누적 25개, Day 30: 누적 71개, 9개 실제 주제). Day 순서대로 순수 Online Greedy(`assign_scrap`, Hybrid Architecture의 Night Batch는 아직 미구현)로 처리하며 각 체크포인트에서 Island 구성과 AI 생성 Label을 스냅샷(`simulate_growth.py`).

### Result
| Day | Island 수 | 비고 |
|---|---|---|
| 1 | 1 | Spring/JPA만, 정상 |
| 7 | 2 | Redis/Kafka/Docker가 두 Island에 중복 등장 시작 |
| 30 | 5 | Island #0(8개 실제 주제)과 #1(7개 실제 주제)이 AWS/Docker/Kafka/Kubernetes/RAG/Redis를 동시에 포함 — 사실상 같은 성격의 섬이 둘로 갈라짐. LLM/RAG만 담긴 파편 Island도 3개 추가 발생 |

Day 30 기준 총 9개의 실제 주제(Spring/JPA/Redis/Kafka/Docker/AWS/Kubernetes/MCP/RAG/LLM) 중 **8개(89%)가 2개 이상의 Island에 중복 등장**했다 — 유일하게 한 Island에만 머문 건 Spring/JPA뿐이다.

### 확인된 사실 (Evidence)
- 동일한 사용자의 자연스러운 30일 성장 시나리오에서도 같은 Topic(Redis, Kafka, Docker 등)이 여러 Island에 중복 등장했다(Day 30 기준 9개 중 8개, 89%).
- Product Decision #002에서 기대한 "Programming Mega Island"는 Online-only Greedy에서는 형성되지 않았다 — 대신 서로 겹치는 5개의 파편 Island가 생겼다.
- Finding #001에서 관찰했던 순서 의존성이 synthetic golden dataset뿐 아니라 시간축이 있는 Virtual User Dataset에서도 재현됐다.
- Online-only 방식은 시간이 지날수록(Day 1→7→30) Island 수가 늘고 동일 주제가 여러 곳에 흩어지는 **분열(fragmentation)** 경향을 보였다.

### 아직 가설인 부분 (Hypothesis)
이 결과는 Hybrid Architecture(Step 5.5)에서 제안한 Night Batch가 해결 대상으로 삼는 fragmentation 패턴과 정확히 부합한다. **하지만 Night Batch를 아직 구현해서 돌려본 것은 아니므로, "Night Batch가 이 문제를 해결한다"는 결론은 내리지 않는다.** 실제 해결 여부는 Hybrid 구현 후 같은 Virtual User Dataset으로 별도 검증이 필요하다.

### Insight
이번 실험은 Finding #001(순서에 따라 Backend/AI가 갈라진다)의 단순 재현보다 더 큰 의미가 있다 — **"같은 사용자의 하나의 관심사가 시간이 지나며 여러 Island로 분열된다"**를 처음 관찰했다. 이건 순수 알고리즘 문제가 아니라 제품 관점에서 훨씬 치명적이다: 사용자가 Redis/Kafka/Docker/Kubernetes를 꾸준히 모았는데 "왜 내 백엔드 관심사가 세 군데로 찢어져 있지?"라고 느낄 수 있는 경험이 실제로 재현 가능하다는 뜻이다. 이를 **Fragmentation of User Interest**로 명명한다.

### Decision
- `experiments/virtual_users/backend_developer.json`(Virtual User Dataset 1호) + `simulate_growth.py`(Growth Simulator)를 PR로 기록한다.
- 결론은 "Hybrid가 필요하다"가 아니라 **"Hybrid(Night Batch)가 해결하려는 문제가 실제로 존재함을 확인했다"**까지로 제한한다.
- 다음 실험(#21, 미실행): Night Batch를 실제로 구현한 뒤 같은 Virtual User Dataset으로 재실행 — Island 수, Topic 중복률(이번 실험에서 쓴 지표를 그대로 재사용), Label 중복률 등을 Before/After로 비교해 Hybrid의 효과를 정량적으로 검증한다.

## Experiment #21: Night Batch Before/After Comparison
날짜: 2026-07-18

### Hypothesis
Experiment #20에서 확인한 Fragmentation of User Interest(Online-only에서 실제 주제의 89%가 여러 Island에 중복)를 Night Batch v0(Merge-only, `hybrid_architecture.md` 5단계 중 1/2/5만 구현)가 줄이는지 검증한다.

### Data
같은 Virtual User Dataset(`backend_developer.json`, 71개)을 두 갈래로 처리(`experiment_night_batch.py`):
- Online-only: Experiment #20과 동일, `assign_scrap`만 사용.
- Online + Night Batch: 매 day 체크포인트(1, 7, 30)가 끝날 때마다 `night_batch()`(offline HDBSCAN을 참고 자료로 쓰고, 다수결 라벨이 같고 purity≥0.5인 Island 쌍만 merge)를 실행.

### Result
| | Island 수 | Topic 중복률 |
|---|---|---|
| Online-only | 5 | 88.9% (9개 중 8개) |
| Online + Night Batch | **1** | **0.0%** |

Night Batch 적용 후 9개 실제 주제(Spring/JPA/Redis/Kafka/Docker/AWS/Kubernetes/MCP/RAG/LLM) 전부가 중복 없이 하나의 Island에 담겼다.

### 증명된 것 (Evidence)
동일한 Virtual User Dataset에서 Online-only는 관심사가 여러 Island로 분열(fragmentation)됐지만, Night Batch v0(Merge-only)를 적용하자 하나의 Programming Mega Island로 통합되며 Topic 중복이 제거됐다 — Island 수 5→1, Topic 중복률 88.9%→0%라는 정량적 개선.

이는 Product Decision #002("Programming은 하나의 상위 의미 공간")가 정적 golden dataset뿐 아니라 **시간이 흐르며 생성된 동적 성장 시나리오에서도 재현된다**는 뜻이다 — Product Decision이 정적 스냅샷의 우연이 아니라는 근거가 하나 더 늘었다.

### 아직 증명되지 않은 것 (Scope, 반드시 같이 기록)
**"Night Batch가 Finding #001을 해결했다"라고 쓰지 않는다.** 이번 결과는 다음 범위로 제한된다:
- 페르소나 1명(Backend 개발자), 데이터셋 1개로만 검증했다 — AI Researcher, Sports 팬, 투자자, Mixed User, 여러 사용자 동시 등은 아직 안 봤다.
- Split·Boundary Topic 이동은 구현하지 않았다 — "정말 갈라져야 하는데 하나로 잘못 뭉친" 경우(예: Sports+Finance가 실제로는 별개여야 하는 상황)를 이 버전은 고치지 못한다. 오히려 지나치게 잘 합쳐버릴 위험은 아직 검증 안 됨.
- `purity_threshold=0.5` 기본값이 이 데이터셋에 우연히 잘 맞았을 가능성 — 파라미터 민감도는 확인하지 않았다.

정확한 표현: **"Night Batch v0가 이 Virtual Backend User 데이터셋에서 fragmentation을 해소했다"** — 일반화는 아직 아니다.

### Insight
숫자 자체보다 지표 선택이 더 중요한 결과다. Island 개수는 알고리즘 설정에 따라 얼마든지 달라질 수 있지만, **Topic Duplication Rate(같은 실제 주제가 여러 Island에 존재하는 비율)는 사용자가 직접 체감하는 UX 문제를 정량화**한다 — "내 Redis 관심사가 왜 세 군데에 흩어져 있지?"를 숫자로 잡아낸다. 앞으로 Hybrid Architecture를 평가할 때 Island Count나 Pairwise F1보다 이 지표를 핵심 제품 지표로 우선한다(`docs/evaluation_metrics.md`에 정식 정의 추가).

### Decision
- `world.py`에 `night_batch()`(Merge-only) 추가, `experiment_night_batch.py`로 Before/After 비교.
- `docs/evaluation_metrics.md`에 **Topic Duplication Rate**를 정식 지표로 추가.
- `docs/hybrid_architecture.md`에 **Hybrid Validation Checklist** 신설 — Backend User 외 페르소나(AI Researcher, Mixed Engineering User, Sports User, Investor)와 Multi-user, Sports+Finance Boundary Case 등으로 검증 범위를 넓히는 로드맵을 백로그로 남긴다.
- PR 결론은 "Night Batch가 Finding #001을 해결했다"가 아니라 **"Night Batch v0가 이 realistic longitudinal 시나리오에서 fragmentation을 해소했다 — 일반화는 향후 과제"**로 제한한다.

## Experiment #22: Offline HDBSCAN Structure Inspection (AI Researcher)
날짜: 2026-07-18

### Hypothesis
Hybrid Validation Checklist의 다음 항목으로 AI Researcher User(Transformer/RLHF/Diffusion/VectorDB/Fine-tuning/Evaluation/Multimodal/Agent/Prompt Engineering, 71개, Backend User와 동일한 Day 1/7/30 구조)를 Experiment #21과 같은 방식(Online-only vs Online+Night Batch)으로 먼저 돌려봤더니, Island 7→6, Topic 중복률 77.8%→77.8%(변화 없음)로 Backend User와 완전히 다른 결과가 나왔다. 원인을 추측하지 않고 직접 확인한다 — 파라미터(purity_threshold 등)는 건드리지 않고 HDBSCAN 구조와 Online Island의 purity 분포만 관찰한다.

### Data
같은 AI Researcher 데이터셋(`ai_researcher.json`, 71개)의 전체 스크랩에 night_batch()와 동일한 기본 파라미터(min_cluster_size=3, min_samples=1)로 offline HDBSCAN을 돌려 클러스터 구성을 관찰하고, Online-only로 만들어진 각 Island가 어떤 클러스터에 얼마나 순수하게(purity) 속하는지 계산(`experiment_hdbscan_inspection.py`).

### Result
- HDBSCAN 결과: **10개 클러스터 + Noise 20개(28%)**. 각 클러스터가 원래 실제 Topic과 거의 1:1로 대응(`#0=Transformer(6)`, `#1=VectorDB(3)`, `#4=Diffusion(5)`, `#6=RLHF(5)` 등 대부분 순수 클러스터) — Backend User 때 9개 Topic을 **하나의** 클러스터로 몰아준 것과 정반대.
- Online 단계에서 9개 Topic이 전부 섞인 거대 Island(#0)의 purity는 **0.20** — 어떤 단일 HDBSCAN 클러스터와도 강하게 안 맞음.

### Insight
Night Batch가 AI Researcher에서 아무 것도 안 한 건 실패가 아니라 **Minimum Change Principle이 의도대로 애매한 후보(purity 0.20)를 걸러낸 것**이다. Backend User와 AI Researcher의 차이는 데이터 품질이 아니라 **두 페르소나의 관심사 구조 자체가 다르다는 증거**다 — Backend User의 9개 Topic은 실제로 하나의 조밀한 의미 공간을 이루지만, AI Researcher의 9개 Topic은 Foundation Model(Transformer/RLHF/Diffusion)과 Application AI(Agent/Prompt Engineering/Evaluation) 등 여러 자연스러운 하위 공간으로 이미 갈라져 있다.

더 근본적으로: **Merge-only는 "offline 클러스터가 Online Island들의 합집합"이라고 암묵적으로 가정하는데, Online 단계에서 이미 여러 의미 공간이 하나의 Island로 뭉쳐버렸다면(Finding #001의 과병합) 필요한 연산은 Merge가 아니라 Split**이다. 이번 실험으로 "Night Batch가 부족한가?"라는 질문이 "Merge가 아니라 Split이 필요한 상황을 처음으로 관측했다"로 바뀌었다.

### Decision
- `docs/algorithm_limitations.md`에 **Finding #003**(Merge-only Hybrid는 Online 단계에서 이미 과병합된 Island를 고치지 못한다, Status: Resolved — Need Split) 신설.
- Product Decision #002의 "Programming = 항상 하나의 Mega Island" 표현을 "Programming은 하나의 상위 의미 공간이며, 실제 Island 구성은 사용자의 관심 밀도에 따라 하나 또는 여러 개의 하위 의미 공간으로 나타날 수 있다"로 완화.
- `docs/hybrid_architecture.md`의 Hybrid Validation Checklist에서 AI Researcher를 체크하고, **우선순위를 재조정** — Mixed Engineering User/Sports User/Investor/Multi-user/Sports+Finance Boundary Case보다 **Split Prototype(Step 5.5 v1.1) 설계가 먼저** 와야 한다는 결정. Split 없이는 나머지 검증도 AI Researcher와 같은 "Merge만으로 설명 안 되는 결과"에 부딪힐 가능성이 크기 때문.

## Experiment #23: Split Prototype - Merge + Split Full Cycle
날짜: 2026-07-18

### Hypothesis
Finding #003(Merge-only는 Online 단계에서 과병합된 Island를 고치지 못한다)에 대한 대응으로 `find_split_candidates`/`apply_split`(Split Trigger + Split Plan, Minimum Change Principle 적용)을 구현했다. AI Researcher에 Merge 이후 Split을 추가로 적용하면 Topic Duplication Rate가 더 내려갈 것으로 예상했다.

### Data
AI Researcher/Backend User 데이터셋에 Online-only → Night Batch(Merge) → Split(`experiment_split.py`)를 순서대로 적용하고 각 단계의 Island 수/Topic 중복률을 비교.

### Result
초기 구현에서 **버그 발견**: Split 적용 후 스크랩 총량이 71개→67개로 4개가 사라짐. 원인은 `find_split_candidates`가 스크랩이 전부 HDBSCAN Noise이거나 그룹 크기가 min_group_size 미만인 Topic을 그냥 버리고 있었기 때문 — 확신 없는 Topic은 survivor 그룹에 합쳐서 반환하도록 수정해 해결(71→71→71로 유실 없음 확인).

버그 수정 후 재실행 결과:
| Stage | Island 수 | Topic 중복률 |
|---|---|---|
| Online-only | 7 | 77.8% |
| + Night Batch (Merge) | 6 | 77.8% |
| + Split | 8 | **88.9%(악화)** |

Split이 Island #0에서 Multimodal+Transformer(#6), Diffusion+Multimodal(#7)을 떼어냈는데, 이 조각들이 **이미 존재하던 다른 Island(#1, #3)와 겹치는 실제 주제를 다시 만들어냈다** — Multimodal이 #0/#1/#3/#6/#7 다섯 곳에 흩어짐.

Split 직후 같은 Island 집합에 `night_batch`(Merge)를 한 번 더 돌려서(`run_night_batch`) 방금 떨어진 조각을 기존 Island와 다시 합치려 시도했지만 **효과 없음**(여전히 8개, 8/9 중복) — 기존의 작은 Island들(#1/#2/#3) 자체가 이미 여러 실제 주제가 섞인 애매한 다수결 라벨을 갖고 있어서, Island 단위 비교로는 새로 떨어진 조각과 서로를 못 찾는다.

### Insight
Split은 분리 대상 Island 하나만 보고 판단해서, 그 조각이 세계에 이미 존재하는 다른 Island와 겹치는지는 확인하지 않는다 — **local 최적화가 global 중복을 늘렸다.** Island 단위 재-Merge로 이를 고치려는 시도도 실패했는데, Island 자체가 이미 여러 실제 주제의 혼합체라서 Island 단위 "다수결 라벨" 비교가 너무 뭉툭하기 때문이다. 이는 Merge/Split을 Island 단위 개별 연산으로 반복 적용하는 접근 자체의 한계를 시사한다 — Boundary Topic Move(Topic 단위 이동)를 추가해도 "Move → 관계 변화 → 재-Merge → 재-Split → 재-Move"가 끝없이 반복되는 local optimization 패턴에 빠질 위험이 크다.

### Decision
Boundary Topic Move를 Island 단위 알고리즘으로 구현하지 않는다. 대신 `docs/hybrid_architecture.md`에 **Night Batch v2(Topic Graph Reconstruction)** 설계를 추가한다 — 핵심 원칙: "Night Batch의 최소 이동 단위는 Island가 아니라 Topic이다." Merge/Split/Boundary Move를 각각의 연산으로 두지 않고 "Topic Graph의 Connected Component 재계산" 하나로 통일한다.

## Experiment #24: Topic Graph Reconstruction - Chaining Instability
날짜: 2026-07-18

### Hypothesis
Night Batch v2(Topic Graph, `topic_graph_reconstruct`)를 Backend User/AI Researcher에 적용하면, Island 단위 접근에서 못 잡던 전역 중복을 Topic 단위 재계산으로 해소할 수 있을 것이다. 두 페르소나를 동시에 만족하는(Backend=1개 유지, AI Researcher=여러 개로 자연스럽게 갈리면서 중복은 낮은) edge_threshold 구간이 있는지 확인한다.

### Data
모든 Topic 쌍의 center_vector cosine similarity로 그래프를 만들고(edge_threshold 이상이면 연결), Union-Find로 Connected Component를 찾아 새 Island로 재구성. edge_threshold를 0.24(island_threshold 잠정 재사용)부터 0.60까지 스윕(`experiment_topic_graph.py`).

### Result
| Threshold | Backend User | AI Researcher |
|---|---|---|
| 0.24~0.35 | 1개, 중복 0% | 1개, 중복 0% |
| 0.40 | 3개, 중복 2/9 | 3개, 중복 1/9 |
| 0.45 | 7개, 중복 3/9 | 8개, 중복 4/9 |
| 0.50 | 10개, 중복 5/9 | 13개, 중복 5/9 |
| 0.55~0.60 | 13~15개, 중복 5~7/9 | 21~22개, 중복 7/9 |

두 페르소나가 거의 동일하게 움직인다 — threshold를 조금만 올려도 "전부 하나"에서 "전부 쪼개지며 중복도 같이 증가"로 바로 건너뛴다. 두 페르소나를 동시에 만족하는 안정적인 중간 구간이 없다.

### Insight
원인은 pairwise threshold + Union-Find의 **체이닝(chaining)**이다 — 예를 들어 RLHF Topic이 거의 모든 다른 Topic과 0.5대 유사도를 가진 "허브" 역할을 해서, A-B와 B-C가 각각 threshold를 넘으면 A-C가 안 닮았어도 Union-Find가 셋을 하나의 Component로 묶어버린다. **이건 Experiment #6~7(Scrap 레벨 Greedy + 단일 Threshold가 안정적인 구간을 못 찾았던 문제)이 Topic 레벨에서 그대로 재현된 것**이다 — Scrap 레벨에서 Greedy+Threshold를 버리고 HDBSCAN(밀도 기반)으로 바꿔서 해결했던 것과 같은 구조의 문제가, Topic 레벨의 naive Union-Find 접근에서 다시 나타났다.

### Decision
`docs/algorithm_limitations.md`에 **Finding #004**(Pairwise Threshold Graph exhibits chaining instability) 신설 — Evidence로 Experiment #6~7(Scrap 레벨), Experiment #23(Island 단위 Split의 local-only 한계), Experiment #24(Topic 레벨 체이닝)를 연결한다. Union-Find(단일 threshold)를 Topic-level HDBSCAN으로 교체하는 게 다음 세션의 목표(**Experiment #25**, 미실행) — Experiment #22에서 HDBSCAN이 AI Researcher의 scrap 레벨 구조를 실제로 잘 나눠줬던 방법론을 이번엔 Topic 레벨(더 적고 밀도 높은 데이터 포인트)에 그대로 적용한다.

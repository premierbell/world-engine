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

## Experiment #25: Topic-level HDBSCAN - Two Variants, Both Fall Short
날짜: 2026-07-18

### Hypothesis
Union-Find의 체이닝 문제(Finding #004)를 Topic-level HDBSCAN(Experiment #12/#22에서 이미 검증된 밀도 기반 방법을 Topic에 적용)으로 교체하면 해결될 것이다.

### Data
두 가지 변형을 Backend User/AI Researcher에 적용:
- **변형 A (Topic-centroid HDBSCAN)**: 각 Topic의 `center_vector`를 직접 HDBSCAN으로 클러스터링(`topic_graph_reconstruct_hdbscan`).
- **변형 B (Scrap-informed Topic Regroup)**: scrap 레벨 HDBSCAN(이미 검증됨)의 클러스터 라벨을 참고해서, 각 Topic이 자기 스크랩들의 다수결 라벨에 따라 그룹화되도록 재구성.

두 변형 모두 `min_cluster_size`/`min_samples`를 스윕.

### Result
**변형 A**: 온라인 단계에서 이미 Topic이 21~27개(71개 스크랩 대비 Topic당 평균 3개 미만)로 잘게 나뉘어 있어서, 어떤 파라미터에서도 Backend User가 12~21개로 쪼개짐(중복 5~9/9) — 원래 1개/0%였던 Merge-only보다 훨씬 나쁨.

**변형 B**: 최선의 경우(mcs=4~6) AI Researcher는 5개/2/9로 개선됐지만, **Backend User는 최선이 7개/4~9(1개/0%에 못 미침)**. Scrap 레벨 HDBSCAN 자체가 Backend User를 "58+7+noise 6"으로 쪼개는데(완벽한 1개 클러스터가 아님), Island 단위로 다수결을 낼 때는 여러 Topic의 스크랩이 뭉뚱그려지며 이 노이즈가 평균화돼 purity≥0.5를 넘겼지만, Topic 단위(스크랩 2~4개)로 내리면 그 평균화 효과가 사라져 노이즈에 더 취약해진다.

### Insight
두 변형 다 실패한 이유가 다르지 않다 — **Aggregation Level(어느 단위에서 의사결정을 내리는가)의 근본적인 트레이드오프**다:

| 접근 | Backend User | AI Researcher | 특징 |
|---|---|---|---|
| Island 단위 (v0 Merge) | 1개, 0% (매우 안정적) | 6개, 77.8% (과병합 못 고침) | 표본이 많아 노이즈 평균화 |
| Topic 단위 (Union-Find/HDBSCAN 변형 A/B) | 7~22개, 4~9/9 (과분리) | 5~27개, 2~8/9 | 표본이 적어 노이즈 증폭 |

Island 단위는 안정적이지만 해상도가 낮고(AI Researcher의 진짜 다중 구조를 못 봄), Topic 단위는 해상도는 높지만 표본 부족으로 노이즈에 취약하다 — **Stability ↔ Resolution 트레이드오프**.

### Decision
`docs/algorithm_limitations.md`에 **Finding #005**(Aggregation Level Trade-off) 신설. 오늘 시도한 4가지(Merge-only, Split, Topic Graph Union-Find, Topic HDBSCAN 변형 A/B)는 겉보기엔 다른 알고리즘이었지만 전부 "의사결정 계층을 Island/Topic 중 어디에 둘 것인가"를 바꾼 것뿐이었다는 게 이번 실험으로 명확해졌다. 다음 세션은 구현이 아니라 설계 세션으로 시작한다 — **Open Question: "Night Batch의 본질은 더 좋은 클러스터링을 찾는 것인가, 아니면 문제가 있는 Island만 최소한으로 수정하는 것인가?"** Backend User는 Online 결과가 이미 좋은데 Night Batch가 이걸 다시 건드리는 것 자체가 문제일 수 있다 — "전체 재구성"이 아니라 "의심스러운 Island만 선택적으로 재평가"하는 방향이 다음 실험 후보다(미설계).

## Finding #006: Topic 오염은 Island가 아니라 Online Topic Formation에서 시작된다
날짜: 2026-07-18

### Hypothesis
Finding #005의 Open Question("Night Batch는 전체 재구성인가, 선택적 재평가인가?")에 답하기 위해 `selective_night_batch`(purity 높은 Island는 안 건드리고, 낮은 Island만 Split 후보로 검토 + 조각을 기존 Island에 흡수)를 구현해서 검증했다.

### Data
Backend User/AI Researcher에 `selective_night_batch`를 min_cluster_size 3~7로 스윕(`experiment_topic_contamination.py`로 원인 진단).

### Result
Backend User는 1개/0%로 여전히 잘 유지됐다. **AI Researcher는 파라미터를 바꿔도 "전부 1개로 뭉침"(mcs≥4)과 "9개인데 8/9 중복"(mcs=3)을 오갈 뿐, 원하는 결과(여러 개로 자연스럽게 갈리며 중복 낮음)에 도달하지 못했다.**

원인을 Island #0 내부에서 직접 확인했다:
```
Island 0 / Topic 0: {RLHF:7, Transformer:6, Fine-tuning:5, Multimodal:4,
                      Agent:4, Diffusion:2, Evaluation:1, Prompt Engineering:1}
(총 30개 스크랩, 8개 실제 주제)
```
27개 Topic 중 5개(19%)가 2개 이상의 실제 주제를 섞고 있었고, 그중 가장 심한 Topic 0 하나가 전체 71개 스크랩 중 30개(42%)를 차지했다.

### Insight
지금까지의 모든 Night Batch 버전(v0~v3)은 "Topic은 신뢰할 수 있는 원자 단위"라고 가정하고 Topic을 통째로 옮기거나 합치기만 했다. 하지만 **Topic 형성 시점(Online, `world.py`의 `Island.add()`, `topic_threshold=0.42`)부터 이미 오염**돼 있었다면 이 가정 자체가 틀린 것이고, 어떤 Night Batch 설계도 이 문제를 못 고친다.

더 중요한 연결: `topic_threshold`를 캘리브레이션한 실험(Experiment #6/#7)은 island_threshold 때와 마찬가지로 **Offline Pairwise 실험**이었다. Finding #001의 Root Cause에서 이미 "Offline Pairwise 실험은 순서 의존성이 없는 문제라 그 결과를 Online 알고리즘에 그대로 적용할 수 없다"고 적었는데, 이 문장이 island_threshold뿐 아니라 topic_threshold에도 그대로 적용되는 얘기였다. 다만 지금까지의 Order Sensitivity 실험(#8/#9/#10)은 전부 Island 레벨(개수, F1)만 측정했지 Topic 순수도는 한 번도 측정하지 않아서 오늘까지 드러나지 않았다.

### Decision
`docs/algorithm_limitations.md`에 **Finding #006** 신설(Status: Open). 로드맵을 재구성한다 — Step 5(Online Topic Formation) → **Step 5.25(Topic Validation/Repair, 신설)** → Step 5.5(Night Batch) → Step 6(Label). 다음 세션은 Night Batch 구현을 이어가지 않고 **Topic Formation Research**로 전환한다 — 연구 질문 5가지: ①Topic이 온라인에서 어떻게 생성되어야 하는가 ②Topic은 immutable인가 ③Topic도 Night Batch(또는 그 앞 단계)의 대상인가 ④Topic을 scrap 단위에서 다시 만들 수 있는가 ⑤Topic의 identity_vector는 언제 확정되는가. 오늘 구현한 Night Batch v0~v3는 전부 폐기하지 않고 Finding #003~#005의 근거로 남긴다.

## Experiment #27: Topic-level Order Sensitivity Test
날짜: 2026-07-18

### Hypothesis
Finding #006에서 발견한 Topic 오염(Island #0의 Topic 0이 8개 실제 주제를 섞음)이 우연이 아니라, Finding #001(Island Order Sensitivity)과 같은 구조적 원인(Greedy + EMA + 단일 Threshold)이 Topic 레벨에도 처음부터 있었기 때문이라면, 같은 데이터를 순서만 바꿔서 반복 실행했을 때 Topic 구성/순수도가 크게 흔들릴 것이다.

### Data
AI Researcher의 71개 스크랩을 원래 Day 순서 + 랜덤 셔플 10회(seed 1~10)로 반복 실행(`assign_scrap`만 사용, Night Batch 없음). 각 결과에서 새로 정의한 **Topic Purity**(`evaluation_metrics.md` 참고)와 Topic 개수, 최대 오염 Topic 크기를 측정(`experiment_topic_order_sensitivity.py`).

### Result
| 지표 | 값 |
|---|---|
| Topic Purity 범위 (11회) | 0.577 ~ 0.817 |
| Topic Purity std | 0.091 |
| Topic 개수 범위 | 22 ~ 34개 |
| 최대 오염 Topic 크기 | 7 ~ 34개 스크랩 |

같은 데이터, 순서만 다른데 Topic Purity가 24%p 가까이 흔들리고 최대 오염 Topic 크기도 7~34개로 요동쳤다.

### Insight
Finding #001에서 Island 개수가 순서에 따라 2~4개로 흔들렸던 것(Experiment #9)과 같은 크기, 같은 성격의 불안정성이 Topic 레벨에서도 확인됐다. 이건 우연이 아니라 **Scrap→Topic 편입(topic_threshold)과 Topic→Island 편입(island_threshold)이 서로 다른 계층에 적용된 같은 알고리즘(Greedy + EMA + 단일 Threshold)이기 때문**이다 — 계층이 다를 뿐 원인은 동일하다.

### Decision
- `docs/algorithm_limitations.md` Finding #006을 **"Greedy + EMA + Threshold는 계층과 무관하게 같은 방식으로 실패한다 (Hierarchical Instability)"**로 재구성(원래는 "Topic Formation Failure"로 좁게 명명했었음). Evidence 2로 이번 실험 추가.
- `docs/evaluation_metrics.md`의 Topic Purity TODO를 정식 정의로 채움.
- **연구 질문 우선순위 재조정**: 기존 5개 질문 앞에 **Question #0(신규, 최우선): "Topic은 Online에서 확정되어야 하는가?"**를 추가 — immutable 여부를 논하기 전에 "언제 확정할지"부터 답해야 한다는 판단. Product Principle("모든 성장은 즉시 체감 가능해야 한다")과 "Topic이 아직 확정 안 됐다"는 사실이 충돌한다는 점도 명시 — "임시 Topic → Night Batch → 확정 Topic" 2단계 생애주기가 필요한지가 Question #0의 핵심 하위 주제.

## Design Decision: Anchor Model (Night Batch v0~v3를 대체)
날짜: 2026-07-18

### Background
Finding #006 이후 바로 구현으로 들어가지 않고 "Topic의 생애주기(Lifecycle)를 어떻게 정의할 것인가"부터 논의했다 — 그 결정이 나오면 알고리즘(Greedy 유지 여부, HDBSCAN 채택 등)은 자연스럽게 따라온다는 판단(Product Decision #002, Hybrid Architecture Invariants 때와 같은 "원칙 먼저, 알고리즘은 나중" 패턴).

### 논의 과정
1. **초안(Repair 모델)**: Online Provisional Topic → Night Batch가 purity를 확인해서 Confirmed로 승격("Repair"). 기각됨 — AI Researcher의 30개 스크랩짜리 오염 Topic은 "조금 고치는" 수준이 아니라 애초에 틀렸다는 게 Finding #006의 증거였다.
2. **수정안(Reconstruction 모델)**: Night Batch는 Greedy 결과를 참고하지 않고 스크랩을 처음부터 다시 클러스터링한다. Online은 순수 UX Preview, Offline이 Truth. Topic과 Island가 완전히 같은 Lifecycle(Provisional→Confirmed)을 공유한다는 것도 이 단계에서 확인 — 아키텍처적 대칭성이 큼.
3. **경계선 추가**: "Offline이 전부 다시 계산한다"를 문자 그대로 받아들이면 이미 Confirmed된 Anchor까지 매번 재계산 대상이 되어 좌표 불변/Minimum Change Principle과 충돌한다는 지적 — Reconstruction의 대상은 "새 스크랩만"으로 제한.
4. **최종안(Anchor Model)**: Confirmed Topic/Island를 "움직이지 않는 Anchor"로 정의. 새 스크랩만 원점에서 재클러스터링(HDBSCAN)하고, 그 결과가 기존 Anchor와 가까우면 Attach, 아니면 새 Anchor 생성. Anchor 자체는 routine Night Batch에서 수정 대상이 아니라 판단 기준(Context)으로만 쓰인다.

### Decision
`docs/anchor_model.md` 신설 — Night Batch v0~v3(`docs/hybrid_architecture.md`)를 대체하는 통합 설계로 문서화:
- **핵심 원칙**: Greedy Online은 Preview UX만 담당, 확정(Truth)은 Night Batch(Anchor 형성)에서만 일어난다.
- **Lifecycle**: Scrap → Provisional Topic → Confirmed Topic(Anchor) → Provisional Island → Confirmed Island(Anchor). Topic과 Island가 동일 구조를 공유.
- **Immutability의 예외**: routine Night Batch에서 Anchor는 불변이지만, 명시적 **Migration Event**(알고리즘 버전 업그레이드/대규모 재색인/사용자 요청)에서는 전체 재구성을 허용 — 장기 개념 드리프트(예: "LLM" Topic이 2년 뒤 Reasoning/Agents/MCP까지 포괄) 대응.
- **Research Question #0/#1 최종 답**: Q0("Online에서 확정되는 계층이 존재해야 하는가") → 없다. Q1("Offline이 Greedy 결과를 얼마나 재사용해야 하는가", 신설) → 새 데이터는 재사용 안 함(원점 재계산), Confirmed Anchor는 Context로만 참고.
- `docs/hybrid_architecture.md` 최상단에 "Night Batch v0~v3는 anchor_model.md로 대체됨" 업데이트 노트 추가(문서 자체는 Finding #003~#005 근거로 보존).
- `docs/algorithm_limitations.md` Finding #006의 Status를 "Resolved(설계 확정, 구현 전)"로 갱신.

### Next Step
`docs/anchor_model.md`의 Open Questions(Attach 판단 기준/threshold, 여러 candidate가 같은 Anchor를 두고 경쟁할 때 처리, Migration Event 트리거 조건, Provisional 상태 UX 노출 여부)부터 다음 세션을 시작한다 — 아직 구현은 시작하지 않았다.

## Experiment #28: Anchor Model v0 구현 - 순서 독립성은 확인, attach_threshold만으로는 품질 목표를 달성하지 못함
날짜: 2026-07-18

### Hypothesis
Anchor Model 설계(`docs/anchor_model.md`) 이후 첫 구현인 night_batch_anchor()가
Finding #001/#006의 순서 의존성을 실제로 없애는지, Duplication Rate/Purity
기준으로 쓸 만한 품질을 내는지 확인한다.

### Data
구현 중 체이닝 버그를 발견하고 고쳤다 — find_best_anchor()가 배치 처리 도중
계속 자라는 result를 비교 대상으로 삼아서, 같은 배치 안에서 방금 생긴
Anchor에 뒤이은 클러스터가 달라붙는 구조였다(Finding #004의 허브 체이닝이
HDBSCAN-cluster 단위에서 재현된 것). 비교 대상을 배치 시작 시점의 고정
스냅샷(original_anchors)으로 제한해서 고쳤다.

Backend User/AI Researcher(day 1=5개/7=20개/30=46개, 총 71개)에 실제 운영
패턴(Day1→Day7→Day30, 매번 그때까지의 Confirmed Anchor 위에서 새 스크랩만
처리)을 재현. attach_threshold를 0.15~0.40으로 스윕(experiment_anchor_model.py).

### Result
1. 순서 독립성: 각 Day 배치 내부 순서를 3가지로 바꿔도 최종 Island 수/
   Duplication Rate 완전히 동일(Backend=10개/66.7%, AI Researcher=13개/88.9%,
   threshold=0.30).
2. Duplication Rate는 threshold와 무관하게 고정: 0.15~0.40 전 구간에서
   Backend=66.7%(6/9), AI Researcher=88.9%(8/9).
3. Topic Purity는 단조 개선: 같은 구간에서 Backend 0.380→0.648,
   AI Researcher 0.338→0.606.
4. Island 개수도 함께 증가: threshold=0.40에서 Backend=14개,
   AI Researcher=20개(실제 주제 수 9개 대비 과분할).
5. Day1 초기 Anchor 가설(Day1이 너무 작아 빈약한 Anchor를 만든다)은
   페르소나마다 다르게 나타남: AI Researcher는 Day1+Day7 병합 시 낮은
   threshold(0.20~0.25)에서 Duplication(88.9%→77.8%)과 Purity(0.338→0.437)
   둘 다 개선. Backend User는 반대로 병합 시 Purity가 악화(0.380→0.282)되며
   Duplication만 개선(66.7%→44.4%). threshold≥0.35에서는 병합 여부와 무관하게
   두 시나리오가 거의 수렴.

### Insight
- 체이닝 버그 수정은 확인됨 — 콜드스타트(단일 배치)로 재현하면 raw HDBSCAN
  결과(Backend={58,7}+noise6, AI Researcher=10개 클러스터+noise20)와 정확히
  일치하는 구성이 나온다. 수정 전에는 전부 1개로 뭉쳤었다.
- Duplication Rate는 연구용 지표로 해상도가 부족하다 — "2개 이상 Island에
  걸치면 무조건 중복"이라는 binary라서 threshold가 만들고 있는 점진적 품질
  개선(Purity 상승)을 완전히 놓친다. 제품 지표로는 여전히 유효하지만,
  알고리즘 튜닝의 연구 지표로는 Purity를 같이 봐야 한다.
- Day1 가설은 부분적으로만 지지됨 — 단일 원인(초기 배치 크기)으로 설명되지
  않는다는 것 자체가 결과다.
- attach_threshold 조정만으로는 "실제 주제 수만큼의 Island"라는 목표에
  가까워지지 않았다 — Purity를 높이면 Island 수도 같이 늘어난다. 붙였을 때
  얼마나 순수한가와 얼마나 잘게 쪼개지는가가 attach_threshold라는 단일
  파라미터에 묶여 있는 것으로 이번 실험 범위에서는 관찰됐다.

### Decision
- docs/algorithm_limitations.md Finding #004에 Evidence 4로 이번 체이닝
  버그(및 수정)를 연결.
- docs/evaluation_metrics.md의 Topic Duplication Rate 항목에 "연구 지표로는
  해상도가 부족하다" 주의사항 추가.
- Research Insight #001 신설(아래).
- 다음 세션은 threshold 튜닝을 이어가지 않고, "attach 메커니즘 자체를
  바꾸려면 무엇을 판단 기준으로 써야 하는가"를 새 Research Question으로
  시작한다(nearest-anchor 단일 비교 대신 cluster 내부 일관성, top-k 후보
  비교 등 - 아직 가설 없음).

## Research Insight #001: Parameter Tuning Cannot Resolve the Precision–Fragmentation Trade-off
Experiment #28에서 관찰. attach_threshold를 올리면 Topic Purity는 계속
좋아지지만 Island 개수도 함께 계속 늘어난다 — "잘못 붙는 걸 줄이는 것"과
"충분히 크게 뭉치는 것"이 이번 구현에서는 반대 방향으로 움직이는 것으로
보였다. Experiment #28 범위(attach_threshold 0.15~0.40, nearest-anchor 단일
비교 방식)에서는 threshold 조정만으로 이 Trade-off를 제거하는 지점은
관찰되지 않았다 — attach 메커니즘 자체(nearest-anchor 단일 비교가 아닌
다른 판단 기준)를 바꿔야 하는지가 다음 Research Question이다.

## Experiment #29: Margin Distribution Analysis - Margin 가설 기각
날짜: 2026-07-18

### Hypothesis
Research Insight #001 이후, attach 메커니즘을 바로 재설계하지 않고 먼저
관찰한다. 가설(Margin Hypothesis): 지금은 1등 Anchor가 threshold만 넘으면
무조건 붙인다 - 2등과의 격차(margin)를 안 본다. margin이 작은("애매한")
attach일수록 실제로 잘못된(다른 실제 주제를 섞는) 판단일 것이다.

### Data
world.py의 night_batch_anchor()에 AttachTrace(best/second similarity,
margin, decision, attach 직전 Anchor 구성 스냅샷)를 옵션으로 추가.
Day1→7→30 증분 시나리오(threshold=0.30)에서 모든 ATTACH 이벤트를 수집하고,
"cluster의 다수결 실제 주제 == attach 직전 Anchor의 다수결 실제 주제"로
사후 채점(experiment_margin_analysis.py).

### Result
- 전체 정확도: Backend User 23.1%(3/13), AI Researcher 5.6%(1/18).
- margin vs correctness 상관계수: Backend 0.214, AI Researcher **-0.201**.
- best_similarity vs correctness 상관계수: Backend 0.708, AI Researcher 0.229.
- margin이 큰(확신 있게 붙인) 사례도 잘못된 attach인 경우가 흔했다 — 예:
  AI Researcher에서 RLHF 클러스터(13개, best_sim=0.501)가 margin=0.052로
  Transformer Anchor에 붙음.

### Insight
Margin Hypothesis는 기각됐다. 더 중요한 건 margin이 아니라 threshold를
넘긴 ATTACH 판단 자체가 대부분 틀렸다는 것(정확도 5.6~23.1%) — 판단 규칙을
조금 손보는 수준이 아니라는 신호다. AI Researcher에서 margin과
best_similarity 둘 다 약하다는 건 "가까운 Anchor를 찾는 것" 자체가 이 의미
공간에서는 신뢰할 수 있는 판단 기준이 아닐 수 있다는 뜻이다.

### Decision
Margin rule은 구현하지 않는다. **Research Question #2 신설: "Anchor는
무엇으로 표현되어야 하는가?"** — identity_vector(단일 평균 벡터)가 정말
Anchor를 대표하는지부터 확인한다(Experiment #30).

## Experiment #30: Anchor Representation Analysis
날짜: 2026-07-18

### Hypothesis
identity_vector 하나로 Anchor를 대표하는 방식이 판별력을 잃는다면, Anchor의
개별 멤버 정보를 함께 사용하는 표현이 correctness와 더 높은 상관을 보여야
한다.

### Data
Experiment #29의 ATTACH 이벤트(anchor_scraps_before로 attach 직전 Anchor
구성을 그대로 보존)마다 세 가지 유사도를 계산: centroid_similarity(기존
기준), nearest_member_similarity(멤버 중 최댓값), topk_avg_similarity(상위
3개 평균). 각각을 correctness와 상관분석(experiment_representation_analysis.py).

### Result
| 지표 | Backend User | AI Researcher |
|---|---|---|
| centroid_similarity (기존) | 0.708 | 0.229 |
| nearest_member_similarity | 0.661 | 0.353 |
| topk_avg_similarity (k=3) | **0.742** | **0.517** |

AI Researcher에서 top-3 평균이 centroid 대비 상관계수를 2배 이상 끌어올렸다
(0.229→0.517). Backend도 소폭 개선(0.708→0.742). 반면 "가장 가까운 멤버 1개"
단독은 Backend에서 오히려 centroid보다 나빴다(0.661) — 극단값 하나에 낚이는
노이즈로 추정.

### Insight
Member 기반 비교(특히 top-k 평균)가 이 두 데이터셋에서는 단일 centroid보다
더 판별력 있는 것으로 관찰됐다 — "평균 벡터가 정보를 잃는다"는 가설이 정량적
증거로 지지받았다(아직 원인이 확정된 건 아니다). 다만 nearest-member 단독은
노이즈에 취약해서 "여러 점 중 하나"가 아니라 "여러 점의 요약(top-k 평균)"이
더 안정적인 절충점으로 보인다.

### Decision
`docs/algorithm_limitations.md`에 **Finding #007**(Representation Loss)
신설 — Finding #004(local connectivity 문제)와는 다른 클래스의 문제로 명시.
`docs/anchor_model.md`의 Open Questions에 **"Anchor는 무엇으로 표현되어야
하는가?"**를 후보 목록(identity_vector/nearest member/top-k averaging/
distribution/prototype set)과 함께 추가. 다음 세션은 이 후보들을 실제
attach 메커니즘으로 설계/구현할지부터 시작한다 - k값, 멤버 수가 많아질 때의
계산 비용, Provisional 단계 적용 여부는 아직 미검증.

## Experiment #31: Top-k Member Representation을 실제 Attach 판단 기준으로 사용 - Trade-off 이동, 해결 아님
날짜: 2026-07-18

### Hypothesis
Experiment #30에서 top-k 멤버 평균이 centroid보다 correctness와 더 강하게
상관됐다면, 이걸 실제 attach 판단 기준으로 바꿨을 때 Research Insight
#001의 Precision-Fragmentation Trade-off가 완화되어야 한다 - 같은 Island
수에서 더 높은 Purity를 내거나, 더 적은 Island 수로 같은 Purity를 낼 수
있어야 한다.

### Data
night_batch_anchor()에 member_topk 파라미터를 추가해 attach 판단 기준을
centroid(identity_vector) 대신 top-3 멤버 평균 유사도로 전환. Experiment
#28과 동일한 방법론(Day1→7→30 증분, 순서 독립성, threshold sweep)으로
Backend User/AI Researcher를 재검증(experiment_topk_representation.py).

### Result
순서 독립성은 유지됨(Backend 9~10개, AI Researcher 9개, 셔플해도 거의
동일). 같은 Island 수로 맞춰 비교하면:

| Island 수 | Purity/Dup (centroid) | Purity/Dup (top-3) |
|---|---|---|
| Backend, 5개 | 0.380 / 66.7% | 0.239 / 22.2% |
| Backend, 10개 | 0.437 / 66.7% | 0.282 / 44.4% |
| AI Researcher, 5개 | 0.338 / 88.9% | 0.282 / 33.3% |
| AI Researcher, 14개 | 0.451 / 88.9% | 0.394 / 66.7% |

두 데이터셋 모두에서 일관된 패턴: top-3는 Duplication Rate를 뚜렷이
낮추지만 Purity도 함께 낮아진다.

### Insight
Experiment #30(post-hoc 채점: 이미 내려진 centroid 기준 attach 결정을
다른 지표로 다시 채점)에서 top-k가 더 잘 맞았던 것이, top-k를 실제
의사결정 기준(online policy)으로 바꿨을 때는 재현되지 않았다 - 오히려
같은 Precision-Fragmentation Trade-off 곡선 위에서 다른 지점(Duplication
우선)으로 이동했을 뿐이다. **좋은 사후 평가 지표(post-hoc metric)가 좋은
의사결정 정책(online policy)이 되는 것은 아니다** - 어떤 attach 결정을
내리느냐에 따라 이후 Anchor의 멤버 구성 자체가 달라지므로(정책이 관측
분포 자체를 바꾼다), 정적으로 측정한 상관관계가 정책으로 그대로 전이되지
않는다.

k값(1, 5, 전체 등)을 더 스윕하는 건 지금 하지 않는다 - 이미 확인된
Trade-off 곡선 위의 다른 점을 찾는 작업일 가능성이 높고, 지금 필요한 건
그 곡선 자체가 왜 존재하는지에 대한 더 근본적인 질문이다.

### Decision
Research Insight #002 신설(아래). Research Question #2를 "Anchor는
무엇으로 표현되어야 하는가?"에서 **"Attach는 무엇을 최적화해야
하는가?"**로 확장 - representation은 그 하위 질문이 된다. attach가 지금은
similarity 최대화만 목적함수로 삼는데, 제품이 실제로 원하는 건 Purity와
Duplication이라는 서로 다른 두 목표라는 게 이번 실험에서 드러났다.
`docs/algorithm_limitations.md` Finding #007에 Evidence 3/Status 갱신,
`docs/anchor_model.md` Open Question #0 확장.

## Research Insight #002: Post-hoc Metric ≠ Online Policy
Experiment #31에서 관찰. Experiment #30에서 top-k 멤버 평균이 correctness와
더 강하게 상관됐던 건 이미 내려진(centroid 기준) attach 결정을 사후에
재평가한 결과였다. 그 지표를 실제 attach 판단 기준(정책)으로 바꾸자 - 어떤
클러스터가 어떤 Anchor에 붙는지 자체가 달라지고, Anchor의 멤버 구성도 그에
따라 달라지므로 - 정적으로 관찰했던 상관관계가 그대로 재현되지 않았다.
좋은 평가 함수가 자동으로 좋은 의사결정 함수가 되지는 않는다. 이건 이번
프로젝트에서 Research Insight #001(Parameter Tuning으로 Trade-off를 못
깬다)과 같은 계열의 교훈이다 - 둘 다 "지금 있는 축(threshold 값, 또는
표현 방식) 위에서 이동하는 것만으로는 근본적인 Trade-off가 안 풀린다"는
걸 보여준다.

## Experiment #32: Assignment Matrix Analysis - Anchor 경쟁이 기본 상태임을 확인
날짜: 2026-07-18

### Hypothesis
Global Assignment(배치 전체를 한 번에 최적화)가 Greedy(candidate마다
독립적으로 가장 점수 높은 Anchor에 배정)보다 다른/나은 결과를 낼 가능성을
가지려면 최소 조건이 있다: 같은 배치 안에서 서로 다른 candidate가 1등으로
같은 Anchor를 두고 경쟁하는 상황이 실제로 존재해야 한다. 그런 경쟁이 없다면
목적함수를 뭘로 정의하든 Greedy와 Global Assignment는 항상 같은 결과를
낸다.

### Data
world.py에 attach 결정을 전혀 내리지 않는 순수 관찰용 함수
`compute_assignment_matrix()`를 추가(night_batch_anchor와 완전히 같은
클러스터링/점수 계산 로직을 공유하도록 `_cluster_new_scraps`/`_anchor_score`로
리팩터링해서 중복·드리프트 방지, 리팩터링 후 Experiment #31과 동일 결과
재현되는 것으로 회귀 없음 확인). Day1→7→30 증분 시나리오에서 Day7/Day30
배치마다(비교 대상 Anchor가 있는 시점만) candidate x Anchor 유사도 행렬을
기록(experiment_assignment_matrix.py).

### Result
- Top1-Top2 gap: Backend mean=0.046(median 0.050), AI Researcher
  mean=0.028(median 0.024) - gap<0.02(사실상 동점)인 candidate가 Backend
  7/18(39%), AI Researcher 11/26(42%).
- Entropy: Backend mean 1.178, AI Researcher mean 1.554 - 점수가 소수
  Anchor에 확 쏠리기보다 여러 Anchor에 걸쳐 퍼져있는 경향.
- **Anchor 경쟁**: 1등 Anchor가 같은 배치의 다른 candidate와 겹치는 경우가
  Backend 17/18건(94%), AI Researcher 25/26건(96%).

### Insight
경쟁이 예외가 아니라 기본 상태임이 확인됐다 - attach를 "candidate마다
독립적인 binary 판단(붙인다/안 붙인다)"으로 모델링하는 것 자체가 현실을
온전히 표현하지 못한다는 뜻이다. attach는 본질적으로 여러 candidate가
한정된 소수의 Anchor를 두고 다투는 **assignment problem**의 성격을 가진다.

이건 지금까지의 실험을 하나로 꿰는 서사이기도 하다 - Experiment #28
(threshold 조정)과 #31(representation 개선을 실제 정책에 적용)이 둘 다
Trade-off를 해결하지 못하고 이동만 시켰던 이유가, 애초에 각 candidate를
독립적으로 점수 매겨 판단하는 구조 자체의 한계였을 가능성이 생겼다 -
점수 함수(score function)를 아무리 바꿔도, 그 점수로 각자 독립 판단하는
구조 자체가 문제라면 해결이 안 된다.

**증명된 것과 아직 증명 안 된 것을 구분한다:**
- 증명됨: 경쟁(같은 배치에서 여러 candidate가 같은 1등 Anchor를 두고
  겹치는 것)은 예외가 아니라 기본 상태다.
- 증명 안 됨: Global Optimizer가 실제로 품질(Purity/Duplication)을
  개선하는지, 목적함수를 어떻게 정의해야 하는지, Greedy보다 나은 결과가
  실제로 나오는지 - 전부 열려 있다.

### Decision
Research Insight #003 신설(아래). Research Question #2("Attach는 무엇을
최적화해야 하는가")를 더 구체화해서 **Research Question #3: "Attach는
어떤 목적함수를 최적화해야 하는가?"**로 좁힌다 - 목적함수 후보(예:
`Similarity - PurityLoss - Fragmentation - NewAnchorCost` 형태의 가중합
등, 확정된 식 아님)를 정의하고, 그 목적함수를 Greedy와 Global Assignment
두 방식으로 풀어서 실제로 다른 결정이 나오는지 확인하는 게 다음 실험
(Experiment #33, 미실행)이다. Hungarian algorithm/ILP 같은 실제 Optimizer
구현은 그 이후 단계 - 지금 바로 구현하지 않는다. `docs/anchor_model.md`
Open Question #0 갱신.

## Research Insight #003: Attach Competition Is the Default State, Not the Exception
Experiment #32에서 관찰. 같은 배치 안에서 서로 다른 candidate가 1등으로
같은 Anchor를 선택하는 경우가 Backend 94%(17/18), AI Researcher
96%(25/26)에 달했다 - 경쟁이 드문 예외가 아니라 거의 모든 candidate에
해당하는 기본 상태다. 이건 attach를 candidate마다 독립적인 binary
판단으로 모델링하는 현재 구조(Experiment #28~31이 전부 이 구조 위에서
점수 함수만 바꿔온 것) 자체가 문제를 온전히 표현하지 못한다는 뜻이다 -
attach는 본질적으로 assignment problem이다. 다만 이 관찰이 "Global
Optimizer가 더 좋다"를 증명하지는 않는다 - 그건 목적함수를 정의하고
실제로 검증해야 할 별개의 질문이다(Research Question #3).

### Next Step
Research Question #3("Attach는 어떤 목적함수를 최적화해야 하는가?")부터
다음 세션을 시작한다 - candidate 목적함수를 정의하고(확정 아님, 여러 항의
가중합 형태 후보), Greedy와 Global Assignment가 그 목적함수 하에서 실제로
다른 결정을 내리는지부터 확인한다(Experiment #33). Optimizer(Hungarian
algorithm, min-cost matching, ILP 등) 구현은 그 이후 단계다.

## Experiment #33: Objective v0 - Greedy는 적어도 하나의 합리적인 목적함수에 대해 전역 최적이 아니다
날짜: 2026-07-18

### Hypothesis
Experiment #32에서 확인한 Anchor 경쟁이 실제로 의미가 있으려면, "같은
Anchor에 서로 다른 candidate를 몰아넣는 것 자체에 비용이 있는" 목적함수
하에서 Greedy와 다른(더 나은) 배정이 존재해야 한다. Optimizer(Hungarian/
ILP)는 아직 구현하지 않고, Greedy에서 시작한 지역 탐색(local search)으로
"더 나은 배정이 존재하는가"만 확인한다.

### Data
**Objective v0**(첫 시도, 확정된 목적함수 아님):

```
J(assignment) = Σ_c attach_score(c, assignment[c])
                - λ · Σ_(같은 Anchor로 배정된 c1,c2 쌍) (1 - cos_sim(c1, c2))
```

각 candidate가 얻는 attach 점수(신규 Anchor 선택은 attach_threshold를
기준값으로 취급)의 합에서, 같은 Anchor에 함께 배정된 candidate끼리 서로
안 닮을수록 벌점을 뺀다. **λ는 탐색을 위한 실험 파라미터이며 최적값을
의미하지 않는다** - pairwise dissimilarity penalty도 "이게 맞는
목적함수"가 아니라 "이런 종류의 항을 하나 넣으면 Greedy와 다른 해가
생기는가"를 보기 위한 첫 시도(Objective v0)일 뿐이다.

Greedy 배정에서 시작해 각 candidate를 다른 Anchor/신규로 바꿨을 때 J가
개선되면 채택하는 지역 탐색을 λ=0(대조군)~1.2로 스윕
(experiment_batch_objective.py).

### Result
- λ=0(대조군): 재배정 0건 - 목적함수가 Greedy와 동일할 때는 Local
  Search도 Greedy와 일치한다는 sanity check 통과.
- λ≥0.10: Backend User 18개 candidate 중 7~8개(약 40%), AI Researcher
  26개 중 9~10개(약 35~38%)가 재배정됨. J(local search)가 J(greedy)를
  λ가 커질수록 꾸준히 앞섬(예: Backend λ=0.3에서 5.186→6.445).

### Insight
**증명된 것**: Greedy는 적어도 하나의 합리적인 목적함수(Objective v0)에
대해 전역 최적이 아니다 - Local Search만으로도 더 높은 J를 내는 배정을
즉시, 대량으로 찾아냈다. 이건 "Global Search가 의미를 가질 수 있다"는
존재증명(existence proof)이다.

**아직 증명 안 된 것**: J(local search) > J(greedy)만 확인했을 뿐,
Purity가 실제로 좋아졌는지 / Duplication이 실제로 줄었는지 / 사용자
경험이 나아지는지는 전혀 모른다. 재배정 목록을 눈으로 봤을 때(예:
Backend의 Redis/Kafka candidate가 Spring/JPA Anchor에서 분리되는 방향)
방향이 그럴듯해 보이는 사례는 있었지만, 이건 육안 관찰일 뿐 정량 평가가
아니다 - Objective v0 자체가 좋은 목적함수인지는 아직 모른다.

정리하면: **Experiment #33은 "Global Search가 필요하다"를 증명한 게
아니라, "Global Search를 고려할 이유가 있다"를 증명했다.** 둘은 다르다.

더 중요한 전환: Experiment #28~32는 전부 "Similarity를 어떻게 계산할까"
(threshold, representation, margin)를 연구했다. Experiment #33은 처음으로
**Similarity가 목적함수의 한 항일 뿐**이라는 걸 보여준다 - 이번 실험은
"어떤 목적함수가 좋은가"를 검증한 게 아니라, 목적함수 자체를 별도의
연구 대상으로 분리해야 함을 보여준 첫 번째 증거다. 이제 연구의 중심은
Similarity Function이 아니라 Objective Design으로 이동한다(Similarity →
Objective → Optimization이라는 연구 계층이 처음 분리됨).

### Decision
Research Insight #004 신설(아래). `docs/anchor_model.md` Research
Question #3에 Experiment #33 결과 반영 - Objective v0(pairwise
dissimilarity penalty)는 "확정된 목적함수"가 아니라 "존재증명용 첫
시도"로 명시하고, 아직 안 들어간 후보 항(entropy penalty, purity
estimate, anchor confidence, new-anchor cost)을 나열. 다음 세션은 이
목적함수 후보들을 어떻게 설계/평가할지(실제 Purity/Duplication으로
검증하는 방법 포함)부터 시작한다 - Optimizer(Hungarian/ILP) 구현은
여전히 더 뒤 단계.

## Research Insight #004: Similarity Is Just One Term in the Objective - Objective Design Is a Separate Research Layer
Experiment #33에서 관찰. Experiment #28~32는 모두 "Similarity를 어떻게
계산/판단할까"라는 하나의 계층 안에서 움직였다(threshold 값,
representation 방식, margin, 경쟁 여부 관찰). Experiment #33은 처음으로
Similarity 위에 목적함수(Objective)라는 계층이 따로 있고, 그 목적함수를
어떻게 설계하느냐에 따라(같은 similarity 값을 쓰더라도) 완전히 다른
배정이 나올 수 있다는 걸 보였다. Greedy는 "Objective = Σ similarity"라는
가장 단순한(그리고 암묵적인) 목적함수 하에서의 최적해였을 뿐이다 -
연구의 중심이 Similarity Function에서 Objective Design으로 이동한다:
Similarity → Objective → Optimization이라는 세 계층이 이번에 처음
분리됐다.

### Next Step
목적함수 후보 항(entropy penalty, purity estimate, anchor confidence,
new-anchor cost 등)을 어떻게 설계/평가할지부터 다음 세션을 시작한다 -
Objective v0(pairwise dissimilarity penalty만)는 그중 한 항의 첫
시도였을 뿐이다. 실제 Purity/Duplication 개선으로 이어지는지 검증하는
방법도 함께 설계해야 한다 - 지금까지는 J(추상적 목적함수 값)만 봤지,
실제 World 상태에 반영했을 때의 품질은 한 번도 측정 안 했다.

## Experiment #34: Objective v0를 실제로 적용했을 때 품질이 정말 좋아지는가
날짜: 2026-07-18

### Hypothesis
Experiment #33은 J(local search) > J(greedy)만 확인했다 - 목적함수 값이
개선됐다는 것이지, 실제 Island 구조의 Topic Purity/Duplication Rate가
개선됐는지는 검증하지 않았다. Objective v0(pairwise dissimilarity
penalty)로 찾은 재배정을 실제 World 상태에 반영해서 Day1→7→30 전체
증분 시나리오를 끝까지 돌리고, Greedy(night_batch_anchor 그대로)와
Experiment #28과 같은 지표로 직접 비교한다.

### Data
Day1(비교 대상 Anchor가 아직 없는 첫 배치)은 night_batch_anchor로
그대로 처리 - Greedy와 Objective v0가 갈릴 수 있는 지점은 Anchor가 생긴
이후(Day7/Day30)뿐이다. 그 이후 배치부터는 Local Search(Experiment #33과
동일한 Objective v0)가 찾은 배정을 실제로 적용해서 Island를 만들고,
다음 배치의 입력으로 이어간다(experiment_objective_quality.py). λ=0(대조군)
~1.2로 스윕.

### Result
λ=0(대조군)은 Greedy와 정확히 동일한 결과(Backend 10개/66.7%/0.437,
AI Researcher 13개/88.9%/0.437)로 sanity check 통과.

| λ | Backend Island/Dup/Purity | AI Researcher Island/Dup/Purity |
|---|---|---|
| 0.00 (=Greedy) | 10 / 66.7% / 0.437 | 13 / 88.9% / 0.437 |
| 0.10 | 11 / 55.6% / 0.577 | 17 / 100.0% / 0.451 |
| 0.30 | 11 / 55.6% / 0.606 | 21 / 100.0% / 0.549 |
| 0.50~1.20 | 11 / 55.6% / 0.634 | 22 / 100.0% / 0.577 |

Backend User는 Purity와 Duplication이 **둘 다** 개선됐다(0.437→0.634,
66.7%→55.6%, Island 수는 10→11로 거의 안 늘어남). AI Researcher는
Purity는 개선됐지만(0.437→0.577) **Duplication은 오히려 악화**됐다
(88.9%→100.0%, 9개 실제 주제 전부가 2개 이상 Island에 걸치게 됨,
Island 수도 13→22로 급증).

### Insight
**증명된 것**: Objective v0는 실제 World 상태를 바꾼다(추상적인 J뿐 아니라
Topic Purity가 두 데이터셋 모두에서 실제로 변한다). 하지만 그 변화가
제품이 원하는 방향(Purity와 Duplication이 함께 좋아지는 것)과 항상
같지는 않다 - AI Researcher에서는 Purity를 올리는 대가로 Duplication이
뚜렷이 나빠졌다. **"J를 크게 만드는 것"과 "좋은 World를 만드는 것"은
동일하지 않다.**

**해석에 주의할 점**: 이 차이를 "Backend는 되고 AI Researcher는 안
된다"는 페르소나 의존성으로 단정하면 안 된다 - Virtual User가 페르소나당
1개뿐이라 일반화할 근거가 부족하다. 더 안전한 해석은 "Objective v0는
특정 구조의 데이터(지배적인 메가토픽이 있고 Topic 간 중첩이 적은 경우)
에서는 제품 목표와 정렬되지만, 다른 구조(9개 주제가 조밀하게 얽힌 경우)
에서는 정렬되지 않는다"는 것 - 원인 후보는 의미 공간의 조밀도, Topic 간
중첩 정도, 지배적 메가토픽 존재 여부 같은 **데이터의 구조적 특성**이지
"Backend/AI라는 사람의 차이"가 아니다.

AI Researcher의 결과가 오히려 더 많은 정보를 준다: Objective v0(pairwise
dissimilarity penalty 하나뿐)가 Purity는 밀어붙이지만 Duplication은
전혀 반영하지 못하고 있다는 신호다 - 지금 목적함수는 사실상 "Purity
근사치"에 가깝고, 제품이 실제로 원하는 두 목표(Purity + Duplication)를
균형 있게 반영하지 못한다.

### Decision
Research Insight #005 신설(아래). Research Question #3을 더 구체화한다 -
"Attach는 어떤 목적함수를 최적화해야 하는가?"에서 **"제품 목표(Purity +
Duplication)를 가장 잘 근사하는 목적함수는 무엇인가?"**로. 연구 계층이
한 겹 더 늘어났다: Similarity → Objective → Optimization이었던 것이
**Product Metric → Objective → Optimization**으로 재구성된다 -
Optimizer의 성능보다 Objective Design(그리고 그 Design이 Product
Metric을 얼마나 잘 근사하는가)이 더 근본적인 연구 대상이다.
`docs/anchor_model.md` Research Question #3 갱신.

## Research Insight #005: Objective Improvement ≠ Product Improvement
Experiment #34에서 관찰. Experiment #33에서 J(목적함수 값)가 개선된
배정을 실제로 적용했더니, 두 데이터셋 모두에서 Topic Purity는 실제로
올랐다(Objective v0가 명목상 하는 일은 하고 있다) - 하지만 Topic
Duplication Rate는 한쪽(AI Researcher)에서 오히려 악화됐다. 즉 J가
좋아진다고 제품이 원하는 두 목표(Purity, Duplication)가 함께 좋아지는
게 아니다 - 지금 목적함수(Objective v0)는 Purity 쪽으로 편향된
근사치일 뿐, 제품 목표 전체를 대표하지 못한다. 이건 Research Insight
#001(Parameter Tuning으로 Trade-off를 못 깬다)/#002(Post-hoc Metric ≠
Online Policy)와 같은 계열의 교훈이 목적함수 계층에서도 반복된 것이다 -
**"평가/최적화 기준으로 쓰는 대리 지표(proxy)가 좋아진다고 실제로 원하는
결과가 좋아지는 게 보장되지 않는다"**는 패턴이 이번에는 threshold도
representation도 아니라 목적함수 자체에서 나타났다.

### Next Step
Research Question #3 확장판("제품 목표를 가장 잘 근사하는 목적함수는
무엇인가?")부터 다음 세션을 시작한다 - Objective v0에 Duplication을
직접 반영하는 항(예: 같은 실제 주제로 추정되는 candidate가 여러 Anchor에
흩어지는 것에 대한 벌점, ground truth 없이 계산 가능한 근사가 필요)을
추가하는 게 유력한 다음 후보이지만 아직 설계 전이다.

## Experiment #35: Candidate-pair Similarity Distribution - Pairwise Similarity가 Fragmentation Penalty의 근거가 되지 못함
날짜: 2026-07-18

### Hypothesis
Objective v0에 Duplication을 반영하는 Fragmentation Penalty(서로 비슷한
candidate가 다른 target으로 갈라지면 벌점)를 추가하기 전에, 그 근거가 될
pairwise similarity가 실제로 "같은 실제 주제"를 구분하는 신호인지 먼저
확인한다. τ(문턱값)를 근거 없이 스윕하지 않고, 실제 candidate 쌍의 유사도
분포를 관찰해서 고른다.

### Data
Day7/Day30 배치에서 candidate 쌍의 centroid 유사도를 전부 계산하고
(compute_assignment_matrix 재사용), ground truth로 "같은 실제 주제 쌍"
vs "다른 실제 주제 쌍"으로 나눠서 분포를 비교했다
(experiment_pair_similarity_distribution.py). **이 실험에서만**(offline
파라미터 캘리브레이션 목적) ground truth를 사용한다 - island_threshold/
topic_threshold를 golden dataset F1로 캘리브레이션했던 것(Experiment
#6/#7)과 같은 성격이다. 실제 attach 판단 로직(world.py)은 여전히 ground
truth에 접근하지 않는다.

### Result
| | Backend | AI Researcher |
|---|---|---|
| 같은 주제 쌍 mean (range) | 0.359 (0.203~0.464) | 0.399 (0.202~0.687) |
| 다른 주제 쌍 mean (range) | 0.333 (0.164~0.599) | 0.352 (0.158~0.578) |

두 분포가 거의 겹친다. Backend는 같은 주제 쌍의 최댓값(0.464)이 다른
주제 쌍의 상위 10% 지점(0.494)보다도 낮다 - 어떤 τ를 골라도 그 문턱을
넘는 쌍이 진짜 같은 주제일 확률이 매우 낮다. AI Researcher는 조금
낫지만(같은 주제 쌍의 일부가 상위 구간에 있음), 같은 문턱을 넘는 다른
주제 쌍의 절대 개수가 압도적으로 많다.

### Insight
**Pairwise similarity는 Fragmentation Penalty의 신뢰할 만한 근거가
아니다.** 어떤 τ를 골라도 "같은 실제 주제라서 벌점을 주는" 경우보다
"우연히 비슷한 다른 주제라서 벌점을 주는"(=과병합 압력) 경우가
구조적으로 더 많을 가능성이 높다.

이건 이번 실험만의 결론이 아니다 - Experiment #29(Margin이 attach
정확도의 신호가 아니었음)와 Experiment #30/31(Representation을 바꿔도
근본 Trade-off가 안 풀림)이 전부 같은 더 큰 결론으로 수렴한다: **이
embedding 공간에서 pairwise cosine similarity 하나만으로는 "같은
Topic"이라는 관계를 충분히 표현하지 못한다.** λ2를 조정하는 건 이 약한
신호(signal)를 더 세게 또는 약하게 쓰는 것일 뿐 - signal 자체가 그대로면
Experiment #28의 threshold sweep처럼 또 다른 Trade-off 지점만 찾게 될
가능성이 높다. 그래서 λ2 스윕(Experiment #36)은 지금 하지 않는다.

### Decision
Research Insight #006 신설(아래). Research Question을 하나 더 추가한다
- **Research Question #4: "Duplication은 어떤 신호로 근사할 수
있는가?"**(Similarity가 아닌 다른 근사 방법 필요). 후보로 구조적
신호(candidate가 top-k Anchor 후보를 얼마나 공유하는지 - Experiment
#32의 assignment matrix에서 이미 일부 수집됨)가 논의됐지만 아직 검증
전이다. `docs/anchor_model.md`에 Research Question #4 추가.

## Research Insight #006: Pairwise Similarity Is Not a Reliable Proxy for Topic Identity
Experiment #35에서 관찰. Pairwise similarity는 attach 판단 기준(threshold,
Experiment #28/#31)으로도, Fragmentation Penalty의 근거(Experiment #35)로도
"같은 실제 주제인가"를 충분히 구분하지 못했다. 같은 주제 쌍과 다른 주제
쌍의 유사도 분포가 거의 겹치고, 심지어 한 데이터셋(Backend)에서는 같은
주제 쌍의 최댓값이 다른 주제 쌍의 상위 10% 지점보다 낮았다. 이건
Margin(Experiment #29)이 attach 정확도의 신호가 아니었던 것과 같은
계열의 결론이다 - **Similarity 하나로 표현 가능한 관계와, "같은
Topic"이라는 관계 사이에는 이 embedding 공간에서 구조적인 간극이 있다.**

### Next Step
Research Question #4("Duplication은 어떤 신호로 근사할 수 있는가?")부터
다음 세션을 시작한다 - Similarity 자체를 재조정(threshold, λ)하는 대신
다른 종류의 신호(예: 여러 candidate가 top-k Anchor 후보를 얼마나
공유하는지 같은 구조적 신호)를 탐색한다. Fragmentation Penalty(λ2 스윕,
Experiment #36)는 신뢰할 만한 입력 신호가 나오기 전까지 보류한다.

## Experiment #36: Structural Co-candidacy Signal - Similarity 계열 신호 탐색의 마지막 시도
날짜: 2026-07-18

### Hypothesis
두 candidate의 직접 embedding 유사도(Experiment #35)는 "같은 실제
주제인가"를 구분하지 못했다. 대신 구조적 신호 - 두 candidate가 어떤
Anchor들을 후보로 바라보고 있는지(top-k overlap, 전체 Anchor에 대한
점수 벡터 상관관계) - 가 direct similarity보다 판별력이 있는지 확인한다.

### Data
Experiment #35와 같은 배치(Day7/Day30)에서, 같은 실제 주제 쌍/다른 실제
주제 쌍 각각에 대해 세 가지 신호를 비교: direct pairwise similarity(대조군),
top-3 Anchor Overlap(Jaccard), score vector correlation(candidate의
전체 Anchor 점수 벡터끼리의 cosine)(experiment_structural_signal.py).

### Result
| 신호 | Backend 차이(같은-다른) | AI Researcher 차이(같은-다른) |
|---|---|---|
| Direct Pairwise Similarity (대조군) | +0.026 | +0.047 |
| Top-3 Anchor Overlap | +0.001 | -0.006 |
| Score Vector Correlation | -0.006 | -0.001 |

두 구조적 신호 모두 같은/다른 주제 쌍을 사실상 구분하지 못했다 - 이미
약했던 Direct Similarity보다도 판별력이 없거나(거의 0) 방향이
뒤집혔다(음수). Score Vector Correlation 자체가 절댓값으로 0.96~0.98에
달했다 - 같은 주제든 다른 주제든 거의 모든 candidate가 서로 거의
동일한 패턴으로 Anchor를 선호한다는 뜻이다.

### Insight
소수의 "허브" Anchor가 거의 모든 candidate의 선호 순위를 지배하고
있어서, "같은 Anchor를 바라보는가"는 실제 주제 동일성과 거의 무관하다 -
Experiment #32에서 확인한 Anchor 경쟁(94~96%)의 원인을 거꾸로 보여주는
결과이기도 하다(Finding #004 허브 체이닝과 같은 계열의 현상).

Margin(#29) → Representation(#30/31) → Direct Similarity(#35) → 구조적
신호(#36)까지, cosine similarity에서 파생 가능한 신호 네 가지가 전부
독립적으로 "같은 실제 주제인가"를 판별하는 데 실패했다. 이건 개별 신호
설계의 문제가 아니라 **이 embedding 공간에서 cosine similarity로 유도
가능한 어떤 신호도 Topic Identity 판별에 충분하지 않을 가능성**을
가리킨다.

### Decision
`docs/algorithm_limitations.md`에 **Finding #008**(Embedding Similarity
Encodes Semantic Relatedness, Not Topic Identity) 신설 - Experiment
#29~#36을 하나의 연구 축으로 마무리한다. **Similarity-derived
signals(Margin, Pairwise Similarity, Anchor Overlap, Score Correlation)를
이용한 Duplication 근사는 더 이상 진행하지 않는다** - 네 가지 독립적인
접근이 모두 "같은 Topic인지"를 안정적으로 판별하지 못했다. 이후 연구는
similarity의 활용법이 아니라, Topic identity를 정의하는 다른 정보원이
필요한지를 연구 대상으로 전환한다. `docs/anchor_model.md` Research
Question #4를 Closed로 갱신하고 Research Question #5를 신설한다.

## Experiment #37: Tag Discriminability Analysis
날짜: 2026-07-18

### Hypothesis
Research Question #5("Similarity만으로 Topic Identity를 만들 수 있는가?")
첫 실험. Embedding cosine similarity 대신 AI가 스크랩마다 추출한 구조화된
키워드 태그(`tag_extractor.py`, ai_rules.md Rule 1과 충돌하지 않음 - 태그
추출도 "이해" 계층)의 겹침(Jaccard)이 Topic Identity를 더 잘 판별하는지
확인한다. 아직 attach 판단은 바꾸지 않는다 - 신호 자체의 판별력만 본다
(Experiment #31의 교훈: post-hoc 신호가 실제 정책으로 이어지리라는 보장이
없다).

### Data
Day7/Day30 배치의 candidate 쌍마다 태그 집합의 Jaccard overlap을 계산해서
같은 실제 주제 쌍 vs 다른 실제 주제 쌍으로 비교(Experiment #35와 같은
방법론, `experiment_tag_discriminability.py`).

### Result
Backend: 같은 주제 쌍 mean=0.012, 다른 주제 쌍 mean=0.002(차이 +0.011).
AI Researcher: 같은 주제 쌍 mean=0.014, 다른 주제 쌍 mean=0.003(차이
+0.011). 방향은 일관되게 맞지만 절대적인 겹침 자체가 매우 드물다 -
Backend는 같은 주제 쌍 11개 중 8개, AI Researcher는 37개 중 33개가 겹침
정확히 0.

### Insight
Direct Similarity(Experiment #35, 차이 +0.026~0.047)보다 절대적 분리
폭은 작지만 방향은 일관됨 - 자유형(freeform) 추출이라 같은 개념도 텍스트
마다 다른 표현으로 갈라져서 안 겹칠 가능성이 있다(태그 자체가 나쁜
신호라기보다 표현이 흩어진 문제일 수 있음).

### Decision
Experiment #38(Error Analysis)로 겹침이 왜 0에 가까운지 원인을 먼저
분리한다 - 새 프롬프트를 바로 설계하지 않는다.

## Experiment #38: Tag Overlap Error Analysis (정성 분석)
날짜: 2026-07-18

### Hypothesis
Experiment #37의 낮은 겹침이 (a) 표현 불일치(synonym), (b) 추상화 수준
불일치, (c) 추출 자체의 불안정성, (d) 진짜 정보 부족 중 어디에서 오는지
사람이 직접 표본을 읽고 분류한다. 이 실험은 알고리즘을 만들지 않는다 -
같은/다른 실제 주제 쌍 표본(각 10개)의 태그를 나란히 출력만 한다
(`experiment_tag_error_analysis.py`).

### Data
AI Researcher/Backend User에서 각각 같은 주제 쌍 10개, 다른 주제 쌍 10개를
무작위 표본으로 뽑아 태그를 나란히 검토.

### Result
- **Precision은 좋음**: 표본에서 다른 실제 주제 쌍이 우연히 태그를 공유한
  사례는 하나도 없었다.
- **Recall이 나쁨**: 같은 실제 주제 쌍인데도 태그가 하나도 안 겹치는
  경우가 대부분(AI Researcher 10쌍 중 8쌍). 예: 둘 다 "Fine-tuning"인데
  한쪽은 `[instruction_tuning, model_training, task_instruction]`, 다른
  쪽은 `[dpo, fine_tuning, lora, ...rlhf]`로 전혀 다른 어휘.
  "LLM/LLM" 쌍도 `llm` vs `llm_agent`처럼 어간은 같지만 정확 문자열이
  안 겹침.
- 프롬프트가 "영어 소문자 snake_case"를 명시했는데도 한국어 태그(예:
  `차이점`, `학습_안정성`)가 계속 섞여 나옴.

### Insight
원인은 **Case B(추상화 수준 불일치)가 지배적**이고 Case A(표현 불일치)도
상당하다 - 자유형 추출이 각 스크랩의 구체적 하위 기법에 초점을 맞추다
보니 공통 상위 태그를 남기지 않는다. Case C(추출 불안정)는 노이즈로
확인되지만 부차적. **Case D(정보 자체가 없음)는 근거가 약함** - 정답
단어가 우연히 포함될 때는 실제로 잘 겹쳤다(정보가 없는 게 아니라
일관되게 안 나오는 것).

### Decision
Case A/B에 대응하는 다음 실험으로 **Experiment #39(Hierarchical Tag
Extraction)**를 설계한다 - 고정 vocabulary(유지보수 비용 크고 DPO/LoRA
같은 신기술을 fine_tuning으로 뭉개는 정보 손실 있음) 대신, LEVEL1(넓은
상위 범주)/LEVEL2(구체적 하위 개념) 2계층 태그로 Recall과 Precision을
동시에 노린다.

## Experiment #39: Hierarchical Tag Extraction
날짜: 2026-07-18

### Hypothesis
자유형 태그의 낮은 Recall은 정보 부족이 아니라 추상화 수준 불일치 때문
이다. LEVEL1(넓은 상위 범주 1개)과 LEVEL2(구체적 하위 개념 2~4개)를 함께
추출하면, LEVEL1에서 Recall이(같은 Topic이면 LEVEL1이 겹칠 확률이 높다),
LEVEL2에서 Precision이(DPO/RLHF 같은 세부 구분 유지) 동시에 확보될
것이다.

### Data
`HierarchicalTagExtractor`(`tag_extractor.py`)로 2계층 태그를 추출 -
프롬프트는 "이 스크랩이 어떤 폴더에 들어갈지"를 명시적으로 묻되, 데이터셋의
실제 ground truth 주제명은 예시에 전혀 노출하지 않았다(다른 도메인 예시로
형식만 학습). Experiment #37/38과 같은 방법론으로 LEVEL1 overlap/Jaccard,
LEVEL2 Jaccard를 같은/다른 주제 쌍으로 비교(`experiment_hierarchical_tags.py`).

### Result
가설과 반대 방향. Backend User는 같은 주제 쌍의 LEVEL1 겹침 비율이
**정확히 0%**(11쌍 전부). AI Researcher는 recall 2.7%(1/37)로 Experiment
#37의 flat 태그보다도 낮았다. 실제 값을 확인하니, 명백히 같은
"Transformer" 실제 주제인 8개 스크랩의 LEVEL1 태그가 `transformer_
architecture, transformer_models, positional_encoding, multi_head_
attention, encoder_decoder_architecture, transformer_models, layer_
normalization, natural_language_processing`로 8개 중 2개만 일치했다 -
"가장 넓은 상위 폴더 이름"을 명시적으로 요청해도 LLM은 여전히 각 스크랩이
다루는 구체적 메커니즘에 초점을 맞췄다.

### Insight
이건 프롬프트 설계의 문제가 아니라 더 근본적인 구조적 한계로 보인다 -
LLM은 각 문서를 정확하게 이해하고 있다(positional_encoding을 다루는
문서에 대해 "이 문서의 핵심은 positional encoding"이라고 답하는 건
틀린 게 아니다). 문제는 **여러 문서를 독립적으로(서로를 보지 못한 채)
태깅하는 한, "이 문서들이 같은 폴더에 들어가야 한다"는 정보가 애초에
그 판단 과정에 존재하지 않는다는 것**이다 - Document Understanding(문서
하나의 핵심이 뭔가)과 Corpus Taxonomy(여러 문서를 어떻게 묶을까)는
다른 문제이고, stateless(문서별 독립 처리) 추출은 원리적으로 후자를
만들어낼 메커니즘이 없다.

### Decision
`docs/algorithm_limitations.md`에 **Finding #009**(Independent Document
Understanding Cannot Produce a Shared Topic Identity) 신설 - Experiment
#29~#39를 아우르는 결론으로 승격한다. **Research Question #5("Similarity
만으로 Topic Identity를 만들 수 있는가?")에 답한다: 증거는 강하게
"아니오" 쪽을 가리킨다** - embedding similarity, margin, representation,
구조적 similarity, freeform tag, hierarchical tag까지 서로 다른 modality
6가지가 전부 같은 한계(문서별 독립 생성 신호로는 corpus 수준 taxonomy를
유도할 메커니즘이 없음)를 공유한다. **Research Question #6(신설)**:
"Topic Identity는 개별 문서의 속성인가, 여러 문서에 걸친 관계적
속성인가?" - `docs/anchor_model.md` 갱신.

## Experiment #40: Tag Relation Analysis (그래프 관찰, 임베딩/LLM/알고리즘 판단 없음)
날짜: 2026-07-18

### Hypothesis
Research Question #6 첫 실험. 태그를 바로 임베딩+HDBSCAN으로 묶기 전에,
더 앞선 질문부터 순수 관찰로 확인한다 - 태그들 사이에 실제로 안정적인
관계 구조(connectivity)가 존재하는가? Experiment #37의 freeform 태그로
그래프(노드=태그, 엣지="같은 스크랩에 함께 등장")를 만들고, Connected
Component가 실제 Topic 경계와 얼마나 일치하는지만 본다 - 임베딩도 LLM
판단도 추가로 쓰지 않는다.

### Data
Backend User/AI Researcher 각각의 태그 co-occurrence 그래프를 Union-Find로
Connected Component 분해(`experiment_tag_network_analysis.py`, Experiment
#37 태그 캐시 재사용, 추가 API 호출 없음).

### Result
- **작은 Component(크기 3~8)는 대체로 단일 실제 Topic으로 순수했다**
  (예: AI Researcher의 RLHFx17, Diffusionx13, Agentx9, Transformerx6 등).
- **하지만 거대한 "허브" Component가 하나씩 생겼다.** Backend User는
  전체 태그 209개 중 88개(42%)가 하나의 Component로 뭉쳐서 Kafka/
  Spring-JPA/Redis/RAG/Docker/MCP/LLM을 전부 섞었다. AI Researcher도
  크기 29짜리 Component가 Fine-tuning/Multimodal/RLHF/Evaluation/Prompt
  Engineering을 섞었다.
- 허브 Component를 빼고도 같은 Topic의 태그가 여러 Component에 흩어진
  경우가 많았다(Backend LLM 9개, AI Researcher Agent/Prompt Engineering
  각 9개 Component).

### Insight
Finding #004(Pairwise Threshold Graph는 Chaining에 취약하다)와 정확히
같은 실패 패턴이다 - "같은 스크랩에 함께 등장"이라는 단일 연결 기준 +
Union-Find(연결되면 무조건 하나로 합침)는, 소수의 범용적인 "허브" 태그가
서로 무관한 지역들을 transitively 이어버리는 체이닝에 취약하다. **관계
구조는 존재하지만("작은 Component는 순수하다"는 긍정적 신호), 순진한
연결성(connectivity) 판단으로는 못 쓴다** - 이 둘은 서로 다른 결론이다.

### Decision
Community Detection(Louvain/Leiden 등) 같은 더 정교한 그래프 알고리즘으로
바로 넘어가지 않는다 - 그 알고리즘들도 결국 "그래프 위에서 연결 구조를
찾는" 접근이고, edge weight를 cosine 기반으로 정의하면 Finding #008을
다시 만날 위험이 있다. 대신 `docs/algorithm_limitations.md`에 **Finding
#010**(Local Connectivity Is Not Topic Identity) 신설 - Finding #004
(Pairwise Threshold Graph)와 Experiment #40(Tag Graph)을 하나로 묶어
일반화한다. Research Question #5/#6을 잠정 종료하고, **Research Question
#7: "Topic Identity는 애초에 복원해야 하는 대상인가, 아니면 시스템이
시간이 지나며 형성(emerge)하는 대상인가?"**로 연구축을 전환한다.

## Experiment #41: Temporal Consistency Analysis (교란 요인 발견)
날짜: 2026-07-19

### Hypothesis
H1(사실상 증명됨): Topic Identity는 단일 관측으로 복원되지 않는다.
H2(검증 대상): 반복 관측은 Identity 자체가 아니라 Identity에 대한
Confidence를 증가시킨다 - 같은 실제 Topic의 새 candidate가 여러 Night
Batch에 걸쳐 반복 등장할 때, 매번 "가장 가까운 Anchor"로 뽑히는 대상이
일관되게 유지되는가?

### Data
Day1로 Anchor를 만들고, Day7/Day30 두 관측 시점에서 `compute_assignment_
matrix()`(순수 관찰)로 각 실제 Topic이 1순위로 가리키는 Anchor id를
기록, 두 시점을 비교(`experiment_temporal_consistency.py`).

### Result
일관성이 전혀 없었다 - Backend User 0/3, AI Researcher 0/2. 모든 실제
Topic이 Day7과 Day30에서 서로 다른 Anchor를 1순위로 선택했다.

### Insight
**이 실험은 H2를 기각한 게 아니라, 실험 설계 자체가 H2를 검증하지
못했다는 걸 보여준다.** Day7과 Day30은 같은 Anchor 집합을 두 번 관측한
게 아니다 - Day7 시점엔 Day1(스크랩 5개)에서 만든 극소수 Anchor만
존재했고, Day30 시점엔 그 사이 Day7 콘텐츠로 만들어진 Anchor들이 추가된
다른(더 풍부해진) Anchor 집합을 봤다. 즉 실제로 비교한 건
`Observation(t1 | AnchorSet1)` vs `Observation(t2 | AnchorSet2)`였고,
H2가 요구하는 `Observation(t1 | 같은 AnchorSet)` vs `Observation(t2 |
같은 AnchorSet)`이 아니었다 - 대상(candidate)과 기준(Anchor Set) 둘 다
고정돼야 하는데 기준이 계속 바뀌었다.

### Decision
H0(신설, RQ#7의 전제조건): "Confidence 축적은 기준이 되는 Anchor Space가
충분히 안정된 뒤에만 가능하다." Experiment #42로 Anchor Space 자체의
안정성부터 측정한다 - Candidate의 일관성을 기대하기 전에 좌표축(Anchor)
자체가 안정적인지 먼저 봐야 한다("GPS 위성이 계속 움직이는데 자동차
위치가 흔들린다고 말하는 것과 같다").

## Experiment #42: Anchor Creation Dynamics (Anchor Space Stability로 시작했으나 측정 대상이 좁혀짐)
날짜: 2026-07-19

### Hypothesis
H0: Anchor Space(Anchor 집합)가 시간이 지나며 안정화되는가(신규 Anchor
생성률이 감소하는가)?

### Data
Day1→7→30 증분 처리 중 `night_batch_anchor()`의 AttachTrace(이미 존재,
추가 계측 없음)에서 배치마다 ATTACH/CREATE 결정 수를 집계
(`experiment_anchor_space_stability.py`). Anchor의 identity_vector는
설계상 절대 불변이므로 "Anchor 이동량"은 이 구현에서 애초에 측정
대상이 아니다 - 측정 가능한 축은 생성률뿐이다.

### Result
| | Day7 신규 생성률 | Day30 신규 생성률 |
|---|---|---|
| Backend User | 0.0% | 45.5% |
| AI Researcher | 40.0% | 28.6% |

AI Researcher는 감소(안정화 방향), Backend User는 오히려 급증. 두
페르소나 모두 Day30 시점에도 상당한 비율로 여전히 새 Anchor를 만들고
있어 0%에 가까워지는 모습은 안 보였다.

### Insight
**이 실험은 "Anchor Space Stability"를 측정한다고 시작했지만, 실제로는
"Anchor Creation Rate"만 측정했다 - 이 둘은 다르다.** Anchor Creation이
많다고 곧 불안정한 게 아니다: 사용자가 정말 새 관심사(예: Backend User가
Day30에 AWS/Kubernetes/Docker를 새로 시작)를 얻었다면 새 Anchor 생성은
정상이고 오히려 기존 Anchor는 전혀 안 흔들린 안정적인 시스템일 수 있다.
반대로 Anchor 생성이 거의 없어도 기존 Anchor의 의미가 완전히 붕괴했다면
그게 더 불안정하다. **Anchor Creation Rate는 Reference Frame Stability의
충분한 proxy가 아니다** - proxy라고 가정했던 것 자체가 틀렸다.

### Decision
H0를 "기각"이 아니라 **"판정 불가(Inconclusive)"**로 기록한다 - 측정
도구(생성률)가 측정하려던 대상(안정성)을 대표하지 못했다는 게 결론이다.
Research Question #7을 둘로 분리한다: **RQ7-A("Anchor Creation은 성장
(Novel Expansion)인가 분열(Redundant Split)인가?")**와 **RQ7-B("Anchor
Assignment[ATTACH]는 안정적인가?")** - Growth와 Assignment는 독립
변수다. RQ7-A부터 Experiment #43으로 검증한다(새 Anchor 각각이 생길
당시 가장 가까웠던 기존 Anchor와의 유사도는 이미 계산되어 있으므로
추가 구현 없이 분류 가능).

## Experiment #43: Anchor Creation Classification (Novel Expansion vs Redundant Split)
날짜: 2026-07-19

### Hypothesis
RQ7-A 검증. 새로 생긴 Anchor를 두 가지로 분류할 수 있다면(ground truth
사용, offline 진단 목적 - Experiment #29/#35와 같은 성격) Experiment
#42의 높은 창조율이 정상 성장인지 회피 가능한 파편화인지 가려낼 수
있다: **Novel Expansion**(새 Anchor의 실제 주제가 가장 가까웠던 기존
Anchor의 실제 주제와 다름 - 정상) vs **Redundant Split**(같음 - 붙었어야
했는데 못 붙은 파편화).

### Data
`night_batch_anchor()`가 CREATE 결정마다 이미 남기는 AttachTrace(best_
anchor_id, best_similarity)를 활용 - 이번 실험을 위해 world.py의
`anchor_scraps_before`를 ATTACH뿐 아니라 CREATE 케이스에도 채우도록
확장했다(판단 로직은 안 바꿈, 진단 정보만 추가).
`experiment_creation_classification.py`로 모든 CREATE 이벤트를 분류.

### Result
첫 배치(비교 대상 Anchor가 아직 없음)를 제외한 CREATE 이벤트가 Backend
User 5건, AI Researcher 8건이었고, **전부 Novel Expansion으로
분류됐다 - Redundant Split은 0건**이었다.

### Insight
**증명된 것**: 이 데이터에서는 CREATE 오류(Redundant Split)가 관측되지
않았다("No redundant CREATE events were observed"). **증명 안 된 것**:
"CREATE는 본질적으로 안전하다"는 아직 과한 주장이다 - 표본이 작고
(n=13), **Precision만 확인했지 Recall은 미확인**이다:

| CREATE 판단 오류 유형 | 현재 상태 |
|---|---|
| False Positive(Redundant Split: 안 새로운데 새로 만듦) | 관측되지 않음(n=13) |
| False Negative(Novel인데 ATTACH해버림) | 미측정 |

Experiment #42의 높은 창조율(Backend 45.5%, AI Researcher 28.6%)은
회피 가능한 파편화가 아니라 정당한 신규 확장이었을 가능성이 크다. 더
중요한 발견은 원인 분리다 - Duplication의 원인이 CREATE(너무 많이
만듦)인지 ATTACH(엉뚱한 곳에 잘못 붙임)인지 갈렸던 오래된 질문에,
증거가 **ATTACH 쪽으로 강하게 수렴한다**: Experiment #29(ATTACH 정확도
5.6~23.1%)/#34(Objective 개선해도 Trade-off만 이동)/#41(같은 실제
Topic이 시점마다 다른 Anchor를 1순위로 선택)이 전부 ATTACH 쪽 문제였고,
이번 실험은 CREATE 쪽에서는 (적어도 Precision 기준) 문제를 못 찾았다.

**Reference Frame = Anchor Set + Assignment Rule**이라는 개념 분리가
이번에 생겼다 - Anchor Set(CREATE)은 잠정적으로 정상 성장으로 보이고,
Reference Frame을 흔드는 건 Anchor Set 자체가 아니라 Assignment
Rule(ATTACH가 어디에 붙일지 정하는 규칙)일 가능성이 크다.

### Decision
`docs/algorithm_limitations.md`에 **Finding #011**(Anchor Creation Is
Not the Primary Source of Duplication — Assignment Is) 신설 -
Experiment #28/#29/#34/#41/#43을 하나의 서사로 연결한다. RQ7-A는 잠정
좁혀짐(Recall 검증 남음, 완전히 닫힌 건 아님) - **RQ7-B("Anchor
Assignment는 안정적인가?")가 남은 최우선 질문**이 된다. 연구의 초점이
"Anchor를 언제 새로 만들 것인가"에서 "기존 Anchor 중 어디에 붙일
것인가"로 거의 완전히 이동한다.

## Experiment #44: Assignment Stability under Perturbation (고정 Anchor Set)
날짜: 2026-07-19

### Hypothesis
RQ7-B 검증. Experiment #41의 교란 요인(Anchor Set 자체가 관측 시점마다
달랐다)을 제거하기 위해, Anchor Set(Day1+Day7)과 클러스터링을 완전히
고정한 채 관측(embedding)만 작은 노이즈로 흔들어서, ATTACH 판단이
관측의 작은 변화에도 안 흔들리는지("brittle하지 않은지") 측정한다 -
단순히 "같은 입력을 여러 번 넣는" 설계는 결정론적 알고리즘에서
"안정성"이 아니라 "결정론성"만 확인하는 함정이 있다는 지적을 반영해서,
입력 자체를 살짝 흔드는 방식으로 설계했다.

### Data
Day1+Day7로 Anchor Set을 만들고 고정, Day30 스크랩의 클러스터링
(candidate 구성)도 한 번만 계산해서 고정(HDBSCAN 파라미터를 흔드는 건
다른 축의 실험이라 이번엔 다루지 않음 - 향후 확장 후보). 각 candidate의
관측된 embedding에 epsilon(0.02/0.05/0.10) 크기의 가우시안 노이즈를
20회(trial) 주입해서, 원본(무섭동) 1순위 Anchor와 같은 Anchor를 고르는
비율(Consistency)과 분포의 엔트로피를 측정, margin과 consistency의
상관관계도 함께 봄(`experiment_assignment_stability.py`).

### Result
epsilon 0.02/0.05에서 Consistency 100%(엔트로피 0, 완전히 안정),
epsilon 0.10에서도 99.1~99.5%. margin-consistency 상관계수는 노이즈가
커질 때만 약하게 나타남(0.2~0.34).

### Insight
Assignment는 노이즈에 전혀 브리틀하지 않다 - 매우 확정적이고 안정적
이다. 그런데 이 안정적인 판단의 정확도는 Experiment #29에서
5.6~23.1%로 매우 낮았다. **즉 Stable but Wrong이다.**

이건 Variance 문제가 아니라 Bias 문제라는 뜻이다 - Variance는 반복
관측(averaging)으로 줄어들지만, Bias는 반복해도 줄어들지 않는다.
H2("반복 관측이 Confidence를 쌓아준다")는 분산이 큰 Weak Signal을
전제로 할 때만 의미가 있는데, 지금 Assignment Signal은 Strong하지만
(분산이 거의 0) Biased(체계적으로 편향)하다 - 완전히 다른 상황이다.
**H2는 기각된 게 아니라, 현재 Assignment Signal 하에서는 애초에 적용
대상이 아니다(not applicable)** - repeated observation이 실패한 게
아니라, 이 신호가 가진 문제(체계적 편향)가 반복 관측으로 풀리는 종류의
문제가 아니라는 게 밝혀졌다.

### Decision
`docs/algorithm_limitations.md` Finding #008에 이 결과를 Additional
Evidence로 추가한다(새 Finding 신설 안 함 - Finding #008의 결론을 한
단계 더 정밀하게 만드는 확장이다): "Similarity에서 파생된 Assignment는
노이즈 많은 신호가 아니라 일관되게 잘못된 신호다." **Research Question
#7을 여기서 종료한다** - 반복 관측이 실패해서가 아니라, 반복 관측이
풀어야 할 종류의 문제가 애초에 아니었다는 게 밝혀졌기 때문이다. 다음
연구 방향은 "어떻게 더 안정적으로 판단할 것인가"에서 "무엇을 판단
신호로 쓸 것인가"로 완전히 좁혀진다 - 아직 새 질문에 정식 번호를 매기지
않는다(다음 세션에서 구체화). `docs/anchor_model.md` Research Question
#7을 Closed로 갱신.

## Research Question #8: Can Topic Identity be recovered from pairwise semantic judgment instead of independent document features?
날짜: 2026-07-19

Similarity/Tag/Graph/반복관측까지 실패한 신호들은 전부 "문서 하나(또는
그 문서에서 독립적으로 계산 가능한 property)"였다. 후보 셋(출처
메타데이터, Pairwise LLM Judgment, 사용자 피드백 루프) 중 **Pairwise
LLM Judgment**를 선택 - 문서 A/B를 동시에 보여주고 "같은 구체적 주제를
다루는가"를 직접 점수로 받는 방식으로, 신호의 단위가 Document
Property가 아니라 Document Relation이라는 점에서 질적으로 다르다.
ai_rules.md Rule 1과도 충돌 안 함(AI는 관계 점수만 제공, 최종 결정은
threshold로 알고리즘이 함).

## Experiment #45: Pairwise LLM Judgment - Signal Existence Test
날짜: 2026-07-19

### Hypothesis
"Pairwise LLM score가 Anchor Model에 넣으면 품질이 좋아지는가"는 너무
큰 질문이다. 먼저 아주 작게: **LLM Pairwise Score가 실제로 같은 Topic과
다른 Topic을 갈라내는가?**만 확인한다. Anchor/CREATE/ATTACH는 전혀
안 쓴다.

### Data
AI Researcher에서 9개 Topic에 걸쳐 18개 스크랩을 층화 표집(topic당
약 2개), 153쌍 전부에 `OpenAIPairwiseJudge`(`pairwise_judge.py`, 신설)
로 0~1 점수를 매기고, 같은/다른 Topic 쌍으로 나눠 비교(ROC-AUC 포함,
`experiment_pairwise_llm_judgment.py`).

### Result
같은 Topic 쌍(n=9) mean=0.289, 다른 Topic 쌍(n=144) mean=0.010 - 차이
+0.279, **ROC-AUC 0.820**. 지금까지 시도한 신호(Direct Similarity
+0.026~0.047, Freeform Tag +0.011, Tag Graph 거의 0)보다 압도적으로
강하다.

### Insight
처음으로 뚜렷한 긍정적 신호다. 다만 표본이 극히 작다(같은 Topic 쌍
n=9) - "LLM이 Topic Identity를 복원했다"가 아니라 "관계를 직접 물어보면
독립 신호들보다 훨씬 많은 정보를 제공한다"까지만 증명됐다는 걸 명확히
구분한다. Document Property 계열(Similarity/Tag/Graph)은 전부 실패했고
Document Relation은 처음으로 성공 신호를 보였다는 게 핵심 구도다.

### Decision
표본을 늘리기 전에 **무엇 때문에 성공했는가**부터 확인한다
(Experiment #46) - LLM이 진짜 개념을 이해해서 맞췄는지, 단순히 표면적
단어 일치에 의존했는지 구분하지 않으면 이 신호를 신뢰할 수 없다.

## Experiment #46: Pairwise LLM Judgment Error Analysis
날짜: 2026-07-19

### Hypothesis
경계 사례(같은 Topic인데 낮은 점수 - False Negative 후보, 다른 Topic
인데 상대적으로 높은 점수 - False Positive 후보)를 골라서 LLM에게
점수와 함께 근거(rationale)를 받아 사람이 직접 분류한다: Type
A(Genuine Semantic) / Type B(Lexical Shortcut) / Type C(우연/오류).

### Data
같은 Topic·낮은 점수 3건, 다른 Topic·상대적으로 높은 점수 7건을
골라 재질의(score+reason 형식)해서 근거를 확인
(`experiment_pairwise_error_analysis.py`).

### Result
검토한 10건 전부 **Type A**였다 - Type B/C는 하나도 없었다. 다만
패턴이 하나 드러났다: 같은 Topic인데 낮은 점수를 받은 쌍은 전부
"Transformer 안의 Sliding Window Attention vs Layer Normalization"처럼
**같은 Topic 안의 서로 다른 구체적 메커니즘**이었고, 다른 Topic인데
상대적으로 높은 점수를 받은 쌍은 대부분 "Evaluation"처럼 여러 Topic에
걸쳐 적용되는 범주 개념이 낀 경우였다.

### Insight
이건 LLM의 오류가 아니라 **Virtual Dataset의 ground truth Topic 라벨이
단일 해상도가 아니라는 것**을 드러낸다 - "Transformer"라는 라벨 하나가
여러 구체적 하위 메커니즘을 뭉뚱그리고 있고, LLM은 "같은 상위 Topic"과
"같은 구체적 메커니즘"을 정확히 구분해서 판단하고 있었다.

### Decision
Experiment #47로 이 관찰을 정량화한다 - 표본을 5배로 늘리는 동시에,
각 pair를 Case A(같은 Topic+같은 mechanism)/B(같은 Topic+다른
mechanism)/C(다른 Topic)로 라벨링해서 mean score를 따로 비교한다.

## Experiment #47: Pairwise LLM Judgment at Scale, with Granularity Labels
날짜: 2026-07-19

### Hypothesis
Case A/B/C 각각의 점수 분포가 계단식으로 갈린다면(A > B > C), "LLM이 판단을
못 한다"가 아니라 "ground truth Topic 라벨 자체가 여러 해상도를 섞고
있다"는 게 정량적으로 증명된다.

### Data
필자가 AI Researcher 71개 스크랩 전체를 읽고 mechanism sub-label을
직접 주석(원 데이터셋 설계자가 정한 게 아님 - 이 실험만을 위한 주석,
주관 개입 가능성 있음). Case A 쌍(같은 mechanism)이 최소 1개씩 보장되게
36개 스크랩을 표집(topic당 최대 4개, Case A 쌍은 무조건 포함), 630쌍
전부 채점(`experiment_pairwise_granularity.py`).

### Result
| Case | 설명 | n | mean score |
|---|---|---|---|
| A | 같은 Topic + 같은 mechanism | 6 | 0.483 |
| B | 같은 Topic + 다른 mechanism | 48 | 0.135 |
| C | 다른 Topic | 576 | 0.006 |

전체 ROC-AUC(같은 Topic 여부 기준)는 0.820(n=9)에서 **0.730**(n=54)으로
재확인됐다 - 표본이 커지며 낙관적 초기 추정이 다소 낮아졌지만 여전히
견고한 분리력이다.

### Insight
계단식 분리(0.483 → 0.135 → 0.006)가 뚜렷하다. 이건 "Ground Truth가
이상하다"는 부정적 결론이 아니라, **Pairwise LLM Judgment가 Topic
label보다 세밀한 semantic unit(mechanism)을 실제로 반영하고 있다**는
긍정적 증거다 - LLM의 semantic resolution이 Virtual Dataset의
resolution보다 높다.

### Decision
`docs/algorithm_limitations.md`에 **Finding #012**(Pairwise LLM
Judgment Reflects a Finer Semantic Unit Than the Topic Label) 신설.
다음은 "좋은 신호인가"가 아니라 **"좋은 신호가 실제 시스템(Purity/
Duplication)을 개선하는가"**를 검증한다(Experiment #48) - 지금까지의
연구에서 처음으로 신호 품질이 아니라 시스템 품질을 검증하는 실험.

## Experiment #48: LLM-Reranked Attach - Does the Signal Improve System Quality?
날짜: 2026-07-19

### Hypothesis
LLM을 검색기가 아니라 **reranker**로만 쓴다(비용 폭발 방지 + Rule 1
유지): 기존 cosine으로 top-3 Anchor 후보를 뽑고(Recall), 그 top-3만
Pairwise LLM Judgment로 재점수화해서 최종 Attach 여부를 결정한다
(Precision). Control(기존 cosine attach, Experiment #28과 동일)과
Treatment(LLM rerank)를 같은 방법론(Day1→7→30, Topic Purity/
Duplication Rate)으로 직접 비교한다. world.py는 안 건드림(순수 실험
스크립트, `experiment_llm_rerank_attach.py`).

### Data
llm_threshold를 0.2/0.3/0.4로 스윕, cosine attach_threshold=0.30(기존
baseline)은 고정.

### Result
| | Control(Cosine) | Treatment(LLM Rerank, threshold=0.3) |
|---|---|---|
| Backend Purity | 0.437 | **0.845** |
| Backend Duplication | 66.7% | 66.7%(동일) |
| Backend Island 수 | 10 | **23**(2.3배) |
| AI Researcher Purity | 0.437 | **0.761** |
| AI Researcher Duplication | 88.9% | 88.9%(동일) |
| AI Researcher Island 수 | 13 | **27**(2배) |

Purity는 두 페르소나 모두 극적으로 개선됐지만, Duplication은 전혀
개선 안 되고 Island 수가 2~2.3배로 폭증했다.

### Insight
LLM Rerank가 실패한 게 아니라 **매우 잘 동작했다** - 다만 LLM이 맞게
판단한 대상(Mechanism)과 우리가 평가하는 대상(Topic)이 다르다.
Experiment #47의 Case A(0.483)/B(0.135) 격차 때문에, llm_threshold
(0.2~0.4)는 Case A(같은 mechanism)는 통과시키지만 Case B(같은 Topic,
다른 mechanism)는 대부분 통과 못 시킨다 - 그 결과 각 Island는 내부적
으로 매우 순수해지지만(Mechanism 단위로 쪼개져서), Topic 단위 중복은
그대로 남는다.

### Decision
threshold를 바로 조정하지 않는다 - Experiment #49로 Case B와 Case C의
점수 분포가 실제로 겹치는지부터 확인한다(겹치면 threshold 튜닝으로는
근본적으로 해결 안 됨).

## Experiment #49: Score Distribution Overlap Analysis (Case A/B/C)
날짜: 2026-07-19

### Hypothesis
Case B와 Case C의 점수 분포가 많이 겹친다면 threshold를 아무리
조정해도 해결 안 되고(Signal Separability 문제), 의외로 분리돼
있다면 threshold sweep이 의미 있다.

### Data
Experiment #47에서 이미 계산된 캐시를 재사용(새 API 호출 없음) -
Case A/B/C 각각의 전체 점수 분포(히스토그램 수준)를 직접 확인.

### Result
Case A(n=6): [0.0, 0.2, 0.3, 0.6, 0.9, 0.9]. Case B(n=48): 0.0이 27개,
0.2가 11개, 0.3이 7개, 0.6~0.8이 3개. Case C(n=576): 0.0이 561개,
0.2가 13개, 0.3/0.7이 1개씩. **score=0.2 지점에서 Case B(11개)와 Case
C(13개)의 절대 개수가 거의 같다** - Case C의 모수(576)가 워낙 커서
비율로는 작아도(2.6%) 절대 개수로는 Case B와 맞먹는 노이즈가 된다.

threshold=0.2 기준(A∪B="같은 Topic"=54쌍 vs C="다른 Topic"=576쌍)으로
계산하면: **Recall 48%(26/54), Precision 63%(26/41)**.

### Insight
Case B와 Case C는 완전히 분리되지도, 완전히 겹치지도 않는다 -
**부분적으로 겹친다.** 이게 Experiment #48의 결과(Recall 부족으로
Duplication 개선 실패)를 정량적으로 설명한다 - threshold=0.2에서도
Recall이 48%뿐이라 진짜 같은 Topic인 candidate 중 절반 이상이 여전히
새 Anchor로 빠졌다. **threshold를 어디에 두어도 Precision↑/Recall↓
또는 Precision↓/Recall↑로 이동할 뿐 - 이건 threshold 최적화 문제가
아니라 Signal Separability 문제다.**

### Decision
`docs/algorithm_limitations.md`에 **Finding #013**(Semantic Resolution
Mismatch) 신설 - threshold sweep은 하지 않는다("threshold를 더
튜닝하면 해결된다"는 가능성을 이 정량적 근거로 닫는다). Experiment
#45~49를 하나의 연구 축으로 마무리하고, Research Question #8에
답한다: **부분적으로 그렇다(Mechanism 수준에서는 강한 신호, Topic
수준 직접 대체는 안 됨).** Research Question #9 신설: "Topic이라는
것은 애초에 pairwise semantic judgment만으로 정의될 수 있는
대상인가?" - `docs/anchor_model.md` 갱신.

## Experiment #50: Topic-level Prompt Judgment - Prompt Objective의 통제 실험
날짜: 2026-07-19

### Hypothesis
Finding #013의 가장 큰 대안 설명(Prompt Artifact)을 제거한다 -
Experiment #45의 프롬프트가 "같은 상위 분야라는 이유만으로 높은 점수를
주지 말 것"을 명시했으므로, LLM이 Mechanism 수준으로 판단한 게 LLM의
능력 한계가 아니라 그렇게 물어봤기 때문일 수 있다. 딱 하나만 바꾼다 -
프롬프트.

### Data
Experiment #47과 완전히 같은 pair(같은 36개 스크랩, 같은 Case A/B/C
분류)에 정반대 지시("구체적 기법이 달라도 같은 상위 주제면 높은
점수를 줘라")를 담은 Topic Prompt로 다시 점수를 매기고, 핵심 지표로
**Δ = score_topic - score_mechanism**을 Case별로 비교
(`pairwise_judge.py`에 mode 파라미터 추가, `experiment_topic_prompt_judgment.py`).

### Result
| Case | mean mechanism_score | mean topic_score | mean Δ |
|---|---|---|---|
| A | 0.483 | 0.875 | +0.392 |
| B | 0.135 | 0.704 | **+0.569** |
| C | 0.006 | 0.262 | +0.256 |

전체 ROC-AUC가 **0.730 → 0.944**로 크게 개선됐다. Δ가 Case B에서
가장 컸다(+0.569 > A +0.392 > C +0.256) - Case C도 어느 정도 올랐지만
(topic이라는 개념 자체가 mechanism보다 넓으므로 자연스러운 현상) A·B
만큼은 아니다.

### Insight
Finding #013의 원인이 "LLM의 semantic prior 한계"가 아니라 **"Prompt
Objective가 Mechanism 수준을 요구했기 때문"**이라는 강한 증거다 - 같은
LLM, 같은 pair, 같은 데이터에서 프롬프트만 바꿨는데 AUC가 이만큼
뛰었다는 건 LLM capability가 아니라 Objective가 바뀐 것이다.

### Decision
아직 Finding으로 승격하지 않는다 - 지금은 offline 신호만 좋아졌을
뿐, 실제 attach 품질(Purity/Duplication)까지 좋아졌는지는 확인 안
됐다. Research Insight로 잠정 기록하고, Experiment #48을 Topic
Prompt로 재실행해서 실제 시스템 품질까지 개선되는지 확인한다
(Experiment #51).

## Experiment #51: LLM-Reranked Attach, Topic Prompt로 재실행
날짜: 2026-07-19

### Hypothesis
Experiment #50의 offline 신호 개선(AUC 0.730→0.944)이 실제 시스템
품질(Purity/Duplication/Island 수)에도 이어지는가? Experiment #48과
완전히 같은 설계(cosine top-3 → LLM rerank)에서 mode만
"mechanism"→"topic"으로 바꾼다.

### Data
`experiment_llm_rerank_attach.py`의 `run_llm_rerank`에 mode/cache_path
파라미터를 추가해서 재사용, `experiment_llm_rerank_attach_topic.py`
(Experiment #51)로 Topic Prompt 점수 분포(Case A 0.875/B 0.704/C
0.262, Experiment #50)에 맞춰 llm_threshold를 0.4/0.5/0.6으로 조정해서
Control(cosine)과 비교.

### Result
| | Control(Cosine) | Treatment(Topic Prompt, threshold=0.5) |
|---|---|---|
| Backend Purity | 0.437 | 0.761 |
| Backend Duplication | 66.7% | **44.4%(개선)** |
| Backend Island 수 | 10 | 17 |
| AI Researcher Purity | 0.437 | 0.704 |
| AI Researcher Duplication | 88.9% | **100.0%(악화)** |
| AI Researcher Island 수 | 13 | 23 |

Backend User는 Purity·Duplication이 동시에 개선됐다(사용자가 예상한
"시나리오 1"). AI Researcher는 반대로 Duplication이 오히려
악화됐다(88.9%→100%) - Mechanism Prompt(Experiment #48)보다도
나쁘다.

### Insight
Topic Prompt가 "정답"이 아니라, 도메인마다 반응이 갈린다. Backend의
실제 Topic들(Redis/Kafka/Spring/Docker)은 기술적으로 서로 뚜렷이
구분되는 semantic gap이 큰 도메인이라 해상도를 넓혀도(Topic Prompt)
잘 안 섞인다. 반면 AI Researcher의 실제 Topic들(RLHF/Fine-tuning/
Prompt Engineering/Agent/Transformer)은 전부 "LLM 연구"라는 하나의
큰 의미공간 안에 밀집해 있다(Finding #008의 원래 예시와 정확히
같은 구조) - Topic Prompt로 해상도를 넓히면 LLM이 "다 같은 LLM
연구잖아"라고 보는 게 오히려 자연스러운 반응이 된다. **LLM이 틀린 게
아니라, Topic label이 요구하는 해상도보다 한 단계 위에서 판단한
것이다.**

### Decision
Finding #013을 수정한다 - Claim을 "Semantic Resolution Mismatch"에서
**"Judgment Resolution Must Match the Evaluation Resolution"**으로
재구성(Experiment #50이 원인을 Prompt Objective로 좁힘). 그 위에
`docs/algorithm_limitations.md`에 **Finding #014**(Optimal Semantic
Resolution Is Domain-dependent) 신설 - "적정 해상도"가 고정 상수가
아니라 도메인의 semantic density에 따라 달라진다는 게 이번 실험의
핵심 결론. Research Question #9에 답한다: **"Pairwise semantic
judgment is sufficient to recover Topic Identity, but only when the
semantic resolution of the judgment matches the semantic density of
the target domain."** Adaptive Resolution(도메인마다 해상도를
자동으로 맞추는 방향)은 백로그로 남기고 지금 실험하지 않는다 -
Research Question #9는 여기서 종료한다. `docs/anchor_model.md` 갱신.

---

## Research Phase 1: Complete

RQ0~RQ9, Finding #001~#014 요약은 `docs/research_phase_1_summary.md` 참고.

## Research Phase 2

## Research Question 10-0: Does semantic resolution exist independently of the measurement method?

RQ10-0의 이론적 정의(H1 Tree/H2 Metric/H3 Graph, observable predictions,
evaluation strategy)는 `docs/research_phase_2_rq10-0.md`에 별도 문서로
관리한다.

## Experiment #52: RQ10-0 Stage A/B — Measurement Invariance & Latent Geometry

### Hypothesis
H1/H2/H3 각각의 observable prediction(`docs/research_phase_2_rq10-0.md`
참고)이 관측 데이터와 얼마나 맞는지 본다. Stage A는 세 measurement
modality(embedding cosine, LLM Mechanism 프롬프트, LLM Topic 프롬프트)
간 구조 일치도로 "Resolution이 측정 독립적인가"를 먼저 검사하고, Stage
B는 그 위에서 각 modality가 Tree(H1)에 가까운지 Metric(H2)에 가까운지
본다.

### Data
AI Researcher curated sample 36개(Experiment #47/#50과 동일 표본,
seed=7). Mechanism/Topic judgment 점수는 기존 캐시
(`pairwise_judgment_cache.json`, `pairwise_judgment_topic_cache.json`)
재사용, embedding은 신규 계산(36건, pairwise가 아니라 O(n)이라 저렴,
`resolution_ontology_embedding_cache.json`에 캐시). 새 LLM judgment
호출 없음.

### Result
**Stage A (odd-one-out agreement / Kendall's τ, 우연 수준 33.3%)**:
Embedding vs Mechanism 39.9%/0.202, Embedding vs Topic 51.0%/0.274,
Mechanism vs Topic 65.4%/0.457 — 세 쌍 다 우연보다 높지만 균일하지
않음.

**Stage B (ultrametric violation / cophenetic avg,ward / MDS stress)**:
Embedding 53.0%/0.708,0.585/40.17, Mechanism 0.8%/0.921,0.595/86.86,
Topic 21.5%/0.769,0.727/32.99.

### Insight
Resolution은 completely measurement artifact도 아니고 completely
objective도 아니다("partial measurement invariance"). Mechanism
프롬프트는 강하게 Tree처럼 행동하고(거의 완벽한 ultrametric, 그러나
저차원 거리공간으로는 안 펴짐), Embedding은 Tree도 Metric도 아니다
(Finding #008의 기하학적 재확인). 즉 지금 관측된 차이는 Tree/Metric/
Graph 세계관의 경쟁이라기보다 **측정 방법이 서로 다른 기하학을
유도한다**는 사실로 대부분 설명된다. H3(Graph)는 기각되지 않았지만
현재 데이터를 설명하는 데 필수적이지도 않다.

### Decision
`docs/research_phase_2_rq10-0.md`에 Stage A/B 결과와 Interim
Conclusion("Different measurement methods do not observe the same
latent geometry...")을 기록. H3는 "viable하지만 현재 불필요"로 보류.
다음 실험으로 새 하위 질문 **"Mechanism Tree Effect: Prompt Artifact
or Model Prior?"**를 정의 — Mechanism 프롬프트의 Tree-like 행동이
prompt wording의 인공물(M1)인지 LLM 내재 구조(M2)인지, 같은 pair에
새 프롬프트(Neutral/Relation)만 바꿔서 같은 Stage B 지표로 비교.

## Experiment #53: Mechanism Tree Effect — Prompt Artifact(M1) or Model Prior(M2)?

### Hypothesis
M1(Prompt Artifact): "같은 구체적 개념/기법인가"라는 위계적 판단을
강제하는 prompt wording 자체가 Tree 구조를 만든다 - prompt에서 그
요구를 빼면 Tree-likeness가 무너진다. M2(Model Prior): LLM의 semantic
knowledge 자체가 hierarchical하다 - prompt를 바꿔도 Tree-likeness가
유지된다.

### Data
Experiment #52와 동일한 36개 curated sample, 동일한 630개 pair.
`pairwise_judge.py`에 새 프롬프트 두 개 추가 - Neutral("두 문서가
얼마나 밀접하게 관련되어 있는가", 위계 판단 요구 안 함), Relation("동일한
주제가 아니어도 좋다, 연구자 입장에서 함께 공부할 가치가 있는가").
630쌍 × 2 프롬프트 = 1260건 신규 LLM 호출(백그라운드 실행).

### Result
| Modality | Ultrametric violation | Cophenetic(avg/ward) | MDS stress |
|---|---|---|---|
| Mechanism | 0.8% | 0.921 / 0.595 | 86.86 |
| Neutral | 56.6% | 0.743 / 0.683 | 34.45 |
| Relation | 55.2% | 0.562 / 0.495 | 10.54 |

"같은 구체적 기법인가"라는 요구를 빼자 Tree 적합도가 붕괴(violation
0.8%→55~57%, cophenetic 0.921→0.5~0.7대), 동시에 MDS stress는
86.86→34.45→10.54로 단조 감소(저차원 연속 공간에 더 매끈하게 펴짐).
Neutral(violation 56.6%, MDS stress 34.45)은 Experiment #52의
Embedding(53.0%, 40.17)과 상당히 근접.

### Insight
M1이 M2보다 현재 가장 설명력이 높은 가설이다. 더 큰 발견은 M1/M2
판정 자체가 아니라 **prompt objective가 관측 가능한 semantic geometry
자체를 선택(construct)한다**는 것 - Hierarchical 프롬프트는 Tree를,
Relational 프롬프트는 연속적인 relatedness space를 복원한다. Neutral과
Embedding의 유사한 프로파일은 Finding #008(Similarity는 Relatedness를
포착하지 Identity는 아니다)을 다른 방식으로 재확인한다. Backend User
데이터셋에서의 재현은 지금 당장 핵심 증거로 필요하지 않다(같은 데이터·
같은 LLM에서 prompt만 바꿔 geometry가 바뀌었다는 것 자체가 이미
인과적) - replication으로 나중에 남겨둔다.

### Decision
`docs/research_phase_2_rq10-0.md`에 **Finding P2-001**(Prompt
Objectives Determine the Observable Semantic Geometry) 기록. RQ10-0의
Interim Conclusion을 "Different measurement methods do not observe
the same latent geometry"에서 **"Different measurement methods
actively select different latent geometries to observe"**로 강화.
새 Open Question 기록(아직 실험 설계 전): Mechanism 프롬프트가 만든
Tree가 사용자가 실제로 느끼는 "관심사 구조"와 일치하는가, 아니면
프롬프트가 만들어낸 구조일 뿐인가 - Phase 1의 Purity vs UX 간극과
같은 축.

## Phase 2 Reframed: Adaptive Resolution → Semantic Objective Discovery

Experiment #52~53 결과를 종합한 뒤, Phase 2의 틀 자체를 재구성했다.
Resolution이 독립적인 값이 아니라 semantic objective(비교 질문 자체)의
결과물이라는 게 드러나면서, 원래 질문("해상도를 도메인마다 어떻게
자동으로 맞출 것인가")이 한 단계 더 상위 질문에 종속된다는 게 밝혀졌기
때문이다. RQ10-0("Does semantic resolution exist independently of the
measurement method?")은 **🟡 Provisionally Answered**로 표시(AI
Researcher 데이터셋 1개, 모델 1개 기준 - Backend User 등 다른 도메인
에서 반증되면 재검토). 새 하위 질문 **RQ10-1**을 정의: "Which semantic
objective best predicts human organizational behavior — and does that
answer itself vary by domain or user?" - Finding #014(적정 해상도는
도메인마다 다르다)의 교훈을 이어받아 "고정된 하나의 정답 Objective가
있다"는 전제로 퇴행하지 않도록 질문에 도메인/사용자 의존성을 처음부터
포함시켰다. Candidate Objectives를 Observed(Mechanism/Topic/
Relatedness - 이미 프롬프트로 간접 테스트됨)와 Speculative(Learning
dependency/Task substitutability/Temporal co-occurrence/User
navigation - 완전 미탐색, User navigation은 현재 Virtual User Dataset
스키마에 없는 행동 로그가 필요) 두 그룹으로 구분해 기록.
`docs/research_phase_2_rq10-0.md`에 "Why was Phase 2 reframed?" 절과
Revision History(Adaptive Resolution → Semantic Objective Discovery)
추가, `docs/algorithm_limitations.md` 포인터도 갱신.
`docs/research_phase_1_summary.md`는 Phase 1 종료 시점의 스냅샷이라
수정하지 않는다 - Adaptive Resolution이 Phase 2의 최초 가설이었다는
역사적 기록 자체가 가치 있다.

## Experiment #54: RQ10-1 Probe 0 — Existing Topic Reconstruction

### Hypothesis
이 Probe가 실제로 답하는 질문은 "어떤 semantic objective가 기존 Topic
레이블을 가장 잘 복원하는가"이지, "어떤 objective가 실제 사용자 조직
방식을 반영하는가"(RQ10-1의 질문)가 아니다 - ground truth가 여전히
가상 데이터셋의 수작업 Topic 레이블이기 때문. RQ10-1의 첫 실험이
아니라 RQ10-0을 닫는 마지막 sanity check로 위치시킨다.

### Data
Experiment #47/#50/#52/#53과 동일한 36개 curated sample, 동일한 630개
pair. Mechanism/Topic/Neutral/Relation 네 캐시 전부 재사용 - 새 LLM
호출 없음.

### Result
| Objective | ROC-AUC | Precision@0.5 | Recall@0.5 | F1@0.5 | Cohen's d |
|---|---|---|---|---|---|
| Mechanism | 0.730 | 0.857 | 0.111 | 0.197 | 2.037 |
| Topic | 0.944 | 0.490 | 0.870 | 0.627 | 3.242 |
| Neutral | 0.922 | 0.494 | 0.741 | 0.593 | 2.586 |
| Relation | 0.893 | 0.124 | 1.000 | 0.220 | 1.334 |

두 층으로 읽는다 - Layer 1(Ranking, AUC): Topic≈Neutral(0.944/0.922,
차이 0.022로 36개 표본 수준에서 강하게 구분 어려움) >> Relation(0.893)
>> Mechanism(0.730). Layer 2(Calibration, Precision/Recall@0.5):
Mechanism은 매우 보수적, Relation은 매우 관대, Neutral/Topic은 중간 -
AUC는 순위 능력을, Precision/Recall은 채점기의 관대함/보수성을 본다.

### Insight
핵심은 "Topic이 이겼다"가 아니라 "Neutral이 거의 다 했다"는 것 -
아무 위계/주제 프레이밍도 요구하지 않은 Neutral이 0.922를 기록했다는
건, 이 가상 데이터셋의 Ground Truth Topic 레이블이 Hierarchy보다
General Relatedness에 훨씬 가까운 정의로 만들어졌을 가능성을 시사한다.
Mechanism 최하위는 Tree geometry가 틀렸다는 뜻이 아니다 - Precision은
높고(0.857) Recall만 낮아서(0.111), Tree의 분기가 Topic 레이블보다 더
세밀했을 가능성이 높다(resolution mismatch, Tree geometry 자체의
기각이 아님).

### Decision
`docs/research_phase_2_rq10-0.md`에 "Probe 0: Existing Topic
Reconstruction"을 RQ10-0 Stage A/B/Experiment #53 다음, RQ10-1 앞에
배치 - RQ10-1의 첫 실험이 아니라 RQ10-0의 마지막 조각으로 기록. RQ10-0
Interim Conclusion을 Probe 0까지 반영해서 재작성. RQ10-1 섹션에는
Probe 0의 Topic≈Neutral 근접이 "실제 사용자 데이터로 검증해야 할 첫
단서"라는 연결 문장 추가.

## Experiment #55: RQ10-0 Probe 0 Replication on Backend User

### Hypothesis
Probe 0(Experiment #54)은 AI Researcher 데이터셋 하나에서만 나온
결과다 - "Topic ≈ Neutral"이 도메인 고유 현상인지 일반적인 현상인지
확인한다. 같은 평가 체계·같은 파이프라인으로 도메인만 바꾼다
(replication study). Mechanism 축은 뺀다 - Backend에는 mechanism
주석이 없고, 지금 확인하려는 건 Mechanism이 아니라 Topic≈Neutral의
일반성이기 때문(Topic/Neutral/Relation 세 objective만).

### Data
Backend User 71개 중 단순 topic별 무작위 샘플링(mechanism 주석이
없어 `curated_sample` 대신 `simple_per_topic_sample` 사용, seed=7,
per_topic_cap=4) → 36개, 630개 pair. Topic/Neutral/Relation 세
캐시에 신규 LLM 호출(백그라운드 실행).

### Result
| Objective | AI Researcher (AUC) | Backend (AUC) |
|---|---|---|
| Topic | 0.944 | 0.923 |
| Neutral | 0.922 | 0.950 |
| Relation | 0.893 | 0.935 |

순위는 뒤집혔다(AI Researcher: Topic>Neutral>Relation, Backend:
Neutral>Relation>Topic) - 그러나 범위는 두 도메인 모두 0.89~0.95로
좁다. Backend는 세 objective 모두 Precision@0.5가 AI Researcher보다
높음(Calibration이 더 타이트, Finding #014와 일관).

### Insight
"누가 1등이냐"는 재현되지 않았지만 "셋 다 거의 비슷하게 잘 된다"는
재현됐다 - Topic/Neutral/Relation을 경쟁하는 objective가 아니라 같은
**Measurement Family**(Semantic Relatedness)로 묶는 게 더 정확하다.
두 도메인 모두에서 이 셋 사이의 격차보다 이 셋 전체와 Mechanism
사이의 격차가 훨씬 크다 - Mechanism만 별도 family(Hierarchical
Decomposition)로 보인다. Finding P2-001을 "Prompt wording이
geometry를 고른다"에서 "Measurement family가 geometry를 고른다"로
정교화한다(family 안에서는 프롬프트 문구가 달라도 geometry가 거의
같음).

### Decision
RQ10-0을 🟡 Provisionally Answered → **🟢 Strongly Supported**로
상향(AI Researcher + Backend 두 데이터셋 재현). 단 "Mechanism이 정말
독립된 family인가"는 Experiment #53 하나·단일 데이터셋에서만 나온
결과라 🟡 Provisionally Answered로 별도 유지 - RQ10-0 판정이 균일하지
않음을 명시. `docs/research_phase_2_rq10-0.md`에 "Measurement
Families" 절 신설, 상태 표기 체계에 🟢 Strongly Supported 티어 추가
(✅/🟢/🟡/🔄 네 단계), RQ10-1의 Candidate Objectives를 family 단위로
재구성.

## RQ10-0 Closed (for now), Research Focus Shifts to RQ10-1

Mechanism family의 Backend 교차검증(1번 옵션, mechanism 주석 신규
작업 필요) 대신 RQ10-1 착수(2번 옵션)를 선택했다 - "미루는" 게 아니라
연구 프로그램을 분리하는 결정이다. Mechanism Backend 검증은 여전히
RQ10-0의 연장 질문이고, 지금 연구 전체의 병목은 더 이상 거기가
아니다. RQ10-0은 🟢 Strongly Supported로 닫되, `docs/research_phase_2_
rq10-0.md`에 **Known Limitation**을 명시(Mechanism family has only
been validated on AI Researcher, cross-domain validation remains
future work). Mechanism Backend 검증을 지금 안 하는 이유: RQ10-1이
Ground Truth 자체("Topic 레이블 = 실제 관심사 조직"이라는 가정)를
재정의할 수 있는데, 그러면 Mechanism을 평가하는 기준도 바뀐다 - 지금
Topic 레이블 기준으로는 Mechanism의 Recall이 낮았지만(Probe 0), 새
Ground Truth에서는 오히려 더 나은 objective가 될 수도 있다. 순서를
뒤집는 게 비용 대비 정보 이득이 크다 - 필요해지면 RQ10-1 도중에
재방문.

RQ10-1의 프레이밍을 명확히 한다: "어떤 Objective가 맞는가"가 아니라
**"무엇을 정답으로 삼을 것인가"**가 핵심 전환이다. Phase 1 내내, Phase
2 전반부(Stage A/B, Experiment #53, Probe 0, #55)까지도 계속 Topic
레이블을 Ground Truth로 신뢰해왔다 - RQ10-1은 처음으로 **Topic labels
≠ Human organization**일 수 있다는 가능성 자체를 연구 대상으로 삼는다.
`docs/research_phase_2_rq10-0.md`에 "Ground Truth Redesign이 RQ10-1의
첫 하위 과제"라는 절 추가 - 아직 이론도 실험 설계도 없다, 다음 세션의
출발점.

## RQ10-1 Ground Truth Redesign: Stage 0/1/2 설계 확정

네 가지 후보(Self-consistency re-labeling, Multi-rater agreement,
Task-oriented retrieval grouping, 실제 사용자 데이터) 중 실제 사용자
데이터를 중심에 두고 나머지 셋은 보조 검증으로 쓰기로 결정 - RQ10-1이
묻는 게 "더 좋은 레이블을 만들 수 있는가"가 아니라 "Human organization
이 실제로 존재하는 측정 대상인가"이기 때문에, 앞의 셋은 여전히
시뮬레이션(같은 모델의 자기 일관성, LLM끼리의 공유된 편향)에 갇혀
있다는 게 이유. 지금까지 "Virtual User → Ground Truth → Evaluation"
이었던 방향이 "Real User → Organization → Ground Truth"로 뒤집힌다.

새로 열린 질문: 관심사 조직은 taxonomy(분류 체계)가 아니라
workflow(용도) 기준일 수도 있다(Redis/Kafka/RabbitMQ를 "Message
Queue"로 묶는 사람도 "Backend Interview 준비"로 묶는 사람도 둘 다
틀리지 않음) - Phase 1/Phase 2 전반부가 "정확한 Topic을 찾는 연구"
였다면 여기서부터는 "무엇을 정답으로 볼 것인가를 정의하는 연구"로
성격이 바뀐다.

Stage 0(Real Human Organization Collection) → Stage 1(Measurement
Families가 이 실제 Ground Truth를 얼마나 설명하는지 평가) → Stage
2(아무 objective도 못 설명하면 새 objective 고민)로 설계.
`experiments/real_user_organization/round1.json` 스캐폴드 생성 -
scraps는 평소에 발견할 때마다 채우고, 20~30개 모이면 자유롭게
그룹화(카테고리 사전 지정 없음, 그룹 이름/이유 기록, 중복 소속
허용). 이 파일은 사용자의 실제 개인 관심사 데이터라 `.gitignore`에
추가(레포가 나중에 Public 전환 예정) - 로컬에만 존재, 커밋 안 함.

`docs/research_phase_2_rq10-0.md`에 "Ground Truth Redesign 설계" 절
추가. 데이터 수집은 비동기로 진행 - 다음 세션은 이 수집이 얼마나
됐는지 확인하는 것부터 시작.

## Stage 0 완료: 실제 스크랩 25개 수집 + 그룹화

사용자가 `scraps.txt`에 실제 URL 25개 + 저장 이유를 채움(다양한
도메인 - 백엔드 면접, 프로그래밍, 야구, 여행, 건강, 투자, 쇼핑 등
섞여 있음). `round1.json`으로 옮기면서 각 URL의 실제 내용을 WebFetch/
WebSearch로 가져와 150~300자 content_summary로 요약 - personal_reason
(원래 저장 이유)과는 분리해서 별도 필드로 보존(Stage 1에서 "내용만"
vs "내용+저장 이유" 비교 실험을 위해). naver blog·namu.wiki 대부분이
WebFetch를 차단해서: 25개 중 9개 원문 직접 fetch, 15개 검색 스니펫
대체, 1개(정보처리기사 필기, s8) 완전 실패 - fetch_status로 품질 표시,
지어내지 않고 note만 남김.

사용자가 직접 25개를 13개 그룹으로 자유롭게 묶음(6개는 단독 항목).
결과가 흥미로움 - 내용상 관련 있어 보이는 것들(예: s8 정보처리기사와
s1/s2 백엔드 면접, 둘 다 CS 관련)을 목적 기준으로 쪼갬(자격증 공부 vs
면접 대비 vs 일반 공부), taxonomy가 아니라 workflow로 조직하는
사례가 실제로 관측됨.

`docs/research_phase_2_rq10-0.md`의 Stage 0을 "완료"로 갱신, 데이터
품질 요약(9/15/1) 기록. `round1.json`은 개인 데이터라 로컬에만 존재
(git에는 포함 안 됨). 다음은 Stage 1(Measurement Families로 이
Ground Truth 설명력 평가) - 아직 구현 전.

## Experiment #56: RQ10-1 Stage 1 Pilot (summary-only, real Ground Truth)

### Hypothesis
Round 1(N=25)을 Mechanism/Topic/Neutral/Relation 네 objective로 처음
평가한다. personal_reason은 의도적으로 뺀다 - "공부용/공부용"처럼
저장 이유가 그대로 겹치면 내용이 아니라 이유를 읽고 Ground Truth를
맞히는 leakage 위험이 있다.

### Data
round1.json 25개 중 content_summary 없는 s8 제외 → 24개, 276쌍
(same-group 19쌍, diff-group 257쌍 - 사용자가 만든 13개 그룹 중
하나라도 공유하면 same).

### Result
| Objective | ROC-AUC | mean same-group | mean diff-group |
|---|---|---|---|
| Mechanism | 0.500 | 0.000 | 0.000 |
| Topic | 0.723 | 0.239 | 0.012 |
| Neutral | 0.918 | 0.200 | 0.038 |
| Relation | 0.903 | 0.413 | 0.182 |

### Insight
Mechanism = 0.500은 실패가 아니라 적용 범위 밖 - 단일 기술 도메인
(AI Researcher의 Transformer/Attention류) 안에서만 성립하는
objective였다. Topic(0.723)이 Neutral/Relation(0.90대)보다 뚜렷이
낮은 게 새로운 발견 - 가상 데이터에서는 Topic≈Neutral≈Relation
이었는데, 실제 사용자 그룹("여행,이동용" = 전주+여수+아쿠아리움+
강남맛집, "건강용" = 다이어트+스트레칭+헬스)은 같은 Topic이 아니라
같은 task bundle(나중에 같이 참고할 것)로 묶여 있어서, "같은
주제인가"를 묻는 Topic보다 "관련 있는가"를 묻는 Neutral/Relation이
더 가까웠다.

### Decision
`docs/research_phase_2_rq10-0.md`에 Stage 1 Pilot 결과 기록. RQ10-1
질문을 "human organizational behavior"에서 **"real-world personal
organization"**으로 좁힘(가상 Topic 레이블과 실제 개인 조직이 다른
objective를 요구한다는 게 드러났으므로). Mechanism 제외, Neutral/
Relation만 갖고 Stage 2 진행 - 변수 하나씩만 바꾸는 원칙 유지.

## Experiment #57: RQ10-1 Stage 2a (질문을 Ground Truth와 정렬)

### Hypothesis
"같은 그룹인가"가 아니라 "사용자가 나중에 함께 다시 찾아볼 가능성이
높은가"로 재정렬한 새 프롬프트(`retrieval` mode)를 추가, content_
summary만으로(personal_reason 없이) Neutral/Relation과 비교한다.

### Data
Experiment #56과 동일 24개/276쌍. Neutral/Relation은 캐시 재사용,
retrieval만 신규 채점(276건).

### Result
| Objective | ROC-AUC | mean same-group | mean diff-group |
|---|---|---|---|
| Neutral | 0.918 | 0.200 | 0.038 |
| Relation | 0.903 | 0.413 | 0.182 |
| Retrieval | 0.913 | 0.366 | 0.144 |

### Insight
세 값이 0.90~0.92에 몰려 N=19 규모에서는 사실상 구분 불가 - 질문
재정렬 자체는 뚜렷한 개선을 안 줬다. Topic처럼 엄격한 매칭만 아니면
(Semantic Relatedness family 안이면) 구체적 문구는 안 중요하다는
쪽으로 해석이 좁혀진다 - Measurement Family 개념이 실제 데이터에서도
재확인됨.

### Decision
prompt를 더 안 건드리고 Stage 2b(personal_reason 추가)로 진행,
Neutral 하나만 대표로 사용(세 objective가 사실상 동등하므로).

## Experiment #58: RQ10-1 Stage 2b (personal_reason을 컨텍스트로 추가)

### Hypothesis
Neutral 하나로, content_summary만 vs content_summary+personal_reason
비교. ROC-AUC 자체보다 어떤 pair가 오답→정답으로 바뀌는지(error
analysis)를 더 비중있게 본다 - N=19라 AUC는 거의 안 움직일 수 있지만
오류 패턴은 바뀔 수 있다는 가설.

### Data
동일 24개/276쌍. content+reason 조건만 신규 채점(276건).

### Result
| Condition | ROC-AUC | mean same-group | mean diff-group |
|---|---|---|---|
| content only | 0.918 | 0.200 | 0.038 |
| content + reason | 0.921 | 0.239 | 0.052 |

가장 심한 false negative(s12-s15, 여수맛집 vs 아쿠아리움) 0.10→0.15,
가장 심한 false positive(s1-s5) 0.75→0.75 - 둘 다 사실상 안 고쳐짐.

### Insight
두 축(질문 변경, 입력에 저장 이유 추가)을 다 시도했는데 둘 다 거의
같은 결과로 수렴 - "더 좋은 prompt를 찾으면 풀린다"는 가설이 꽤
강하게 기각된다. 지금 personal_reason이 대부분 content에서 이미
추론 가능한 정보였다("도커 입문"+"공부용" - LLM도 content만 보고
짐작 가능)는 게 원인으로 보인다. 진짜 새 정보가 되려면 content 밖에
있는 행동 맥락(언제/누구와/어떤 상황에서 다시 볼지)이어야 한다.

### Decision
**Finding P2-002**(Prompt Engineering Is Not the Bottleneck for Real
Organization) 신설. Round 1(N=25 Pilot)을 여기서 종료 - 확인된 것
(Mechanism 적용범위 밖, Relatedness family 동등, prompt/얕은 reason
둘 다 무영향)과 확인 안 된 것(사용자의 실제 조직 원리는 아직
복원 안 됨)을 정리. RQ10-1을 **"Objective Discovery"에서 "Information
Discovery"로** 한 단계 재구성 - "어떤 objective가 맞는가"가 아니라
"사용자 조직을 복원하려면 어떤 정보를 새로 수집해야 하는가". 새
personal_reason(진짜 behavioral context) 수집은 사실상 Round 1.5
(새 데이터셋 제작)라 지금 하지 않고 향후 과제로 남김.

## Round 1.5 설계: Behavioral Context Discovery

RQ10-1을 한 단계 더 재구성 - "Which semantic objective explains
human organization?"에서 **"What information is actually used by
humans when organizing personal knowledge?"**로. Phase 1(Resolution
발견) → RQ10-0(Measurement Family 발견) → RQ10-1 Round 1(정보 부족
발견)로 각 단계가 앞 단계의 한계를 이어받는 구조.

Round 1.5는 새 알고리즘이 아니라 사람의 조직 방식을 설명하는 행동
정보가 무엇인지 규명하는 게 목적. 질문을 최소화(4개)해서 25개
스크랩 각각에 새로 받는다: purpose(왜 저장?), time_horizon(언제
다시 볼?), trigger(무슨 상황에서 다시 찾을? - 가장 중요하게 보는
축, 예: 전주 여행의 Topic은 "여행"이지만 trigger는 "전주 가기
직전"), importance(못 찾으면 얼마나 곤란한가 - 개별 속성이라 pairwise
judge 입력에 자연스럽게 안 들어감, 수집은 하되 사용 방식은 결과 보고
결정).

`round1.json`에 4개 필드(purpose/time_horizon/trigger/importance)
빈 값으로 스캐폴드 추가(로컬 전용, 커밋 안 함). `docs/research_phase_2_
rq10-0.md`에 Round 1.5 설계 절 추가. Stage 1.5 실험 계획: content_
summary만 vs content_summary+behavioral context로 Neutral(Round 1
대표 objective) 채점 비교 - 의미 있게 개선되면 "사람은 semantic
similarity보다 behavioral context를 더 많이 사용해 지식을 조직한다"는
결론. 아직 데이터 수집 전, 실행 안 함.

## Experiment #59: RQ10-1 Round 1.5 - Behavioral Context

### Hypothesis
진짜 behavioral context(content에서 추론 불가능한 정보)를 주면
content-only 대비 실제 그룹 복원력이 개선되는가? Neutral 하나로,
content_summary만 vs content_summary+purpose+time_horizon+trigger
비교(importance는 계획대로 제외 - 개별 속성인 데다 실제 값도
"검색해서 바로 찾을 정도로 낮음"으로 거의 균일해서 추가 정보 없음).

### Data
사용자가 25개 스크랩 전부에 4개 필드를 채움. content_summary 있는
24개, 276쌍(same-group 19쌍) - Experiment #56/#58과 동일 표본/GT.

### Result
| Condition | ROC-AUC | mean same-group | mean diff-group |
|---|---|---|---|
| content only | 0.918 | 0.200 | 0.038 |
| content + behavioral | 0.925 | 0.332 | 0.078 |

AUC는 노이즈 수준(+0.007)이지만, 가장 심하게 틀렸던 same-group 쌍
10개 중 7개가 +0.05~+0.15 개선(예: s12-s15 0.10→0.20, s15-s23
0.10→0.25) - Stage 2a/2b(질문 변경, 얕은 이유 추가)에서는 거의 안
움직였던 것과 다른 패턴. 다만 diff-group의 일부 오답도 같이 상승
(s17-s9 +0.25, s10-s19 +0.20)해서 선택적 개선이 아니라 전반적 상승과
섞여 있었고, 절대값도 threshold를 넘길 만큼은 아니었다.

### Insight
질문(Round 1)도 얕은 저장 이유(Round 1b)도 완전히 무효했는데,
진짜 behavioral context는 처음으로 방향성 있는 움직임을 만들었다 -
하지만 자동 분류를 완결할 정도는 아니다. "AI가 사용자 조직을 혼자서
복원할 수 있는가?"라는 원래 질문의 답은 "아니다"이지만, "행동
맥락을 조금 받으면 AI 추천 품질은 개선된다"는 답은 얻었다 - 이건
연구 실패가 아니라 제품 설계 원칙(자동 분류가 아니라 AI 추천+사용자
확인)으로 직결된다.

### Decision
**Finding P2-003**(Behavioral Context Improves Semantic Organization,
But Only Incrementally) 신설. 사용자와 합의한 stopping rule에 따라
결과와 무관하게 Round 1/1.5, 나아가 **Phase 2 전체를 여기서 종료**한다
- 더 파고드는 것(behavioral context 표현 방법 최적화, trigger
vector화 등)은 새 질문이 아니라 이미 답 나온 질문의 성능 개선이라는
판단. `docs/research_phase_2_rq10-0.md`에 Experiment #59 결과와
Finding P2-003, "Phase 2: Complete" 기록. `docs/research_phase_2_
summary.md` 신설(Phase 1 summary와 같은 구조 - 연구 목표/RQ 요약/
Finding 요약/실패한 접근/최종 결론). `docs/v1_design.md` 신설 - 연구
결론을 제품 설계로 옮김("스크랩+선택적 맥락 → AI 추천(Two-stage
architecture, Neutral objective) → 사용자 확인", 실제 제품에서는
Round 1.5의 4개 질문이 아니라 자유 입력 1개로 마찰 최소화).
`docs/anchor_model.md`, `docs/algorithm_limitations.md`의 Phase
상태 표시를 "Phase 2도 Complete"로 갱신.

## v1_design.md 보강: Content Extraction을 별도 엔지니어링 리스크로 명시

Phase 2 종료 브리핑을 사용자가 ChatGPT 세션과 릴레이하며 검토하는
과정에서, "Content extraction이 파이프라인의 한 단계로 담백하게
들어가 있는데 실제로는 AI 추천보다 먼저 풀어야 하는 독립적인
엔지니어링 문제"라는 지적이 나왔다. Round 1 데이터로 검증
가능했다(WebFetch 성공 9/25, 검색 스니펫 대체 15/25, 완전 실패
1/25 - naver blog/namu.wiki 등 국내 플랫폼 다수가 스크래핑 차단) -
지적을 그대로 받아들이지 않고 이미 있는 실험 데이터로 재확인한 뒤
반영했다.

`docs/v1_design.md`에 "Open Engineering Risk: Content Extraction"
절 신설(고려 사항: robots 차단/JS 렌더링/로그인·Paywall/국내
플랫폼/YouTube/PDF/GitHub·Notion 등 소스별 처리, 추출 라이브러리
선택과 fallback 전략이 V1 구현 전 결정 필요). Scrap Flow에 Content
Extraction 단계를 명시적으로 추가. Out of Scope 섹션을 문서 근거
있는 항목만으로 재정리("Reinforcement Learning"처럼 대화 중 근거
없이 나온 제안은 반영 안 함 - Island merge/split은 Roadmap V2와
연결되는 근거 있는 항목이라 추가).

## V1 구현 착수: Content Extraction부터, docs/content_extraction.md 신설

AI 추천 파이프라인(Embedding/Cosine/LLM Rerank)보다 Content
Extraction을 먼저 구현하기로 결정 - 뒤 단계 전부가 여기서 나오는
결과물의 품질에 의존하기 때문. AI 추천 쪽은 V0 연구로 설계가 거의
확정된 반면(Two-stage architecture, Neutral objective), Extraction은
아직 불확실성이 큰 영역(라이브러리, 플랫폼별 처리, fallback 전략
전부 미정)이라는 게 근거.

**스택 결정**: Java/Spring - 다른 포트폴리오 프로젝트(NewsMailer,
BuzzerBidder, Notification Platform, MotiPeople)와 일관된 스토리를
위함. AI 부분은 Embedding/LLM API 호출이라 언어 생태계에 안 묶여서
Python을 유지할 이유가 적음. Extraction만 Java 생태계(jsoup+
readability4j)로 먼저 검증하고, 성공률이 부족하면 그때만 Python
마이크로서비스로 분리 - 처음부터 다중 언어로 시작 안 함.

`docs/content_extraction.md` 신설:
- `ExtractionResult`(status/title/content/summaryCandidate/
  sourceType/fallbackLevel/failureReason) - failureReason은 실패
  원인(ROBOTS_BLOCKED/NETWORK_ERROR/TIMEOUT/UNSUPPORTED_SOURCE/
  EMPTY_CONTENT/LOGIN_REQUIRED)을 기록해 운영 지표를 뽑을 수 있게 함
- FallbackLevel을 0~4 등급으로 명확히 정의(DIRECT_EXTRACTION →
  OPEN_GRAPH_ONLY → SEARCH_SNIPPET → USER_INPUT → EXTRACTION_FAILED)
- SourceType 8종(ARTICLE/NAVER_BLOG/NAMUWIKI/GITHUB/YOUTUBE/PDF/
  NOTION/UNKNOWN) - 티스토리/브런치는 ARTICLE과 전략이 같아서 통합
- 플랫폼별 처리 전략 표 - 네이버 블로그의 iframe 2단계 요청 패턴,
  봇 차단과 JS 렌더링을 별개 문제로 구분(Round 1 실패 원인 대부분은
  전자)해서 Playwright를 기본값으로 두지 않음
- 품질 지표(KPI): Success Rate, Fallback Distribution, SourceType
  Success Rate, Average Content Length - Round 1의 36% 성공률은
  범용 스크래퍼 기준이라 이 전략 적용 후 재측정 필요
- Non-goals: robots 우회/로그인 세션 자동화/CAPTCHA 우회/Paywall
  우회/불법 스크래핑 - 명시적으로 범위 밖.

## V1 첫 구현: Spring 프로젝트 스캐폴딩 + Extraction Foundation

로컬에 있는 다른 Java/Spring 포트폴리오 프로젝트 두 개(notification-
platform, motipeople-server)를 직접 확인해서 컨벤션을 검증했다 -
notification-platform은 `backend/`, Gradle Groovy DSL, `com.example`
(Spring Initializr 기본값이 그대로 남음), 레이어+기능이 섞인 평평한
패키지 구조였고, motipeople-server(사용자가 "주로 쓰던" 프로젝트)는
`server/`, Gradle Kotlin DSL, `com.motipeople`(프로젝트명을 그대로
패키지 루트로 씀), `{feature}/{controller,dto,entity,repository,
service}` feature-first 구조였다. 두 프로젝트가 서로 다른 컨벤션을
쓰고 있다는 걸 실제로 열어봐서 확인한 뒤, motipeople 쪽을 기준으로
채택 - notification-platform은 당시 컨벤션이 섞인 것으로 보고,
motipeople이 여러 기능을 가진 실제 서비스로 자란 선례이자 World
Engine이 자랄 모습에 더 가깝다는 판단.

Spring Initializr(`start.spring.io`)로 프로젝트 생성 - 처음
`bootVersion=4.1.0.RELEASE`를 명시하면 서버 측에서 BOM 해석 에러(500)
가 발생했는데, bootVersion을 생략하고 서비스 기본값에 맡기니 정상
생성됨(서비스 쪽 일시적 이슈로 추정). `group=com.worldengine`,
`type=gradle-project-kotlin`, Java 21 toolchain, 의존성(web/
validation/data-jpa/postgresql/lombok/actuator/testcontainers/
docker-compose)으로 생성 후 `world-engine/server/`에 배치.

**Extraction Foundation 구현** - `docs/content_extraction.md`
설계를 그대로 코드로 옮김:
- `com.worldengine.extraction.model`: `ExtractionResult`(record) +
  `ExtractionStatus`/`SourceType`/`FallbackLevel`/`FailureReason`
- `com.worldengine.extraction.strategy`: `ExtractionStrategy`
  인터페이스, `ArticleExtractionStrategy`(jsoup 1.21.1 +
  readability4j 1.0.8 - Mozilla Readability 알고리즘의 Kotlin/Java
  포트, Maven Central에서 좌표 확인 후 사용) - 본문 추출 실패 시
  Open Graph 메타태그로 자동 격하
- `com.worldengine.extraction.service`: `ContentExtractionService`
  (전략 리스트에서 `supports()`가 true인 첫 전략에 위임하는 라우터)
- `ArticleExtractionStrategyLiveTest`: `@Tag("live")`로 분리한 실제
  네트워크 통합 테스트(44bits.io Docker 글, Wikipedia Spring
  Framework 문서, 네이버 블로그) - `./gradlew liveTest`로 수동 실행,
  기본 `./gradlew test`에서는 제외(외부 서비스 의존으로 CI 불안정화
  방지). 3/3 통과 확인 - 일반 기사 두 개는 본문 추출 성공, 네이버
  블로그는 전용 전략 없이도 정상적으로 실패/fallback 처리됨(Round 1
  의 실패 패턴과 일관, NaverBlogExtractionStrategy 필요성을 재확인).

**기본 테스트 안정화**: Spring Initializr가 자동 생성한
`ServerApplicationTests`가 Testcontainers로 실제 Postgres를 띄우려
해서 Docker 없는 환경에서 실패 - 아직 JPA 엔티티가 없는 시점이라
Testcontainers가 불필요하다고 보고, H2 인메모리 DB(`testRuntimeOnly`)
로 전환해서 `./gradlew test`가 Docker 없이도 통과하도록 정리.
Testcontainers 설정(`TestcontainersConfiguration`)은 삭제하지 않고
남겨둠 - 실제 JPA 리포지토리가 생기는 시점에 별도 통합 테스트에서
다시 씀.

`docs/adr/` 신설 - ADR-001(Java over Python: V0는 연구 코드라 Python,
V1은 제품 코드라 Java/Spring, AI 사용이 API 호출뿐이라 Python
생태계 이점이 V1엔 크지 않음), ADR-002(Feature-first 패키지 구조:
motipeople-server 컨벤션을 실제로 비교 확인한 뒤 채택, notification-
platform의 평평한 구조는 채택 안 함).

첫 PR 범위: Spring 스캐폴딩 + Extraction Foundation(model/strategy/
service) + live 테스트 + ADR 2개 - 하나의 완결된 마일스톤. 다음은
`docs/content_extraction.md`를 따라 NaverBlogExtractionStrategy,
GithubExtractionStrategy, YouTubeExtractionStrategy,
PdfExtractionStrategy, 검색 스니펫 fallback을 순서대로 구현.

## NaverBlogExtractionStrategy 구현 (Java 코드는 사용자가 직접 타이핑)

PR #50 직후 사용자가 명시적으로 작업 방식을 바꿈 - "앞으로 자바 코드
같은건 너가 보여주면 내가 따라치는 식으로 가보자." 이후 Java 코드는
Claude가 Write로 직접 작성하지 않고 채팅에 보여주면 사용자가 타이핑,
Claude는 리뷰·컴파일·테스트만 담당하는 방식으로 전환.

구현 전 실제 네이버 블로그 페이지를 curl로 직접 확인 - `blog.naver.com/
{blogId}/{logNo}` 경로에서 blogId/logNo를 바로 파싱해 `PostView.naver`
URL을 구성할 수 있음을 검증(iframe 응답의 실제 src가 정확히 이 패턴),
본문이 `div.se-main-container`에 깨끗하게 담겨 있음도 확인.

**타이핑 과정에서 발견된 버그 3개** (전부 `:`/`.` 관련 오타):
1. `document.selectFirst("div se-main-contained")` - CSS 선택자에
   `.`이 빠지고 클래스명도 오타(`contained`→`container` 필요) → 절대
   안 매칭돼서 항상 fallback으로 빠짐
2. `BLOG_ID_LOG_NO_PATTERN.matcher(uri.toString())` - 정규식은 경로만
   매칭하게 만들었는데 전체 URL 문자열을 넣어서 항상 매칭 실패 →
   `uri.getPath()`로 수정
3. `meta[property=og.title]`/`og.description` - 실제 속성은 콜론인데
   점으로 오타 → Open Graph fallback도 항상 실패

세 곳 다 수정 후 컴파일 성공. `NaverBlogExtractionStrategy`도
`ArticleExtractionStrategy`도 `@Component`인데 후자가 `supports()`를
항상 true로 반환해서, Spring이 주입하는 `List<ExtractionStrategy>`
순서에 따라 전용 전략이 아예 실행 안 될 위험이 있었음 - `@Order`로
명시적 우선순위 부여(NaverBlog=1, Article=LOWEST_PRECEDENCE).

### Result

`NaverBlogExtractionStrategyLiveTest` - Round 1에서 WebFetch로 전부
직접 추출 실패했던 네이버 블로그 URL 3개(`dailytrip_/222858904869`,
`nimo611/223347108051`, `happy_snubh/223529460665`)로 검증, **3/3
성공**. `ArticleExtractionStrategyLiveTest`도 2/2 유지, 기본
`./gradlew test`도 Docker 없이 통과.

### Insight

`content_extraction.md`에서 세운 가설("봇 차단 문제는 무거운 대응
없이 iframe 2단계 요청 같은 가벼운 방법으로 해결 가능하다")이 실제
데이터로 검증됨 - Round 1의 WebFetch 실패(9/25 직접 성공)가 도구의
한계였지, 네이버 블로그 자체가 뚫을 수 없는 벽은 아니었다는 근거.

## GithubExtractionStrategy 구현

HTML 파싱 대신 GitHub REST API로 README를 직접 요청 - 구현 전 실제
curl로 `Accept: application/vnd.github.raw+json` 헤더를 주면 base64
디코딩 없이 원문을 바로 받을 수 있음을 검증. README 없으면 저장소
`description` 필드(JSON, `com.fasterxml.jackson`이 아니라 `tools.
jackson.databind` - Spring Boot 4.1이 Jackson 3.1.4를 쓰면서 패키지가
바뀜)로 격하. 인증 없는 API는 시간당 60회 제한 확인(운영 단계에서
personal access token 필요 가능성 기록).

타이핑 과정에서 진짜 버그는 세미콜론 누락 1건뿐이었음 - Jackson
패키지 임포트(`tools.jackson.databind`)는 오히려 Claude가 구식
패키지명(`com.fasterxml.jackson`)으로 잘못 알려줬던 것을 사용자가
올바르게 고쳐 씀(Spring Boot 4.1의 실제 의존성 트리로 확인). 이후
`json.path("description").asText(null)`이 Jackson 3.x에서
deprecated라는 컴파일 경고가 나와 `asString(null)`로 교체(클래스
파일 직접 열어서 API 확인 후 제안).

`GithubExtractionStrategyLiveTest` - spring-boot 저장소 URL 2개
(루트, `/tree/main` 경로 포함 - owner/repo 파싱이 trailing path가
있어도 되는지 검증) 2/2 통과. 전체 live 테스트 7/7(기사 2+네이버
블로그 3+GitHub 2), 기본 test도 Docker 없이 통과 유지.

## YouTubeExtractionStrategy 구현 - Data API 대신 메타태그

`content_extraction.md`엔 원래 "YouTube Data API"로 적혀 있었으나,
실제로 확인해보니 키 없이는 403(Data API), oEmbed는 title/author만
주고 description이 없었다. 반면 watch 페이지 HTML 자체에
`og:description`으로 영상 설명이, `youtu.be` 단축링크도 jsoup의
기본 리다이렉트 추적으로 동일하게 메타태그가 노출되는 걸 curl로
확인 - API 키 없이, 다른 HTML 기반 전략과 같은 패턴(jsoup)으로
처리 가능하다는 근거. 자막(timedtext)은 비공식 엔드포인트+언어
선택+페이지 내부 JSON 구조 변경 리스크가 겹쳐서 향후 확장 범위로
미룸. `content_extraction.md`의 YouTube 행과 설계 원칙 문단을
갱신(ADR은 "전략 구현 세부사항"이라 불필요하다고 판단, Data API로
전환하게 되면 그때 ADR로 남기기로).

같은 페이지 요청에서 이미 `og:title`을 얻으므로, description이
없을 때의 fallback(문서상 "oEmbed 제목만")도 별도 API 호출 없이
이미 가진 title로 처리하도록 구현 - 네트워크 호출 하나를 줄임.

`YouTubeExtractionStrategyLiveTest` - watch URL과 `youtu.be` 단축
링크 둘 다 2/2 통과, 오타 없이 정확하게 타이핑됨. 전체 live 테스트
9/9(기사 2+네이버 3+GitHub 2+YouTube 2), 기본 test 유지.

## PdfExtractionStrategy 구현

Apache PDFBox 3.x는 2.x에서 API가 크게 바뀜(`PDDocument.load()` 정적
메서드 제거, `Loader.loadPDF()`로 이동) - Jackson 3.x 때 실수를
반복하지 않으려고 이번엔 미리 javadoc(`Loader.loadPDF(byte[])` 등
오버로드)을 직접 확인한 뒤 코드를 제시. jsoup으로 PDF 바이트를
받아(`ignoreContentType(true)` + `maxBodySize` 상향) `Loader.loadPDF`
+ `PDFTextStripper`로 텍스트 추출, 스캔본처럼 텍스트 레이어가 없으면
URL 파일명을 제목/내용으로 대체.

타이핑은 오타 없이 정확했으나, **Claude가 준 live 테스트용 PDF URL
(W3C 더미 PDF)이 지금 403을 반환**한다는 게 실제 실행에서 드러남(코드
버그 아님, 테스트 URL 선정 실수) - curl로 재검증 후
`www.orimi.com/pdf-test.pdf`(실제 1페이지 PDF, 200 확인)로 교체.
같은 확인 과정에서 arxiv 논문 PDF(`arxiv.org/pdf/{id}`)처럼 `.pdf`
확장자가 없는 URL은 지금 `supports()`(확장자 검사만 함)로 못 잡는다는
한계도 발견 - Round 1 실제 데이터엔 `.pdf` 확장자 있는 PDF만 있었고,
Content-Type 기반 판별은 `supports()`를 I/O 없는 순수 함수에서 벗어나게
만드는 더 큰 설계 변경이라 지금은 미루기로 결정(Playwright/YouTube
Data API/자막 파싱을 미룬 것과 같은 "증거 없이는 안 만든다" 원칙).

전체 live 테스트 10/10(기사 2+네이버 3+GitHub 2+YouTube 2+PDF 1),
기본 test 유지. `docs/content_extraction.md`의 다섯 전략(Article/
NaverBlog/GitHub/YouTube/PDF)이 전부 구현 완료 - 남은 건 JS 렌더링
전략(Playwright, 아직 증거 없어 보류)과 검색 스니펫 fallback.

## Extraction Validation: ContentExtractionService를 Round 1 실제 데이터로 재현

검색 스니펫 fallback을 바로 만들지, 먼저 5개 전략의 실제 성능을
측정할지 사용자와 논의 - "증거 없이는 안 만든다" 원칙을 검색 API
도입 여부에도 적용하기로 하고 후자를 선택. `ContentExtractionKpiLiveTest`
신설 - `ContentExtractionService`(5개 전략 전부 Spring 순서대로 연결)
를 Round 1의 실제 25개 URL(`round1.json`, gitignore 대상)로 재현.

타이핑 과정에서 Claude가 Jackson 패키지를 또 구버전(`com.fasterxml.
jackson.databind`)으로 잘못 알려줬고, 이번엔 IDE가 그걸 Testcontainers
내부용 shaded 복사본(`org.testcontainers.shaded.com.fasterxml.jackson...`)
으로 자동완성해서 컴파일은 됐지만 잘못된 의존성이었음 - `asText`가
deprecated 경고 없이 컴파일된 것으로 shaded 복사본이 구버전 Jackson
이라는 것도 확인, `tools.jackson.databind` + `asString`으로 수정.

### Result
| 지표 | 값 |
|---|---|
| Success Rate (DIRECT+OPEN_GRAPH) | **88.0%** (22/25) - Round 1의 WebFetch 기준 36% 대비 대폭 상승 |
| NAVER_BLOG | 9/9 (100%) |
| PDF | 1/1 (100%) |
| ARTICLE(기타 전부) | 12/14 (86%) |
| GitHub/YouTube | 0건(Round 1 URL 중 해당 없음) |
| 평균 본문 길이 | 5,961자(DIRECT_EXTRACTION만) |

실패 3건 중 `UNSUPPORTED_SOURCE` 1건은 **사이트 문제가 아니라 데이터
결함**으로 확인 - `round1.json`의 namu.wiki URL 하나에 인코딩 안 된
공백이 그대로 있어서 `new URI(...)` 파싱 자체가 실패(파이썬으로 직접
확인). 나머지 `ROBOTS_BLOCKED`/`NETWORK_ERROR` 각 1건은 전용 전략이
없는 namu.wiki 계열로 추정.

### Insight
검색 스니펫 fallback 없이도 88%가 나왔고, `content_extraction.md`가
잠정 제시한 목표(70%)를 넘었다. 남은 실패는 외부 검색 API보다 (a)
URL 인코딩 정규화, (b) namu.wiki 전용 전략 쪽이 더 싸고 정확한
해결책으로 보인다.

### Decision
`docs/extraction_validation.md` 신설 - 테스트 데이터/결과/실패 원인
분석/V1 판단(검색 스니펫 fallback·Playwright·Python 분리 전부 "지금은
불필요")을 기록. `docs/content_extraction.md`의 KPI 절에 "측정 완료"
포인터 추가. Extraction 쪽 작업은 여기서 baseline을 확보하고 일단락 -
다음은 AI 추천 파이프라인(Embedding/Cosine/LLM Rerank)으로 이동
가능한 상태.

## AI 추천 파이프라인 착수: OpenAiEmbeddingClient

`docs/v1_design.md` Scrap Flow 4단계(Cosine 후보 추리기)의 입력을
만드는 첫 조각. OpenAI가 공식 Java SDK를 안 내서(Python/Node/Go/
Kotlin만 있음) jsoup/PDFBox 때와 같은 이유로 Spring `RestClient`를
직접 써서 Embeddings API를 호출하기로 결정. 코드 제시 전에 실제
curl로 응답 스키마(`data[].embedding`, 1536차원)를 미리 검증(OPENAI_
API_KEY는 `prototype/.env`에 이미 있는 걸 재사용, 절대 값을 출력하지
않고 셸에서만 source).

API 키 주입 방식(환경변수 vs .env 재사용)과 live 테스트 검증 여부를
AskUserQuestion으로 확인 - 둘 다 "권장" 옵션(환경변수 주입, live
테스트 병행)으로 결정.

### 버그 3건 - 전부 Spring 자동설정/클래스패스 관련, 코드 로직 버그 아님

1. `RestClient.Builder`를 생성자에서 Spring 주입받게 짰는데, 이
   프로젝트 설정에서는 그 빈이 자동 등록 안 됨 - `RestClient.builder()`
   를 직접 호출하는 방식으로 변경(Spring 빈 의존성 하나 제거).
2. 그 결과 `OpenAiEmbeddingClientLiveTest`의 생성자 호출부도 인자
   개수가 바뀌어서 같이 고쳐야 했음(사용자가 먼저 "이러면 테스트
   쪽에 문제 생기는 거 아니냐"고 스스로 짚어냄).
3. `server/src/test/resources/application.properties`가 `src/main/
   resources`의 동일 파일을 **병합이 아니라 완전히 덮어쓴다**는 걸
   처음에 놓쳐서, `openai.api-key`만 추가하고 `openai.embedding-model`
   을 빠뜨림 - 기본 `./gradlew test`가 `PlaceholderResolutionException`
   으로 실패. 두 프로퍼티 다 테스트 리소스에 있어야 한다는 걸
   확인하고 정정(Claude가 처음엔 "한 줄만 필요하다"고 잘못 안내했다가
   실패 스택트레이스 보고 정정).

### Result

`OpenAiEmbeddingClientLiveTest` - 실제 텍스트를 embed해서 1536차원
벡터 반환 확인. 기본 `test`도 가짜 키(`test-key-not-real`)로 전체
Spring 컨텍스트가 뜨는 것까지 확인(Docker도 실제 API 키도 필요 없는
상태 유지). 전체 live 테스트 12개 중 11개 통과 - PDF 1건은
`orimi.com`이 이 시점에 응답 없음(curl로 직접 재확인, 오늘 변경과
무관한 외부 사이트 일시 장애).

### Decision
`OpenAiEmbeddingClient`(`com.worldengine.recommendation.client`)
커밋. 다음은 Island 후보에 대해 Cosine similarity를 계산하는 단계
(Scrap Flow 4단계 완성) → LLM Pairwise Judge 재정렬(5단계).

## CosineSimilarity - 순수 계산 유틸

Island 영속성(JPA 엔티티/Repository)이 아직 전혀 없는 상태에서 Cosine
유사도 계산을 어디까지 만들지 논의 - V0 Python의 `compute_assignment_
matrix()`가 DB 없이 입력→계산→출력만 하는 순수 함수였던 것과 같은
분리 원칙을 V1에도 적용하기로 함. Island Entity/JPA/Repository/
PostgreSQL/추천 서비스는 명시적으로 이번 범위 밖.

GPT 의견을 사용자가 가져와서 검토 - 인터페이스 설계(`findTopK(query,
candidates, k)`, `VectorCandidate`/`SimilarityResult` record)와 In/
Out of Scope 구분은 그대로 반영. 클래스/레코드 이름을 "Island"가 아니라
일반적인 이름(`VectorCandidate`)으로 짓자는 것도 반영(비용 거의 없고
재사용성에 도움). **다만 패키지를 `common/vector/`에 두자는 제안은
반영 안 함** - 지금 실사용처가 recommendation 하나뿐인데 미리
common으로 옮기는 건 "증거 없이는 안 만든다/확장하지 않는다" 원칙에
어긋난다고 판단, `recommendation/vector/`에 둠. GPT 의견이라고 전부
받아들이지 않고 이 프로젝트의 기존 원칙에 맞는지 걸러서 반영.

### Result
`CosineSimilarity`(정적 메서드, Spring Bean 아님), `VectorCandidate`/
`SimilarityResult`(record), `CosineSimilarityTest`(빈 리스트/k 초과/
정렬/직교·동일 벡터 케이스) - 타이핑 오타 없이 5/5 테스트 전부 통과.
외부 API 호출이 없어서 `@Tag("live")` 아닌 일반 테스트로 기본 `test`
에 바로 포함.

### Decision
`com.worldengine.recommendation.vector` 패키지 커밋. Island 영속성이
생기면 `IslandRepository → List<VectorCandidate>` 변환 어댑터만
추가하고 이 계산 로직은 그대로 재사용 예정.

## Island Entity/Repository - 최소 영속성 레이어

CosineSimilarity(PR #57) 머지 후, GPT 의견을 사용자가 가져와서 검토.
"LLM Pairwise Judge는 실제 Island 데이터가 있어야 의미 있게 테스트
가능하다"는 의존관계(Scrap → Extraction → Embedding → Island
Repository → Cosine Recall → LLM Pairwise Judge → User Confirm)는
타당하다고 판단해 그대로 반영 - Island 영속성부터 먼저 감.

이번 PR 범위는 GPT 제안대로 좁게: Island Entity + IslandRepository +
embedding 필드 + 기본 CRUD 테스트만. Scrap Entity/엔티티 관계 매핑/
추천 서비스는 명시적으로 이번 범위 밖(다음 PR들로 미룸).

embedding 저장 방식(GPT는 "JSON이나 적절한 형태로"라고만 하고 구체화
안 함)은 직접 결정: pgvector 같은 DB 벡터 확장 도입 안 함. 지금 설계는
IslandRepository로 전체 조회 후 애플리케이션 메모리에서
`CosineSimilarity.findTopK()`로 계산하는 구조라 DB 쪽 벡터 검색이
필요 없고, 개인용 V1 규모에서 Island 개수도 많지 않을 것 - "증거
없이는 새 인프라 안 들인다" 원칙 그대로 적용. `float[]` ↔ JSON 문자열
직렬화를 JPA `AttributeConverter`(`EmbeddingConverter`)로 처리해서
Entity/Repository 쪽에서는 `float[]`로만 다루도록 함.

### 버그 2건

1. `EmbeddingConverter.convertToDatabaseColumn`을 타이핑하다
   `convertToDataBaseColumn`(B 대문자 오타)으로 씀 - `@Override`라
   인터페이스 시그니처 불일치로 컴파일 실패. 사용자가 직접 재타이핑해
   수정(Claude가 Edit 도구로 직접 고쳤다가 "코드는 보여주면 사용자가
   타이핑" 규칙 위반임을 스스로 인지하고 되돌림).
2. `src/test/resources/application.properties`의
   `spring.jpa.hibernate.ddl-auto=none`이 그대로 남아 있어서 테스트용
   H2에 `island` 테이블이 아예 생성되지 않음(`Table "ISLAND" not
   found`) - Entity가 없던 시점에 설정된 값이었고, 이번에 처음으로
   실제 JPA Entity가 생기면서 드러남. `create-drop`으로 변경(아직
   Flyway/Liquibase 같은 마이그레이션 도구가 없어 테스트 단계에서는
   Hibernate 자동 스키마 생성이 맞다고 판단, 프로덕션
   `src/main/resources`는 변경 안 함).

참고로 `@DataJpaTest`의 패키지 경로도 Spring Boot 4.1에서
`org.springframework.boot.test.autoconfigure.orm.jpa`(3.x)에서
`org.springframework.boot.data.jpa.test.autoconfigure`로 바뀐 걸
Claude가 처음에 놓쳤는데, 사용자 IDE의 자동완성이 맞았음(직접 jar
안의 클래스 경로 확인해서 검증).

### Result
`Island`(entity), `EmbeddingConverter`(AttributeConverter),
`IslandRepository`(JpaRepository), `IslandRepositoryTest`(저장/조회,
삭제 2케이스) - 전부 통과.

### Decision
`com.worldengine.island` 패키지 커밋. 다음은 `IslandRepository`를
Cosine 계산과 연결(Repository → `List<VectorCandidate>` 변환) →
LLM Pairwise Judge 재정렬.

## IslandRecallService - Repository와 Cosine 연결

Island 영속성(PR #58) 완료 후, `IslandRepository`로 전체 조회한 결과를
`CosineSimilarity`가 쓰는 `VectorCandidate`로 변환하는 얇은 어댑터
계층을 추가. PR #57에서 미리 세워둔 계획("Island 영속성이 생기면
Repository → List<VectorCandidate> 변환 어댑터만 추가하고 계산 로직은
그대로 재사용") 그대로 실행 - `CosineSimilarity`는 손대지 않음.

`IslandRecallService`(`@Service`)가 `IslandRepository.findAll()` →
`VectorCandidate(id, embedding)` 매핑 → `CosineSimilarity.findTopK()`
호출까지만 담당. Island id를 String으로 변환해서 넘김(VectorCandidate가
범용 id 타입을 String으로 잡아둔 PR #57 설계 덕분에 추가 변환 로직
불필요).

### 버그 1건

테스트에서 `new Island(...)`로 순수 객체를 만들면 `@GeneratedValue`
필드라 `id`가 `null` - `assertThat(...).isEqualTo(close.getId().
toString())`이 NPE. 영속화 없이 "실제로 저장된 것처럼" id를 채워야
하는 문제라 `ReflectionTestUtils.setField()`로 가짜 id(1L, 2L)를
강제 주입해서 해결 - Mockito 단위 테스트에서 JPA 생성 필드를 다루는
일반적인 패턴.

### Result
`IslandRecallService`, `IslandRecallServiceTest`(가장 가까운 Island
1개 recall하는 케이스) - 오타 1군데 있었으나(첫 버전 assert가
`getId()` null 상태였음, 근본 원인은 테스트 데이터 문제) 수정 후 통과.
전체 테스트 그린.

### Decision
`com.worldengine.recommendation.service` 패키지 커밋. 다음은 LLM
Pairwise Judge 재정렬(Scrap Flow 5단계, Neutral objective 기본값).

## LlmPairwiseJudgeClient - Precision 단계 API 클라이언트

Scrap Flow 5단계(LLM pairwise judge로 top-3 재정렬)의 첫 조각. V0
Python(`prototype/pairwise_judge.py`)은 mechanism/topic/neutral/
relation/retrieval 5개 objective 프롬프트를 전부 갖고 있었는데(연구
목적상 비교 실험 필요), V1 제품 설계(`docs/v1_design.md`)는 이미
"Neutral을 기본값으로 쓴다"고 확정했으므로 나머지 4개는 포팅하지
않음(YAGNI) - Neutral 프롬프트 하나만 하드코딩.

또 하나 GPT 제안(`score()`가 `PairwiseJudgeResult(score, model)`
같은 래퍼 레코드를 반환하게 하자)은 기각 - 기존 `OpenAiEmbeddingClient.
embed()`가 `float[]`를 그대로 반환하는 선례와 불일치하고, model/token
같은 운영 정보를 실제로 쓰는 소비자가 아직 없어서 "증거 없이는 안
만든다" 원칙 적용. `double score(String textA, String textB)`로 단순
유지.

Island를 비교할 때 어떤 텍스트를 쓸지(이름? 대표 스크랩 요약?
description 필드?)는 아직 결정 안 함 - Scrap Entity/관계 매핑이 없어서
지금 결정하면 가정 위에 가정을 쌓는 꼴이라 의도적으로 미룸. 이번 PR은
순수 API 클라이언트만.

이번엔 `openai.pairwise-judge-model` 프로퍼티를 추가하면서 PR #56에서
겪었던 "test resources가 main resources를 완전 대체" 문제를 미리
알고 양쪽에 다 추가 - 처음으로 이 버그를 사전에 방지함.

### Result
`LlmPairwiseJudgeClient`(Neutral 프롬프트, temperature=0, 파싱 실패시
0.5 반환 - Python `except ValueError: return 0.5` 그대로 포팅) -
타이핑 오타 없음. 기본 `test`(오프라인) 통과, `liveTest`로 실제
gpt-4o-mini 호출 - "관련 있는 텍스트" 쌍의 점수가 "무관한 텍스트" 쌍보다
높게 나옴 확인.

### Decision
`com.worldengine.recommendation.client` 패키지 커밋. Island를 실제로
비교하려면 Scrap Entity/관계 매핑, 그리고 Island의 대표 비교 텍스트를
뭘로 할지부터 설계해야 함 - 다음 단계로 남김.

## Scrap Entity/Repository + EmbeddingConverter 공용화

Island(PR #58)와 같은 패턴으로 `Scrap` JPA Entity + `ScrapRepository`
추가. 필드는 `ExtractionResult`(title/content/summaryCandidate→summary/
sourceType/fallbackLevel)에 embedding·userContext(선택 1줄 맥락,
`docs/v1_design.md` Scrap Flow 3단계)를 더한 구성 - `sourceType`/
`fallbackLevel`은 `extraction.model`의 기존 enum을 그대로 재사용
(`@Enumerated(EnumType.STRING)`).

**이번 PR 범위에서 의도적으로 뺀 것**: `islandId` 같은 Island 연결
필드. 스크랩은 생성 시점엔 아직 어느 Island에도 안 속하고(추천 확인
전), 실제 배정은 나중에 만들 User Confirm API 몫 - 지금 넣으면 근거
없는 가정이 됨.

**EmbeddingConverter를 `island.entity`에서 `common.jpa`로 이동**.
CosineSimilarity(PR #57) 때 "실사용처가 하나뿐이라 common으로 미리
안 옮긴다"고 판단했던 것과 정확히 대칭 - 이번엔 Scrap이 두 번째
실사용처로 생겨서 "증거(두 번째 소비자) 생기면 그때 일반화한다"는
원칙을 그대로 적용해 이동. 로직 변경 없는 순수 리로케이션이라 Claude가
git mv로 직접 처리(사용자에게 먼저 확인받음 - 새 로직 없는 기계적
작업까지 타이핑시킬 필요는 없다고 판단).

### Result
`Scrap`, `ScrapRepository`, `ScrapRepositoryTest`(정상 케이스 +
추출 실패로 title/content/embedding이 전부 null인 케이스) - 타이핑
오타 없이 한 번에 통과. `EmbeddingConverter` 이동 후 `Island`import만
갱신, 전체 테스트 그린 유지.

### Decision
`com.worldengine.scrap` 패키지 + `common.jpa.EmbeddingConverter`
커밋. 다음은 Island 비교용 대표 텍스트를 뭘로 할지 결정하고
`LlmPairwiseJudgeClient`를 `IslandRecallService`의 top-3 후보에
연결하는 `RecommendationService`.

## RecommendationService - Recall+Precision 전체 연결

`docs/v1_design.md` Scrap Flow 4~5단계(Cosine Recall → LLM Pairwise
Judge Precision)를 처음으로 끝까지 연결. `IslandRecallService`로 top-N
후보를 좁힌 뒤, 각 후보를 `LlmPairwiseJudgeClient`로 재정렬.

**Island 비교 텍스트 결정**: 지금은 `Scrap`-`Island` 관계가 없어서
(그 FK는 User Confirm API 몫으로 미룸) "대표 스크랩 요약" 같은 건 못
씀 - 대신 이미 있는 `Island.name`을 비교 텍스트로 사용. 새 필드나
관계를 미리 만들지 않고 지금 가진 것으로 감(Extraction Validation,
PR #55 때와 같은 패턴 - 제일 단순한 방법으로 먼저 붙여보고, 품질
부족하면 그때 데이터 근거로 description 필드/대표 텍스트 생성 로직을
추가하기로 함).

### Result
`RecommendationService`, `IslandRecommendation`(record) - Mockito로
`IslandRecallService`/`IslandRepository`/`LlmPairwiseJudgeClient`
전부 목킹한 단위 테스트 1건: Cosine 순서(다이어트 1위)를 LLM 점수가
실제로 뒤집는 케이스(백엔드가 1위로 재정렬)까지 확인 - Precision
단계가 Recall 순서를 바꿀 수 있다는 것 자체를 검증. 타이핑 오타 없이
한 번에 통과.

### Decision
`com.worldengine.recommendation.service.RecommendationService` 커밋.
Scrap Flow 4~5단계까지는 전부 연결됨(1~3단계 Content Extraction/
Scrap 저장, 6~7단계 UI/User Confirm은 아직). 다음은 실제 API
엔드포인트(스크랩 생성 → 추천 → 확인) 노출.

## POST /scraps - Scrap Flow 1~5단계 실제 API로 노출

`docs/v1_design.md` Scrap Flow를 처음으로 실제 HTTP 엔드포인트로
연결. `POST /scraps`가 URL(+선택적 userContext)을 받아 Content
Extraction → content 앞부분 자르기(`ScrapContentPreprocessor`,
`scrap.max-summary-length` 설정값) → 임베딩 → `Scrap` 저장 →
`RecommendationService`로 top-3 추천까지 한 번에 처리.

GPT 의견(설정값으로 빼기, 별도 전처리 컴포넌트로 분리) 반영, 다만
`prepareForEmbedding`/`prepareForComparison`처럼 이름을 나누자는
제안은 기각 - 지금은 둘 다 완전히 같은 동작(앞 N자 자르기)이라 다른
이름의 메서드 두 개를 만드는 게 조기 분화. `truncate()` 하나만 유지.

`ExtractionResult.summaryCandidate`는 여전히 null(LLM 요약 단계
자체를 아직 안 만듦) - `content`를 자른 값을 Scrap.summary/임베딩/
LLM 비교 입력으로 그대로 씀. 나중에 실제 요약 품질이 부족하다는
근거가 생기면 그때 별도 요약 단계 추가.

### 버그 2건

1. 테스트: `@InjectMocks`가 `@Mock`이 아닌 일반 필드
   (`scrapContentPreprocessor`)는 생성자 주입 대상에서 제외한다는 걸
   몰라서 `ScrapService` 생성자에 null이 들어가 NPE - `@Spy`로 변경해서
   해결(실제 로직은 그대로 돌면서 `@InjectMocks` 대상에도 포함).
2. **실제 서버를 띄워 curl로 검증하다가 발견**: `ArticleExtractionStrategy`
   가 `SocketTimeoutException`/`HttpStatusException`/`IOException`만
   잡고 있었는데, jsoup은 `http://`/`https://`로 시작 안 하는 URL을
   `IllegalArgumentException`(unchecked, `MalformedURLException`을
   감쌈)으로 던져서 catch를 다 통과해 컨트롤러까지 새어나가 500 에러가
   남. PR #50/51 때부터 있던 기존 버그였는데 실제 HTTP API가 이번에
   처음 생기면서 드러남 - `catch (IllegalArgumentException e)`를
   추가해 `FailureReason.UNSUPPORTED_SOURCE`로 우아하게 처리하도록
   수정. Mock 기반 단위 테스트만으로는 못 잡는 종류의 버그라, H2를
   임시로 `runtimeOnly`로 바꿔 실제 `bootRun` + curl로 검증한 덕분에
   발견(확인 후 build.gradle.kts는 원상복구).

### Result
`ScrapContentPreprocessor`, `ScrapService`, `ScrapController`,
`ScrapCreateRequest`/`ScrapCreateResponse` - 전체 테스트 통과 +
실제 GitHub URL로 추출→임베딩→저장→추천(빈 배열, cold start)까지
end-to-end 확인, 잘못된 URL도 500 없이 `FAILED` 상태로 정상 응답
확인.

### Decision
`com.worldengine.scrap.{controller,dto,service}` 패키지 +
`ArticleExtractionStrategy` 버그 수정 커밋. 다음은
`POST /scraps/{id}/confirm`(Island 확정, 이때 `Scrap.islandId` 추가).

## POST /scraps/{id}/confirm - Scrap Flow 6~7단계, V1 Genesis 루프 완성

`docs/v1_design.md` Scrap Flow의 마지막 조각. 추천 중 기존 Island를
선택하거나 새 Island를 만들어서 Scrap을 실제로 배정. `Scrap.islandId`
필드(관계 매핑 없이 단순 컬럼)를 이번에 처음 추가 - PR #61에서
의도적으로 미뤄뒀던 부분.

**새 Island의 embedding**: 확정하는 스크랩 자신의 embedding을 그대로
사용 - 새 섬은 그 첫 스크랩의 위치에서 시작한다는 게 V0의 "새 섬은
로컬 배치" 철학과 일치. GPT 의견에서도 동의한 부분.

**프로젝트 첫 공통 예외 처리 인프라 도입**: `IllegalArgumentException`
이 그대로 500이 되는 건 "클라이언트 요청이 잘못됐는데 서버 에러로
응답"하는 HTTP 의미 오류라, 최소한의 `@RestControllerAdvice`
(`GlobalExceptionHandler`, `common.web`)를 지금 추가하기로 함 -
`IllegalArgumentException`(잘못된 요청 조합) → 400,
`EntityNotFoundException`(존재하지 않는 scrap/island) → 404 두 개만.
ErrorCode enum/커스텀 BusinessException 계층/i18n/RFC7807은 명시적으로
제외(GPT 의견 그대로 필터링해서 반영) - 앞으로 생길 다른 엔드포인트도
이 기반을 재사용.

### 버그 2건 (둘 다 타이핑 누락, 리뷰에서 잡음)

1. `confirmsWithNewIslandUsingScrapEmbedding()` 테스트 메서드 전체가
   누락 - 가장 중요한 "새 Island 생성" 경로가 검증 안 되고 있던 걸
   Read로 파일 리뷰하다 발견.
2. `throwsWhenScrapNotFound()`에 `@Test` 어노테이션이 빠져서 죽은
   메서드였던 것도 같이 발견.

### Result
실제 bootRun+curl로 전체 흐름 검증: 스크랩 생성 → 새 Island로 confirm
→ 두 번째 스크랩 생성 시 방금 만든 Island가 실제로 추천 후보에 잡힘
(llmScore 0.3) → 기존 Island로 confirm → 잘못된 요청(400)/존재하지
않는 island·scrap(404) 전부 의도대로 응답. 이 시점에 **V1 Genesis
핵심 루프(URL 입력 → 추출 → 임베딩 → 추천 → 사용자 확인 → Island
배정)가 처음으로 실제로 완주됨**.

### Decision
`Scrap.islandId`, `ScrapConfirmService`, `GlobalExceptionHandler`
커밋. 사용자와 합의: 이 PR이 머지되면 `develop`을 `main`으로 머지
(V1 Genesis 마일스톤).

## GET /scraps, /scraps/{id}, /islands, /islands/{id} - 조회 API

V1 Genesis 루프(PR #64) 완주 후 다음 방향을 사용자에게 물어봄 - 정정
기록/조회 API/새 방향 중 **조회 API**를 먼저 선택. 이유(사용자+GPT
공통 근거): 핵심 루프는 완성됐지만 지금까지 저장된 게 실제로 뭔지
확인하려면 DB를 직접 봐야 했음 - 관찰 가능성이 정정 기록보다 먼저
필요. GPT 의견 필드 목록에서 `selectedIslandId`는 실제 엔티티 필드명
(`islandId`)과 달라서 그대로 안 쓰고 기존 이름 사용, 목록 응답에
`title`을 추가(GPT 목록엔 없었지만 관찰 가능성 목적에 필요).

`ScrapRepository`에 `findByIslandId`/`countByIslandId` 파생 쿼리
추가. `Island` 쪽엔 컨트롤러/서비스가 아예 없어서 새로 만듦
(`IslandController`, `IslandQueryService`). 응답 DTO는 전용 Summary/
Detail로 분리 - `embedding`/`content`(원문 전체) 같은 큰 필드는
응답에서 제외.

### 버그 2건 (타이핑 중 발생, 리뷰에서 잡음)

1. `IslandController.java`가 `island/controller/` 서브패키지가 아니라
   `island/` 바로 아래에 생성되고 `package com.worldengine.island;`로
   선언됨 - 다른 모든 컨트롤러(`{feature}.controller`) 컨벤션과
   불일치. Claude가 git mv + 패키지 선언 수정으로 직접 정리(사용자
   확인 후, 로직 없는 기계적 수정이라 PR #61의 EmbeddingConverter
   이동 때와 같은 예외 적용).
2. `IslandDetailResponse`가 `List<ScrapSummaryResponse>`가 아니라
   `List<ScrapDetailResponse>`로 타이핑됨 - `IslandQueryService`가
   실제로 만들어 넘기는 타입과 달라 컴파일 에러. 같은 방식으로 Claude가
   직접 수정.

### Result
실제 bootRun+curl로 4개 엔드포인트 전부 검증: 스크랩 생성 → confirm
→ `GET /scraps`(목록)/`GET /scraps/{id}`(상세, summary 포함)/
`GET /islands`(scrapCount 포함)/`GET /islands/{id}`(포함된 scrap
목록) 전부 정상, 존재하지 않는 id는 404로 정상 응답.

### Decision
`scrap`/`island` 양쪽 조회 API 커밋. 다음은 사용자와 합의한 순서대로
정정 기록(Correction) 기능.

## 정정(Correction) 기록 - Scrap Flow 7단계

`docs/v1_design.md` Scrap Flow 마지막 원칙("사용자의 정정은 기록만
해둔다, V1 스코프에서는 재학습에 안 씀") 구현. 정정 여부를 판단하려면
confirm 시점에 "원래 뭘 추천했었는지"가 필요한데 그 정보가 지금까지
응답으로만 나가고 저장이 안 됐음 - 스크랩 생성 시점에 추천 1순위
Island id를 `Scrap.recommendedIslandId`로 같이 저장해두고, confirm된
`islandId`와 비교해서 판단하는 방식으로 설계. 별도 이력 테이블은 안
만듦 - 스크랩당 추천 1번·확정 1번의 1:1 관계라 엔티티 필드 하나로
충분.

`islandId`/`confirmIsland()`(PR #64) 때와 같은 패턴으로 생성자에
필드를 안 넣고 post-construction 메서드(`recordRecommendedIsland`)로
처리 - 기존에 `new Scrap(...)`을 호출하는 모든 테스트 파일을 건드리지
않기 위함. `wasCorrected()`는 Scrap 엔티티에 직접 둔 순수 판단
로직(추천도 없고 확정도 안 된 경우, 추천과 확정이 같은 경우는 모두
false).

### 버그 1건 (Claude 실수)

`ScrapSummaryResponse`에 `wasCorrected` 필드를 추가하면서
`IslandQueryService.toSummary()`(이번 작업 범위에 없던 기존 파일)의
호출부를 안 고쳐서 컴파일 에러 - 사용자 타이핑 실수가 아니라 Claude가
영향받는 다른 파일을 놓친 것. 알려주고 사용자가 직접 수정.

### Result
`ScrapTest`(recordRecommendedIsland+confirmIsland 조합 3케이스) 전부
통과. 실제 bootRun+curl로 검증: 추천 없이 confirm한 스크랩은
`wasCorrected: false`, 추천(Island A)과 다른 Island로 confirm한
스크랩은 `recommendedIslandId: 1, wasCorrected: true`로 정확히
기록되고 목록/상세 응답 둘 다 반영됨.

### Decision
`Scrap.recommendedIslandId`/`wasCorrected()`, `ScrapService` 순서
변경, 조회 API 응답에 정정 정보 노출 커밋. V1 다듬기 다음 방향은
추후 사용자와 다시 논의.

## Minimal UI - V1 UX 실사용 검증

정정 기록(PR #66) 완료 후 다음 방향 논의 - "API는 완성됐지만 AI 추천→
사용자 확인 경험 자체는 Postman/curl로 검증 불가능하다"는 사용자+GPT
공통 판단으로 V2보다 UI 연결을 먼저 하기로 함(V0부터 이어온 "가설보다
실사용 검증" 원칙의 연장).

**스택 결정**: React 등 SPA 프레임워크 대신 순수 HTML+CSS+Vanilla JS
정적 페이지, `server/src/main/resources/static/`에 배치 - Spring
Boot가 별도 설정 없이 그대로 서빙(WelcomePageHandlerMapping이
index.html을 자동 인식), npm/빌드툴/별도 dev server/CORS 설정 전부
불필요. "지금 필요한 건 프론트엔드 개발이 아니라 V1 UX 검증"이라는
근거로 GPT 의견도 동일하게 정리 - 나중에 V2에서 World 시각화(배치/
애니메이션/드래그 등)로 상태 관리가 실제로 중요해지면 그때 React 등
SPA로 분리하기로 합의(지금 구조를 흔들지 않고 옮길 수 있음).

HTML/JS는 이 프로젝트에서 처음 다루는 언어라 작업 방식(Claude가
직접 작성 vs 보여주고 타이핑)을 먼저 확인 - Python 때와 같은 이유
("핵심 학습 대상이 아니라 UX 검증 도구")로 Claude가 직접 Write.

### Result
`index.html`/`style.css`/`app.js` 3개 파일로 스크랩 입력→추천 Top-3
표시→기존 Island 선택 또는 새 Island 생성→confirm→Islands/최근
Scraps 실시간 갱신까지 한 화면에 구현. **claude-in-chrome으로 실제
브라우저에서 전체 흐름을 클릭해서 검증**(API curl이 아니라 진짜 UI
클릭 테스트는 이 프로젝트에서 처음) - cold start 케이스(추천 없음
→ 새 Island 생성), 추천 후보 클릭 케이스(score 0.30 표시된 추천
버튼 클릭 → 확정) 둘 다 정상 동작, 콘솔 에러 없음, 사이드바 카운트
실시간 반영 확인.

### Decision
`server/src/main/resources/static/` 커밋. 다음은 실제로 이 화면을
써보면서 V1 보완점을 찾거나, V2(Evolution) 설계 착수 - 사용법 그대로
"써보고 나서 결정"하기로 함.

## Finding: Island 비교 텍스트로 name(라벨) 사용 시 LLM 점수가 실질 무의미(0.1 근처 고정)

Minimal UI(PR #67)로 실제 사용해보면서 발견 - "야구" Island 후보가
명백히 관련 있는 야구 기사에도 score 0.10, 나머지는 0.00으로 사실상
변별력이 없었음.

**Evidence(실제 OpenAI 호출로 재현)**: 같은 기사 본문(오타니 부상
기사, 1272자)을 B로 뭘 주느냐만 바꿔서 비교.
- B = `"야구"`(Island.name 그대로, 지금 코드) → **0.1**
- B = `"야구 관련 뉴스와 정보"`(라벨을 문장으로 살짝 늘림) → **0.1**
  (길이를 늘려도 라벨 형태면 그대로 낮음)
- B = `"오타니 쇼헤이가 부상으로 다저스 선발 로테이션에서 이탈했다"`
  (실제 기사문 형태의 같은 도메인 문장) → **0.85**

**Root Cause**: Neutral 프롬프트가 "두 스크랩 요약"을 비교하도록
설계돼 있어서, Island 이름 같은 카테고리 라벨은 "요약"처럼 안 읽힘 -
길이가 아니라 "콘텐츠처럼 생겼는가"가 핵심 변수. PR #62에서 "Island.name
비교는 임시방편, 품질 부족 근거 생기면 발전시킨다"고 미리 열어뒀던
지점이 실사용으로 확인됨.

**처음 검토한 대안(기각)**: "Island의 가장 최근 스크랩 summary"를
비교 텍스트로 쓰는 안 - 사용자가 즉시 지적: "마지막 스크랩만 계속
따라가면 전체 주제와 동떨어질 수 있는 거 아니야?" - 정확한 지적.
최근 스크랩 하나가 우연히 벗어난 주제면 그 뒤로 계속 그 쪽으로
드리프트됨.

**채택한 해결책**: "새 스크랩의 embedding과 cosine 유사도가 가장 높은
기존 스크랩(같은 Island 소속)"의 summary를 비교 텍스트로 사용. 이미
있는 `CosineSimilarity`/스크랩 embedding을 그대로 재사용(새 인프라
불필요) - 매 비교마다 "이번 스크랩과 제일 비슷한 실제 사례"가 동적으로
선택되므로 특정 스크랩(최근 것)에 고정되는 드리프트 문제가 없음.
Island 안에서 주제가 여러 갈래로 갈리는 것(V2 Topic 분화 영역)까지
완전히 해결하진 않지만, V1 수준에서는 충분.

### Result
`RecommendationService.representativeText()`가 `ScrapRepository.
findByIslandId()`로 후보 스크랩을 모두 불러온 뒤 cosine 최댓값 스크랩의
summary를 사용(대표 스크랩이 없으면 기존처럼 Island.name 폴백). 실제
앱에서 재검증 - "고우석 이물질 논란" 기사가 야구 0.45 > 축구 0.25 >
개발 CS 0.10으로, 순서와 격차 모두 뚜렷하게 개선됨(이전 0.1/0.0/0.0
대비).

같은 세션에서 `spring.jpa.hibernate.ddl-auto=update`도 추가 - Docker
Postgres로 처음 로컬 실행 시 `relation "island" does not exist` 발견
(Spring Boot가 임베디드 DB에서만 ddl-auto 기본값을 create-drop으로
잡고, Postgres 같은 외부 DB는 기본값이 none이라 테이블이 아예 안
생성됨). Flyway/Liquibase 같은 정식 마이그레이션 도구는 아직 이르다고
판단(솔로 개인 프로젝트, 스키마 이력 관리 필요 단계 아님) - `update`로
데이터 보존하며 스키마만 자동 반영.

### Decision
두 수정 모두 커밋. 다음은 계속 써보면서 V1 보완점을 찾거나 V2
설계 착수.

## Finding: ArticleExtractionStrategy가 SPA 껍데기 HTML을 "성공"으로 오판

Minimal UI로 계속 써보다가 두 번째 발견(같은 세션 내 3번째 실사용
버그) - `zero-base.co.kr`의 SPA 랜딩페이지를 스크랩했더니 title/
summary가 둘 다 "국내최초 취업정보회사 - 제로베이스"(19자, 페이지
제목 그대로)였고, 이 콘텐츠로 추천을 돌리니 모든 Island가 0.05~0.10
사이로 밋밋하게 나옴.

**Root Cause**: `ArticleExtractionStrategy.extract()`가 readability4j
결과를 `content != null && !content.isBlank()`로만 검사했음 - jsoup은
JS를 실행 못해서 SPA 페이지는 초기 HTML 껍데기(제목 정도)만 갖고
있는데, 이것도 "빈 문자열이 아니다"라는 이유로 DIRECT_EXTRACTION
성공 판정. `docs/content_extraction.md`가 처음부터 "JS 렌더링 필요
페이지"를 알려진 한계로 남겨뒀던 부분이 재확인됨.

**GPT 의견 필터링**: "재사용 가능한 `ExtractionQualityEvaluator`
컴포넌트로 분리 + 설정값으로 임계치 관리 + 실패 시 Open Graph
fallback으로" 제안은 전부 반영(PR #63의 `ScrapContentPreprocessor`
패턴과 동일선상, `docs/content_extraction.md`의 기존 fallback 체인과도
일치). 다만 "나머지 4개 전략에도 재사용하자"는 부분은 반영 안 함 -
실제로 이 문제가 확인된 건 `ArticleExtractionStrategy` 하나뿐이라
나머지까지 지금 고치는 건 근거 없는 확장(증거 있는 곳에만 적용).

### 버그 2건 (Claude 실수, 사용자 타이핑 문제 아님)

`ArticleExtractionStrategy` 생성자 시그니처가 바뀌면서 `new
ArticleExtractionStrategy()`를 직접 호출하던 기존 테스트 2개
(`ArticleExtractionStrategyLiveTest`, `ContentExtractionKpiLiveTest`)
를 처음에 안 챙겨서 컴파일 에러 - 둘 다 이번 작업 범위 파악 누락으로
알려주고 사용자가 직접 수정.

### Result
`ExtractionQualityEvaluator`(설정값 `extraction.min-content-length=50`)
- 전체 테스트 통과. 실제 재현: `zero-base.co.kr`이 이제
`fallbackLevel: OPEN_GRAPH_ONLY`로 정직하게 처리되고 summary도
실제 og:description 문장으로 바뀜(19자 제목 반복 대신). 정상 기사
케이스는 회귀 없이 SUCCESS 그대로 유지 확인.

### Decision
`ExtractionQualityEvaluator` + `ArticleExtractionStrategy` 수정
커밋. 나머지 전략에 같은 가드레일이 필요한지는 추가 증거가 나오면
그때 판단.

## 미확정 스크랩 재방문 흐름 + README

Extraction KPI 재측정(88%, 변화 없음, Playwright 도입 근거 없음으로
결론)까지 마친 뒤 다음 다듬기 후보를 논의 - "스크랩만 해두고 나중에
정리" 패턴이 지금 흐름(생성 직후에만 confirm 가능)에서 빠져있다는
GPT 의견에 사용자 동의, 최우선으로 채택.

**설계 결정**: GPT는 `GET /scraps/{id}`에 추천을 얹거나 별도 API를
두는 두 안을 제시했는데, 전자는 기각 - 이미 "그냥 조회"용으로 쓰이는
엔드포인트에 매번 LLM 호출을 얹으면 비용/의미 둘 다 애매해짐. 대신
`POST /scraps/{id}/recommendations`를 신설해 명시적 액션으로 분리,
기존 `RecommendationService`/`confirm` API 그대로 재사용.

**안전장치(GPT가 언급 안 한 부분)**: 이미 확정된 스크랩에 추천
재계산을 허용하면, 나중에 Island 구성이 바뀌었을 때
`recommendedIslandId`가 조용히 갱신되면서 `wasCorrected`가
`true→false`로 뒤바뀔 수 있어 정정 기록(PR #66)의 신뢰성이 깨짐 -
이미 확정된 스크랩엔 400으로 막음(`IllegalArgumentException`).

`GET /scraps?confirmed=false`로 미확정만 조회하는 필터도 같이 추가
(UI의 "정리할 스크랩" 목록에 필요, 기존 조회 API를 확장하는 수준이라
범위 크지 않음).

### Result
백엔드: `ScrapRepository`(findByIslandIdIsNull/NotNull),
`ScrapQueryService.findAll(Boolean confirmed)`,
`ScrapService.refreshRecommendations()`, 컨트롤러 2곳 - 전체 테스트
통과, 타이핑 오타 없음. 프런트: "정리할 스크랩" 카드 신설(Claude가
직접 작성) - 클릭하면 추천 재계산 → 기존 confirm 흐름 그대로 재사용.

실제 브라우저(claude-in-chrome)로 전체 흐름 검증: 미확정 스크랩이
"정리할 스크랩"에 뜸 → 클릭 시 추천 재계산(0.90) → 확정 클릭 →
Islands 카운트 증가 + "정리할 스크랩 없음"으로 목록 비워짐 + 추천
섹션 자동 숨김. 이미 확정된 스크랩에 재계산 시도 시 400 확인.

**README 전면 개정**: V0 시절 체크리스트 그대로 방치돼 있던 루트
`README.md`를 V1 완료 상태로 갱신, `backend/` → `server/` 경로
수정, 로컬 실행 방법(Docker Postgres, OPENAI_API_KEY, ddl-auto=update
설명, test vs liveTest) 추가.

### Decision
백엔드/프런트/README 전부 이번 PR에 포함(사용자 요청 - "하는 김에
리드미까지"). 다음 방향은 계속 써보며 재논의.

## V1 Validation - GET /scraps/stats

"V2 가기 전에 develop→main 동기화 + V1 검증 지표"라는 GPT 순서 제안을
사용자가 가져옴 - 큰 방향(가설 대신 실사용 데이터로 다음 단계 결정)은
동의, 다만 구체 수단(PostHog 등 외부 분석 툴 도입)은 기각.

**필터링 근거**: 필요한 지표(추천 수락률/변경률/미확정 비율)가 이미
DB에 다 있음 - `Scrap.recommendedIslandId`/`islandId`/`wasCorrected()`,
`GET /scraps?confirmed=false`(PR #70) 재사용으로 계산 가능. 새 이벤트
트래킹/외부 SaaS 연동은 지금까지 지켜온 "증거 없이는 새 인프라 안
들인다" 원칙(pgvector/Playwright/Flyway 전부 같은 이유로 보류)과
충돌. "이전 대화에서 PostHog 관심 표명"이라는 GPT의 근거는 이 프로젝트
세션·메모리 어디에도 없어 확인 안 된 전제로 판단, 반영 안 함.

`confirmedAt`(평균 Confirm 소요 시간) 필드 추가는 사용자가 명시적으로
범위 밖으로 결정 - 핵심 질문("추천을 받아들이는가")엔 4개 지표로 충분.

**먼저 `develop`→`main` fast-forward 머지**(V1 Polish 완료 시점,
PR #65~70) 완료.

### Result
`GET /scraps/stats` - totalScraps/confirmedScraps/unconfirmedScraps/
recommendationAcceptedCount/recommendationOverriddenCount/
coldStartConfirmedCount/acceptanceRate/overrideRate. 순수 산술
로직이라 단위 테스트 대신 실제 데이터로 4가지 시나리오(cold start/
수락/변경/미확정) 전부 만들어서 curl로 직접 검증 - 집계 정확함 확인.
`/scraps/stats`가 `/scraps/{id}`(Long 파싱)에 안 먹히고 정확히
라우팅되는 것도 확인(Spring의 정적 경로 우선 매칭).

### Decision
`ScrapStatsResponse`/`ScrapQueryService.computeStats()`/
`GET /scraps/stats` 커밋. 며칠 실사용 후 이 지표로 V2 설계 방향
판단 예정.

## Finding: readability4j가 이커머스 페이지의 "공통 안내 영역"을 본문으로 오판(2건, 보류)

실사용 중 발견, 서로 다른 두 쇼핑몰에서 독립적으로 같은 실패 패턴
재현됨:
- `ktwizstore.co.kr`(KT 위즈 굿즈샵) 상품 페이지 - title도 빈 문자열,
  summary가 "교환 및 반품 주소 - ..."로 시작하는 반품 정책 문구
- `twinslockerdium.co.kr`(LG 트윈스 굿즈샵) 상품 페이지 - 마찬가지로
  summary가 "교환 및 반품 주소 - ..."로 시작

**Evidence(실제 OpenAI 호출로 재현)**: 두 번째 사례(LG트윈스)가 추천에서
야구 0.75로 꽤 높게 나와서 확인해보니, 실제 야구 콘텐츠와의 관련성이
아니라 **먼저 야구 Island에 들어가 있던 첫 번째 사례(KT위즈)의 반품
문구와 서로 비슷해서** 높게 나온 것으로 확인됨:
- LG트윈스 반품문구 vs KT위즈 반품문구 → 0.75
- LG트윈스 반품문구 vs 실제 야구 기사(스크랩 1) → 0.05

즉 잘못 추출된 스크랩이 Island에 한 번 들어가면, 이후 비슷하게
잘못 추출된 스크랩이 오히려 "잘 맞는 것처럼" 보이면서 추천 품질을
조용히 오염시키는 연쇄 효과가 실증됨.

**Root Cause(가설, 미확정)**: `ExtractionQualityEvaluator`(PR #69)의
길이 체크는 통과하지만(반품 정책 문구도 800~1300자로 충분히 김),
readability4j가 실제 상품 설명이 아니라 페이지의 반복적인 공통 안내
영역(교환/반품/배송 정책)을 "본문"으로 선택하는 게 근본 원인으로
추정됨 - 아직 왜 그 블록을 고르는지(텍스트 밀도 기준 등 readability
알고리즘 내부 동작)까지는 분석 안 함.

**GPT 의견을 사용자가 가져옴 - "교환 및 반품" 같은 특정 문구를 막는
키워드 휴리스틱은 반영 안 하기로 결정.** 이유: 이런 상투구는
배송안내/이용약관/개인정보처리방침 등으로 계속 바뀔 수 있어서, 문구
하나씩 막는 건 이 프로젝트가 계속 피해온 "사례별 패치"에 해당함.
진짜 필요한 건 "본문이 아니라 공통 안내 영역인가"를 판별하는 더
일반적인 신호(운영 키워드 밀도, 주소/전화번호 비율, 문장 구조 등)인데,
2건만으로는 그 일반적 특징을 설계하기엔 근거가 부족함.

### Decision
**지금은 코드 수정 안 함** - 이 Finding만 기록. 같은 유형(공통
안내/약관 영역이 본문으로 오판되는 케이스)이 3~5건 정도 더 쌓이면
공통 특징을 분석해서 `ExtractionQualityEvaluator`를 일반화하는 방향
으로 재검토.

## 긴 쇼핑몰 URL/제목 500 에러 + failureReason 영속화 + 대형 오픈마켓 봇 차단 기록

실사용 중 쇼핑몰 URL(네이버 스마트스토어, 쿠팡) 스크랩 시 500 에러
발견. 원인: `Scrap.url`/`title`이 길이 지정 없어 Hibernate 기본값인
`VARCHAR(255)`로 생성됐는데, 추적 파라미터가 잔뜩 붙은 쇼핑몰 URL은
500자를 넘기 일쑤라 DB insert에서 `value too long` 에러로 크래시.

**Claude의 잘못된 안내 정정**: 처음에 "`ddl-auto=update`면 재시작
시 자동으로 컬럼 타입이 넓혀진다"고 안내했으나 틀림 - Hibernate의
`update` 모드는 새 테이블/컬럼 추가는 해줘도 **기존 컬럼의 타입
변경(ALTER COLUMN)은 안 해준다.** 실제 Postgres 컨테이너에 `\d scrap`
으로 직접 확인해서 여전히 VARCHAR(255)임을 확인 후, `ALTER TABLE
scrap ALTER COLUMN url/title TYPE TEXT`를 Claude가 직접 실행해서
해결(로컬 개발 DB, TEXT가 VARCHAR(255)의 상위호환이라 안전한 변경).
Java 엔티티도 `columnDefinition = "TEXT"`로 수정.

**다나와 사례로 봇 차단 진단 방법 확립**: 같은 URL이 curl은 200,
jsoup은 403 - 단순 User-Agent 문제가 아니라 요청 패턴(TLS/HTTP
클라이언트 핑거프린팅) 기반 차단으로 추정. IntelliJ 콘솔 로그에
직접 접근 못하는 상황에서, 임시 진단용 라이브 테스트를 만들어
`./gradlew liveTest`로 실행해서 정확한 `FailureReason`을 확인하는
방법을 확립(테스트 완료 후 파일 삭제) - `ExtractionResult`가 API
DTO에 안 노출되던 시절엔 이런 임시 테스트가 유일한 확인 수단이었음.

**GPT 의견 필터링**: 대형 오픈마켓(쿠팡/지마켓/네이버 스마트스토어/
다나와) 봇 차단 우회는 시도하지 않고 `docs/content_extraction.md`에
Known Limitation으로 기록 - 이미 있는 "robots.txt 우회 안 함" Non-goal
원칙과 일치, 사이트별 예외 처리가 계속 늘어나는 걸 피함. UI에 실패
사유 안내 메시지 추가하자는 제안은 반영하되, "필요하면 한 줄 설명을
입력해주세요"라는 문구는 뺌 - 실제로 스크랩 생성 후 userContext를
나중에 추가/수정하는 API가 없어서 안 되는 걸 된다고 안내하는 부정확한
문구였음.

**FailureReason이 애초에 Scrap 엔티티에 저장이 안 되고 있던 것도
이번에 발견** - `ExtractionResult.failureReason()`은 계산되지만
어디에도 영속화되지 않아서, 실패 원인을 사후에 API로 확인할 방법이
없었음(이번 다나와 진단 때 임시 테스트를 만들어야 했던 이유). PR #64
(`recommendedIslandId`)와 같은 패턴으로 생성자 대신
`recordFailureReason()` 메서드로 추가 - 기존 `new Scrap(...)` 호출부를
안 건드림.

### 버그 1건 (타이핑 누락)
`ScrapService.createScrap()`에서 `scrap.recordFailureReason(...)`
호출이 처음에 빠져서 `failureReason`이 계속 null로 나감 - 알려주고
사용자가 직접 추가.

### Result
`Scrap.url`/`title` TEXT로 확장(Java+DB 둘 다), `failureReason`
저장 및 `ScrapCreateResponse`/`ScrapDetailResponse`에 노출, UI에
실패 사유별 한국어 안내 메시지. 실제 봇 차단 URL(지마켓)로 재현해서
`failureReason: "ROBOTS_BLOCKED"`가 생성/조회 응답 둘 다에 정확히
나옴을 확인, 사용자도 실제 화면에서 메시지 확인.

### Decision
전부 커밋. Scrap Flow의 "실패도 정직하게 보여준다"는 원칙이 API
전반에 걸쳐 한 단계 더 완성됨.

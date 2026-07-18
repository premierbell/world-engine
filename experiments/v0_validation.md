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

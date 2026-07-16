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

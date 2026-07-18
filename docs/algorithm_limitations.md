# Algorithm Limitations

이 문서는 V0에서 발견한, 알고리즘 자체의 구조적 한계를 기록한다. Threshold를 더
튜닝해서 해결되는 문제가 아니라, 접근 방식 자체를 재검토해야 하는 발견들이 여기 들어간다.

> **Research Principle #001** (`experiments/v0_validation.md` 참고): World
> Engine은 사람이 미리 정의한 카테고리를 재현하는 것이 아니라, 반복적으로
> 관찰되는 의미 구조를 발견하고 이를 제품에 반영한다. 단, "반복 관찰"만으로
> Product Decision을 내리지 않는다 — 여러 독립적인 방법론에서 같은 결과가
> 나오고 그 원인까지 인과적으로 설명 가능할 때만 제품 결정으로 승격하고,
> 결과는 반복되지만 원인이 설명되지 않으면 Watch Metric으로 보류한다.
> Finding #002가 이 기준이 실제로 적용된 첫 사례다.

## Finding #001: Online Incremental Clustering은 입력 순서에 따라 다른 세계를 만든다 (Order Sensitivity)

### Claim
Island 편입 판단을 "새 스크랩 vs 가장 가까운 Island의 identity_vector, threshold
이상이면 병합"이라는 단일 규칙으로만 하면, threshold를 아무리 세밀하게 조정해도
"정확히 의도한 개수의 Island로 안정적으로 갈리는 구간"이 존재하지 않을 수 있다.

### Evidence 1 — Online Threshold Sweep (Experiment #8)
같은 데이터셋(`golden_dataset/threshold/topic/dataset.json`, 35개, Backend/AI/Sports
3개 도메인)에 대해 island_threshold를 0.24~0.34까지 올려가며 관찰:

| Threshold | Islands | 비고 |
|---|---|---|
| 0.24 | 2 | Backend+AI 뭉침, Sports만 분리 |
| 0.26 | 4 | Sports도 쪼개짐, 3개 도메인이 섞인 섬 등장 |
| 0.28 | 5 | Backend/AI/Sports 전부 부분적으로 쪼개짐 |
| 0.30 | 7 | |
| 0.32 | 9 | |
| 0.34 | 10 | |

**"언더분리(2개) → 정확히 3개 → 오버분리" 순서가 아니라, "언더분리 → 바로
오버분리"로 건너뛴다.** 정확히 3개(Backend/AI/Sports)로 깔끔하게 갈리는 threshold가
스윕 범위 안에 없었다. (돌이켜보면 threshold=0.24에서 항상 뭉치는 게 Backend+AI였다는
점은 Finding #002의 첫 단서이기도 했다.)

### Evidence 2 — Order Sensitivity Test (Experiment #9)
같은 threshold(0.24, 0.28)로 입력 순서만 5가지로 바꿔서(random seed 1~5) 실행:

- `island_threshold=0.24`: Island 개수가 **2~4개**로 요동침. 매번 Sports/AI/Backend가
  서로 다른 조합으로 섞임(seed 1은 Sports+AI+Backend가 한 섬에, seed 4는 Sports+AI가
  한 섬에).
- `island_threshold=0.28`: Island 개수가 **5~6개**로 요동침. 마찬가지로 어떤
  도메인이 어떤 도메인과 섞이는지도 매번 다름.

같은 threshold, 같은 데이터인데 **입력 순서만 바꿔도 Island 개수와 구성이
달라진다.** threshold 문제가 아니라 그리디(Greedy) 온라인 할당 자체의 순서
의존성 때문이다.

### Evidence 3 — Order Sensitivity v2, Pairwise F1 (Experiment #10)
island_threshold=0.24(baseline) 고정, 4가지 순서(그룹 순서 Backend→AI→Sports /
Sports→Backend→AI, 랜덤 셔플 seed=42 / seed=777)로 실제 정답 라벨 대비 Pairwise
F1을 계산:

| Order | Islands | F1 |
|---|---|---|
| Backend→AI→Sports | 4 | 0.610 |
| Sports→Backend→AI | 4 | 0.660 |
| Shuffle(seed=42) | 3 | 0.517 |
| Shuffle(seed=777) | 3 | 0.691 |

F1이 **0.517~0.691**로 17%p 가까이 흔들린다. **가장 유리한 조건(도메인별로 묶어서
순서대로 넣기)으로도 정확히 3개로 갈리지 않았다** — 그룹 순서 두 경우 모두 4개
Island가 나왔고 AI가 매번 여러 Island에 걸쳐 흩어졌다. 문제가 "입력 순서가
나빠서"가 아니라, 그리디 알고리즘이 가장 이상적인 조건에서도 3-도메인 구조를
복원하지 못한다는 더 강한 증거다.

### Evidence 4 — Greedy 개선 시도: Topic-First Assignment (Experiment #11)
Evidence 1~3까지는 전부 "지금 이 Greedy 구현(Island identity_vector 하나와만
비교)이 나쁘다"는 가설이었다. 이걸 반박하기 위해, Island 단위가 아니라 세상에
존재하는 **모든 Topic**과 먼저 비교하는 변형(`assign_scrap_topic_first`)을 만들어
같은 데이터셋·같은 32가지 순서(그룹 순서 2가지 + 랜덤 셔플 30가지, seed 1~30)로
Greedy(`assign_scrap`)와 나란히 비교했다.

| Algorithm | F1 mean | F1 std | F1 min | F1 max | Island 개수 최빈값 |
|---|---|---|---|---|---|
| Greedy (assign_scrap) | 0.595 | 0.085 | 0.459 | 0.829 | 3개 (32번 중 14번) |
| Topic-First | 0.647 | 0.084 | 0.515 | 0.825 | 2개 (32번 중 12번) |

F1 평균(0.595→0.647)과 최악의 경우(0.459→0.515)는 개선됐다. 하지만 **표준편차는
0.085→0.084로 사실상 그대로**다 — 입력 순서에 따라 결과가 흔들리는 정도 자체는
줄지 않았다. 게다가 Island 개수 최빈값이 3개(정답)에서 2개(언더분리)로
이동했다: Topic-First는 "Island 안의 Topic 중 단 하나라도 threshold를 넘으면
병합"하는 구조라 병합 문턱이 사실상 더 낮아지고, 그 결과 Greedy의
오버분리 편향을 언더분리 편향으로 바꿨을 뿐이었다.

**이 실험이 중요한 이유는 F1 숫자가 아니라 std가 안 움직였다는 사실이다.**
`principles.md`의 두 번째 원칙("세계는 안정적이어야 한다")은 "같은 데이터를
넣으면 같은 세계가 나와야 한다"는 뜻이고, std는 그 원칙을 직접 측정하는
지표다. Island 판단 기준을 (identity_vector 하나 → 모든 Topic)으로 완전히
바꿨는데도 이 지표가 그대로였다는 것은, 문제가 "무엇과 비교하는가"가 아니라
"언제, 어떤 순서로 결정을 내리는가"에 있다는 뜻이다.

### Evidence 5 — Offline HDBSCAN과의 비교 (Experiment #12)
Evidence 4(Topic-First)까지도 여전히 Greedy 계열(Online, Nearest-Neighbor
기반) 안에서의 변형이었다. 이번엔 아예 다른 계열 — 전체 데이터를 한 번에 보고
결정하는 offline 밀도 기반 클러스터링(HDBSCAN) — 을 같은 데이터셋, 같은 32가지
순서로 돌려 Greedy와 비교했다. `min_cluster_size`/`min_samples`를 함께
스윕해서(단일 파라미터만 올리면 밀도 조건도 같이 빡빡해져 전부 noise가 되는
현상을 확인 후 두 파라미터를 분리) baseline(`min_cluster_size=5,
min_samples=1`)을 찾았다.

| Algorithm | F1 mean | F1 std (order sensitivity) | Islands (mode/range) | Avg runtime |
|---|---|---|---|---|
| Greedy (assign_scrap) | 0.595 | 0.0840 | 3 (14/32) / 2-5 | 20.65ms |
| HDBSCAN (mcs=5, ms=1) | 0.721 | **0.0000** | 3 (32/32) / 3-3 | 4.60ms |

32가지 순서 전부에서 HDBSCAN은 정확히 동일한 3개 Island, 동일한 F1(0.721)을
냈다 — **표준편차가 정확히 0.0000.** Island 판단을 Online에서 Offline으로
바꾸자 순서 의존성이 완전히 사라졌다.

### Root Cause — 확정 (Experiment #12로 검증)
Evidence 4까지는 "Online Incremental Clustering이라는 접근 방식 자체의
성질일 가능성이 높다"는 추정이었다. Evidence 5는 이를 직접 검증한다: 같은
embedding, 같은 데이터셋에서 접근 방식만 Online → Offline으로 바꿨더니
variance가 정확히 0으로 떨어졌다. **순서 의존성의 원인은 Greedy 구현도,
비교 기준(Island vs Topic)도 아니라, "데이터를 하나씩 받아 그때그때
지역적으로 결정하는" Online Incremental Clustering이라는 접근 방식 자체였다는
것이 확정됐다.**

### Implication
Order Sensitivity는 offline 접근(전체 재클러스터링 또는 이를 포함하는
hybrid)으로 완전히 해결 가능하다는 근거가 확보됐다. 후보 A(지금 방식 유지)는
폐기한다 — variance가 존재한다는 것 자체가 `principles.md`의 "세계는
안정적이어야 한다" 원칙과 직접 충돌하기 때문이다. 남은 결정은 후보
C(offline로 완전 전환)와 D(Online 생성 + 주기적 offline 배치로 정리) 중
하나이며, 이 판단에는 Island가 "언제" 움직여도 되는가(Product 관점)가 함께
들어가야 한다 — 자세한 후보 비교는 Finding #002 이후 별도 절에서 다룬다.

### Status
**해결 (Resolved by Offline Clustering).** Order Sensitivity라는 현상 자체는
Experiment #12로 완전히 검증됐다. 다만 Evidence 5 실행 중 발견한 별도 문제
(HDBSCAN도 Backend와 AI를 분리하지 못함)는 이 Finding과 원인이 다르므로
Finding #002로 분리했다.

---

## Finding #002: Backend와 AI 사이의 경계가 원래 애매하다 (Semantic Boundary Ambiguity)

> 처음엔 "Domain Separation Failure"(알고리즘이 분리를 못 한다)로 이름 붙였다.
> Experiment #13 이후 이름을 바꿨다 — 문제는 알고리즘이 분리를 못 하는 게
> 아니라, **분리해야 한다는 전제 자체가 의심스럽다**는 쪽으로 무게가
> 옮겨갔기 때문이다. "Failure"는 정답이 있다는 걸 전제하지만, 지금 증거는
> 정답 자체(Backend와 AI가 별개의 Island여야 한다)를 의심하게 만든다.

### Claim
Backend와 AI 스크랩은 Greedy, Topic-First, HDBSCAN 세 가지 서로 다른 계열의
알고리즘 전부에서 하나의 Island로 뭉쳤다. 순서 의존성(Finding #001)과는 독립된
문제다. Experiment #13에서 golden dataset에 경계 사례(Vector DB, Spring AI 같은
콘텐츠)가 하나도 없는데도 순수 Backend/AI 콘텐츠끼리 이미 가깝다는 게 확인되면서,
원인이 알고리즘이 아니라 **두 도메인이 embedding 공간에서 애초에 하나의
연속체(continuum)에 가깝게 표현되어 있을 가능성**으로 좁혀졌다.

### Evidence 1 — Category 유사도 분포 (Experiment #2, Step 3)
Backend 8개/Sports 6개/AI 6개, 190쌍 비교에서 카테고리 내부 평균이 카테고리
간보다 높긴 했지만, **Backend 내부 유사도 범위(0.10~0.60)가 카테고리 간 평균과
겹칠 만큼 넓었다.** 당시엔 이걸 "Backend가 이미 여러 하위 Topic(Spring/Redis/
Kafka)으로 나뉘어 있다"는 뜻으로 해석하고 넘어갔다 — Topic Threshold를
분리하는 것으로 대응(`growth_rules.md` Topic Discovery Rule).

### Evidence 2 — 알고리즘 3종 전부에서 반복된 병합 (Experiment #8, #12)
| Algorithm | Backend/AI 관계 | 재현성 |
|---|---|---|
| Greedy (island_threshold=0.24, Experiment #8) | 뭉침 | 매번은 아니지만 최저 threshold에서 항상 뭉침 |
| Topic-First (Experiment #11) | 뭉침 경향 강화(언더분리 편향) | 32번 중 다수 |
| HDBSCAN (mcs=5, ms=1, Experiment #12) | **완전히 뭉침** (Backend 15 + AI 9 = 1개 cluster, Sports 10만 분리, AI 1개는 noise) | **32/32, 100%** |

세 알고리즘의 판단 방식(threshold 비교 / topic 우선 병합 / 밀도 기반)이
서로 완전히 다른데도 똑같은 두 도메인이 계속 뭉친다는 것은, 문제가 판단
로직이 아니라 **입력(embedding, 데이터셋)** 쪽에 있다는 강한 신호다.

### Evidence 3 — Topic-level Continuum 분석 (Experiment #13)
golden dataset을 다시 확인해보니 Backend 토픽은 Spring/JPA·Redis·Kafka,
AI 토픽은 LLM·RAG뿐이었다 — "Vector DB", "Spring AI" 같은 경계 사례가 하나도
없다. 즉 지금까지의 병합은 애매한 콘텐츠 때문이 아니라 **순수 Backend
콘텐츠와 순수 AI 콘텐츠끼리도 이미 가깝다**는 뜻이다. Experiment #2와 같은
방법론(내부/교차 평균 Cosine Similarity)을 이번엔 7개 Topic 단위로 재실행:

| Pair | 평균 유사도 |
|---|---|
| AI 내부 | 0.3829 |
| Backend 내부 | 0.3559 |
| Sports 내부 | 0.3246 |
| **AI ↔ Backend** | **0.2779** |
| AI ↔ Sports | 0.2057 |
| Backend ↔ Sports | 0.1911 |

AI↔Backend 교차 유사도(0.2779)는 AI↔Sports(0.2057)·Backend↔Sports(0.1911)보다
뚜렷하게 높다. "내부 유사도 − 교차 유사도" 간격도 Backend-AI 쌍에서만 유독
좁다(AI: 0.105, Backend: 0.078) — Sports와 비교할 때(AI: 0.177, Backend: 0.165)의
절반 수준이다.

Topic 단위로 더 들어가면 더 뚜렷하다: **Redis는 같은 Backend인 Spring/JPA보다
AI 토픽인 RAG에 더 가깝다** (Redis-Spring 0.286 < Redis-RAG 0.290). 경계
사례를 넣지 않았는데도, 순수 Redis 캐싱/Pub-Sub 콘텐츠만으로 이미 RAG 쪽과의
거리가 같은 Backend보다 가깝게 나왔다 — 실제로 Redis가 Vector Search/Semantic
Cache 인프라로 자주 쓰이는 것과 일치하는 결과다. Embedding이 우리가 붙인
"Backend"라는 이름표보다 **기술 스택의 실제 사용 맥락**을 학습하고 있는
것으로 보인다.

### Evidence 4 — Observation: Programming Domains Form a Large Semantic Cluster (Experiment #15)
Evidence 1~3까지는 전부 Backend-AI 두 도메인만 봤다. 이 관찰이 두 도메인만의
특수 현상인지 확인하려고 8개 도메인(AI/Backend/Cloud/Database/Security/Sports/
Finance/Science, 96개, 경계 사례 15개 포함 — `golden_dataset/semantic_atlas/
dataset.json`)으로 범위를 넓혔다. 목표는 정답을 맞히는 게 아니라 라벨 없이
embedding이 자연스럽게 만드는 구조를 그대로 관찰하는 것이었다(HDBSCAN,
`min_cluster_size=3, min_samples=1`, 관찰용 — F1 계산 없음).

**확인된 사실 (Evidence):**
- Programming 계열 5개 도메인(AI/Backend/Cloud/Database/Security)이 하나의
  클러스터로 뭉쳤다 — Cloud 12/12, Security 12/12, Backend 11/12, AI 10/12,
  Database 10/12가 같은 클러스터에 들어갔다(전체 96개 중 50개).
- Island 단위 평균 유사도에서도 이 5개 도메인은 서로 0.26~0.30대로 고르게
  묶이는 반면 Science(0.21~0.26)나 Sports와는 뚜렷하게 갈렸다(Backend의
  가장 가까운 이웃은 Cloud, Database의 가장 가까운 이웃은 Backend 등).
- 서로 다른 도메인(Science/Finance) 소속의 경계 사례 두 개 — Biology(AlphaFold/
  유전체 ML)와 Fintech/AI Trading — 가 하나의 작은 클러스터로 묶였다. Evidence
  3의 Redis↔RAG 패턴이 "AI가 응용된 콘텐츠는 원래 도메인과 무관하게 서로
  가까워진다"는 형태로 도메인을 넘어 재현된 것이다.
- Sports와 Finance 일부(Sports 6개 + Finance 5개)가 같은 클러스터에 들어갔다.

**Hypothesis (원인 미확정):**
Sports와 Finance가 같은 클러스터로 묶인 원인은 register(뉴스 기사체) /
vocabulary overlap / embedding model bias 중 하나 또는 복합일 가능성이 있다.
**현재 실험만으로는 원인을 특정할 수 없다** — 이 데이터셋의 Sports/Finance
텍스트가 둘 다 "~집중", "~전망한다" 같은 뉴스 리포트 톤으로 쓰인 반면 Programming
계열은 "~하는 방법을 정리한다" 같은 기술 블로그 톤이라는 점이 눈에 띄지만, 이건
관찰된 상관관계이지 검증된 원인이 아니다. 이 가설을 검증하려면 같은 내용을
서로 다른 register(뉴스/블로그/위키/요약문)로 다시 써서 클러스터가 유지되는지
비교하는 **Experiment #16(Register Control)**이 필요하다 — 아직 실행하지 않음.

문체 혼입이 반드시 "나쁜 신호"인 것도 아니다: World Engine이 실제로 다루는
사용자 스크랩도 뉴스/블로그/공식문서/GitHub README/논문이 섞여 있으므로,
Controlled Corpus(문체 통제)와 Natural Corpus(실제 사용 환경과 비슷한 혼합
문체) 평가를 구분해야 한다는 인사이트로 이어진다. 자세한 내용은
`evaluation_metrics.md`의 "Corpus Design" 절 참고.

### Evidence 5 — Register-independent Sports-Finance Clustering (Experiment #16)
Evidence 4의 Hypothesis(register 때문일 수 있다)를 직접 검증했다. 같은 24개
사실(Sports 12, Finance 12)을 뉴스 기사체/블로그체/위키 서술체/요약문체 4가지
register로 각각 다시 써서 동일 코퍼스를 4벌 만들고(`golden_dataset/
register_control/dataset.json`, 96개), register별로 Sports 내부/Finance
내부/Sports↔Finance 교차 유사도와 HDBSCAN 결과를 비교했다(`experiment_register_
control.py`).

| Register | Sports 내부 | Finance 내부 | Sports↔Finance | Gap | HDBSCAN |
|---|---|---|---|---|---|
| news | 0.299 | 0.270 | 0.242 | 0.028 | 병합됨 |
| blog | 0.325 | 0.317 | 0.257 | 0.061 | 병합됨 |
| wiki | 0.260 | 0.244 | 0.212 | 0.032 | 병합됨 |
| summary | 0.352 | 0.316 | 0.296 | 0.020 | 병합됨 |

**4개 register 전부에서 Sports와 Finance가 병합됐다.** Gap이 가장 작은(가장
잘 붙는) register는 news(0.028)가 아니라 오히려 가장 건조한 문체인
summary(0.020)였고, 감정·시제가 없는 wiki(정의체)에서도 여전히 병합됐다.
Gap 편차도 register 전체에서 0.020~0.061로 크지 않다.

### Rejected Hypothesis #1 — Register Contamination
**Claim**: Sports-Finance clustering is primarily caused by writing style
(register) — 즉 둘 다 뉴스 리포트 톤으로 쓰였기 때문에 가까워 보인다.
**Status: Rejected by Experiment #16.** Register를 뉴스→블로그→위키→요약문으로
완전히 바꿔도 결과가 변하지 않았다(4/4 병합). 이건 register가 원인이 아니라는
것을 보여주는 실험이지, "그래서 의미적으로 가깝다"를 증명하는 실험은 아니다 —
**실험이 증명한 범위는 "register만으로는 설명되지 않는다"까지다.** 왜 붙는지
(경쟁/순위/예측/통계/시장분석/시즌성 같은 공유 구조 때문인지)는 여전히
검증되지 않은 질문으로 남는다(아래 Root Cause 참고).

### Root Cause — 재구성 (Experiment #13, #15, #16 이후)
지금까지의 후보 목록(Embedding 품질 / Summary 품질 / Dataset 규모 / Domain
정의의 모호성)을 다시 보면, Evidence 3~5는 4번째 후보(Domain 정의 자체의
모호성)를 특히 강하게 지지한다. 7개의 독립적인 관찰 — Experiment #2(카테고리
유사도 분포), Threshold Sweep(Experiment #8), HDBSCAN(Experiment #12),
Pairwise Similarity와 Topic 분석(Experiment #13), Semantic Atlas(Experiment
#15), Register Control(Experiment #16) — 이 전부 같은 방향을 가리켰다는 것은
우연으로 보기 어렵다. 특히 Experiment #15는 이 현상이 Backend-AI 두 도메인만의
특수 사례가 아니라 **여러 도메인에서 반복되는 패턴**(Biology↔Fintech/AI
Trading)이라는 것을 보여줬고, Experiment #16은 그중 하나(Sports-Finance)가
적어도 register 때문은 아니라는 것까지 좁혔다.

**단, 이걸 "golden dataset의 라벨이 틀렸다"로 결론 내리면 안 된다.** Golden
dataset은 진실이 아니라 평가 기준(하나의 관점)이다. 대신 평가 자체를 두
층으로 분리해야 한다 — Canonical Taxonomy(사람이 정의한 라벨, 회귀 테스트용)와
Semantic Evaluation(embedding이 실제로 만드는 구조, 관찰용). 자세한 정의는
`evaluation_metrics.md`의 "Evaluation Layers" 절 참고.

**Sports-Finance가 왜 붙는지는 여전히 열린 연구 질문이다.** Register가
아니라는 것만 확인됐을 뿐, 원인이 실제 의미적 근접성이라고 단정할 근거는
아직 없다.

### Candidate Hypotheses (Unvalidated) — Sports-Finance 근접성의 원인 탐색
이 목록에 있는 항목은 **Finding #002의 Evidence가 아니다.** Evidence로
승격되려면 충분한 표본(N≈20~30)에서 재현되어야 한다 — 아래 항목들은 그
기준을 아직 통과하지 못했거나 검증 중이다.

- **경쟁/예측/통계/시장분석/시즌성** — Experiment #17(Semantic Factor
  Probe, 6개 후보 중 5개)에서 Sports+Finance보다 다른 도메인(주로 Database,
  Science)에 더 가깝게 나와 기각.
- **순위(Rank)** — Experiment #17에서 probe 1개(N=1)로 Specificity Gap
  +0.031을 보여 유력 후보였으나, **Experiment #18에서 같은 개념을 20가지
  phrasing(N=20)으로 재현 시도한 결과 평균 -0.0076, 95% CI [-0.036,
  +0.021]로 0을 포함 — 재현 실패.** N=1에서의 신호는 노이즈였을 가능성이
  높다. **Status: Rejected(재현 실패로 증거 없음).**
- **평점/레이팅(Rating)** — Experiment #18에서 Rank의 하위 개념군(Score/
  League/Standings/Leaderboard/Top N/Rating/Ranking/Index, 각 N=5)을 같이
  비교하던 중 발견. Mean Gap +0.0768(5개 중 4개 양수)로 8개 중 가장 강한
  신호였으나 N=5뿐이었다. **Experiment #19에서 25가지 phrasing(N=25)으로
  확장 재현한 결과 평균 +0.0063, 95% CI [-0.011, +0.023]로 0을 포함 —
  재현 실패.** Rank와 정확히 같은 패턴(소규모 표본 신호가 표본을 늘리자
  사라짐)이 두 번째로 재현됐다. **Status: Rejected(재현 실패로 증거 없음).**
- 나머지 Rank Family(Leaderboard +0.0082/4/5, Score/Standings/League는
  거의 0, Ranking -0.058/0/5, Index -0.068/1/5)는 Rating보다도 약해 시도할
  이유가 더 줄었다.

### Methodology Note — Single-Concept Probing 잠정 중단 (Experiment #19 이후)
Rank와 Rating이 연달아 같은 방식(N 확대 시 신호 소멸)으로 재현에 실패하면서,
**"Sports-Finance를 잇는 단일 latent concept이 하나 있을 것"이라는 실험
모델 자체를 의심해야 하는 지점에 왔다.** OpenAI 임베딩은 1536차원이고,
의미는 보통 특정 축 하나가 아니라 수백~수천 개 차원에 조금씩 걸쳐
표현된다 — Sports-Finance 근접성이 "경쟁성 축 하나"가 아니라 순위·추세·
확률·기록·성장/하락처럼 여러 미세한 요소가 합쳐진 결과라면, 단일 개념
probe로는 애초에 유의미한 신호가 잡히지 않을 수 있다.

**다음 후보 방법론(백로그, 아직 설계·실행 안 함): Lexical Ablation.**
추상적 probe 문장을 새로 만드는 대신, 실제 Sports/Finance 문장에서 구체
어휘를 한 단어씩 제거해가며(예: "손흥민이 득점했다" → "한 선수가 득점했다"
→ "개체가 결과를 만들었다") 유사도가 어떻게 변하는지 관찰하는 방식. 어떤
단어를 지웠을 때 Sports-Finance 유사도가 크게 떨어지는지를 보면 SHAP과
비슷한 방식으로 "무엇이 근접성을 만드는가"를 데이터 기반으로 좁힐 수 있다.
Concept Probing(Experiment #17~19)보다 정보량이 크지만, 아직 실행하지
않았고 우선순위도 재조정 대상이다(아래 Status 참고).

### Product Decision #002 — Finding #002는 버그가 아니라 발견이다 (Programming 한정)
Programming 5개 도메인이 하나로 뭉치고(Experiment #15), Sports-Finance도
반복적으로 가깝게 나오는(Experiment #2/#8/#12/#13/#15/#16) 현상을 놓고
"애초에 해결해야 할 결함인가, World Engine 철학이 실제로 작동한다는
증거인가"를 결정했다. **결론은 둘로 나뉜다 — Programming과 Sports-Finance는
증거의 "종류"가 다르기 때문이다.**

**Programming(AI/Backend/Cloud/Database/Security): 발견으로 채택.**
World Engine은 이 5개 도메인을 하나의 상위 의미 공간으로 취급하는 것을
허용한다. 정확히는 "AI와 Backend는 하나다"가 아니라 **"AI와 Backend를
억지로 분리하려 하지 않는다"**는 뜻이다. 근거:
- 서로 다른 6가지 방법론(카테고리 유사도-Experiment #2, Threshold
  Sweep-#8, Greedy/HDBSCAN-#12, Topic 분석-#13, 8도메인 Atlas-#15)이 전부
  같은 방향을 가리켰고, 인과적으로도 설명된다(Redis→RAG 벡터 검색,
  MCP→백엔드 API 노출 등).
- 이걸 억지로 갈라놓으려면 사람이 만든 규칙(온톨로지, 수동 override)이
  필요한데, 이는 "AI는 이해, 알고리즘은 결정" 원칙과 충돌한다. 오히려 이
  결과는 **"정확히 N개 도메인으로 갈려야 한다"는 canonical taxonomy
  전제 자체가 V1 설계에서는 틀렸을 수 있다**는 뜻이다.
- **Growth Rule과의 연결**: `growth_rules.md`의 City 형성 트리거("크기가
  아니라 밀도 — 다양성×연결성")가 Programming Island 내부에서 실제로
  관찰되는 Topic 다양성(Spring/Redis/Kafka/RAG/LLM/MCP…)과 정확히
  일치한다. Finding #002는 이 Growth Rule을 실험적으로 뒷받침하는 첫
  사례다 — Island가 하나로 뭉치더라도 내부 Topic이 뚜렷하게 남아있어야
  "성장이 체감 가능하다"(Product Principle)는 원칙을 지킬 수 있다.
- **한계 (반드시 같이 기록)**: 이 결정은 절대 진리가 아니라 현재 실험
  범위(8개 도메인)에서 반복 관찰된 현상이다. 나중에 Design/DevOps/Math/
  GameDev/Embedded/CAD/Robotics 같은 도메인이 추가되면 Programming
  Island가 다시 둘 이상으로 갈라질 수 있다 — 그건 실패가 아니라 World
  Engine이 "정해진 섬을 유지하는 시스템"이 아니라 "데이터가 보여주는
  섬을 발견하는 시스템"이라는 증거다.
- **표현 수정 (Experiment #22 이후)**: "Programming = 항상 하나의 Mega
  Island"라고 쓰지 않는다. Backend User(Experiment #21)에서는 실제로
  하나의 Island로 수렴했지만, AI Researcher(Experiment #22)에서는 같은
  Programming 상위 공간 안에서도 Foundation Model(Transformer/RLHF/
  Diffusion)과 Application AI(Agent/Prompt Engineering/Evaluation) 같은
  여러 하위 의미 공간이 offline HDBSCAN에서 뚜렷이 분리됐다. 정확한
  표현은: **"Programming은 하나의 상위 의미 공간이며, 실제 Island
  구성은 사용자의 관심 밀도에 따라 하나 또는 여러 개의 하위 의미
  공간으로 나타날 수 있다."** `growth_rules.md`의 City 개념과 연결하면
  Programming City 안에 Backend District/Infrastructure District/
  Foundation Model District/Agent District처럼 여러 District가 있는
  구조에 가깝다 — 자세한 원인은 Finding #003 참고.

**Sports-Finance: Watch Metric #001로 보류, 제품 설계에 반영하지 않음.**
Programming과 달리 결과는 반복되지만(Experiment #2/#8/#12/#13/#15/#16)
원인은 설명되지 않는다(Experiment #17~19, Concept Probing 2회 실패,
95% CI가 매번 0을 포함). "결과 반복 + 설명 가능"과 "결과 반복 + 설명
불가"는 제품이 신뢰할 근거로 다르게 취급해야 한다 — V1 출시 후 실제
사용자 데이터에서도 동일 패턴이 반복되는지 지속 관찰하고, synthetic
golden dataset의 결과만으로 제품 동작을 결정하지 않는다.

자세한 기록은 `experiments/v0_validation.md`의 "Product Decision #002",
"Watch Metric #001", "Research Principle #001" 참고.

### Status
Programming 부분은 **Resolved(Product Decision #002로 승격)**. Sports-Finance
원인은 여전히 미해결(Open)이지만 우선순위가 낮아졌다 — Watch Metric으로
보류됐으므로 당장 더 팔 필요는 없다. 향후 백로그(우선순위 미정):
1. **Lexical Ablation (백로그, 미설계)** — Concept Probing보다 정보량이
   큰 대안 방법론. Sports-Finance 원인을 더 파고 싶어지면 이 방향으로.
2. **Human Labeling Study(inter-rater agreement)** — Kafka/Redis/Spring/JPA/
   RAG/LLM/Prompt Engineering/Vector DB 같은 스택을 사람에게 직접 분류하게
   했을 때도 의견이 갈리는지 확인. 사람들끼리도 정답이 갈린다면 Pairwise F1
   자체를 절대 지표로 쓸 수 없다는 뜻이므로, Semantic Evaluation의 근거가 더
   강해진다.

---

## 후보 비교: Order Sensitivity를 해결할 아키텍처는 C인가 D인가

Finding #001이 Resolved로 바뀌면서, 남은 선택은 다음 두 후보로 좁혀졌다:
- **C. Offline 전환**: Island 배치를 전부 offline 클러스터링(HDBSCAN 등)으로
  대체
- **D. Hybrid (Online 생성 + Night Batch)**: 스크랩 저장 시 즉시 Island가
  성장하는 Online 경험은 유지하고, 별도 주기적 배치가 Island를 정리
  (merge/split)

C는 철학적으로 걸리는 지점이 있다: `vision.md`의 "사용자는 씨앗만 심는다 →
AI는 의미를 이해한다 → 알고리즘은 세계를 성장시킨다"라는 흐름과
`principles.md`의 "세계는 안정적이어야 한다"를 같이 놓고 보면, 스크랩을
저장할 때마다(또는 일정 주기로) **전체를 다시 계산해서 기존 섬 위치가
바뀔 수 있는 구조**는 그 자체로 새로운 종류의 불안정성이다 — Order
Sensitivity는 없앴지만 "재계산 시점마다 세계가 달라질 수 있다"는 문제로
바뀔 뿐일 수 있다.

D는 "낮에는 실시간 성장(Online), 밤에는 세계 정리(Batch)"로 두 요구를
분리한다 — 사용자가 스크랩을 저장하는 순간의 즉각적 피드백(Online)은
유지하면서, 잘못 배치된 섬을 정리하는 책임은 사용자가 보지 않는 시점(배치)에
분리해서 진다. **D를 Night Batch v0(Merge-only)로 실제 프로토타이핑해서
검증했다(Experiment #21/#22)** — Backend User에서는 fragmentation을
완전히 해소했지만, AI Researcher에서는 Merge만으로 부족하다는 것도
확인됐다(Finding #003). D 방향 자체는 유지하되, Merge 외에 Split이
추가로 필요하다는 것이 다음 구현 목표다.

---

## Finding #003: Merge-only Hybrid는 Online 단계에서 이미 과병합된 Island를 고치지 못한다

### Claim
Night Batch v0(Merge-only)는 "여러 Island로 쪼개진(fragmented) 상태"는
효과적으로 고치지만, "이미 하나로 지나치게 뭉친(over-merged) Island"는
고치지 못한다. Merge는 서로 다른 Island를 합치는 연산이라, Island 하나
내부가 이미 여러 의미 공간을 담고 있는 문제에는 애초에 적용할 수 없다 —
이 경우엔 Split이 필요하다.

### Evidence — Backend User vs AI Researcher (Experiment #21/#22)
같은 방법론(71개 스크랩, Day 1/7/30, Online-only → Night Batch v0)을 두
페르소나에 적용:

| Persona | Online-only Island 수 | +Night Batch | Topic 중복률 (Before→After) |
|---|---|---|---|
| Backend User (#21) | 5 | **1** | 88.9% → **0.0%** |
| AI Researcher (#22) | 7 | 6 | 77.8% → **77.8%(변화 없음)** |

Backend User는 Merge-only만으로 완전히 해소됐지만, AI Researcher는 거의
그대로였다. 원인을 추측 대신 직접 관찰했다(Experiment #22, 파라미터는
건드리지 않고 구조만 관찰):

- offline HDBSCAN이 AI Researcher의 71개 스크랩에서 **10개 클러스터 +
  Noise 20개(28%)**를 만들었고, 각 클러스터가 원래 실제 Topic과 거의
  1:1로 대응했다(`#0=Transformer`, `#1=VectorDB`, `#4=Diffusion`,
  `#6=RLHF` 등 대부분 순수 클러스터). Backend User 때 HDBSCAN이 9개
  Topic을 **하나의** 클러스터로 몰아준 것과 정반대다.
- Online 단계에서 이미 9개 Topic이 전부 섞여버린 거대 Island(#0)의
  purity가 **0.20**밖에 안 됐다 — 어떤 단일 HDBSCAN 클러스터와도 강하게
  안 맞는다는 뜻이다. Night Batch가 이 Island를 다른 Island와 합치지
  않은 건 버그가 아니라 **Minimum Change Principle(Invariant #5)이
  의도대로 애매한 후보를 걸러낸 것**이다.

### Root Cause
Merge-only는 "offline 클러스터가 Online Island들의 합집합"이라고
암묵적으로 가정한다. 하지만 Online Island가 처음부터 여러 의미 공간을
담고 있으면(Finding #001의 과병합), offline 정제에 필요한 연산은 Merge가
아니라 Split이다 — 서로 다른 Island를 합치는 연산으로는 하나의 Island
내부를 쪼갤 수 없다.

### Implication
- Backend User와 AI Researcher의 차이는 데이터 품질 문제가 아니라, **두
  페르소나의 관심사 자체가 다른 구조를 갖고 있다는 증거**다 — Backend
  User의 9개 Topic은 실제로 하나의 조밀한 의미 공간(Programming
  Mega Island)을 이루지만, AI Researcher의 9개 Topic은 Foundation
  Model(Transformer/RLHF/Diffusion)과 Application AI(Agent/Prompt
  Engineering/Evaluation) 등 여러 자연스러운 하위 공간으로 이미 갈라져
  있다. Product Decision #002의 "Programming = 하나의 상위 의미 공간"은
  유지하되, "항상 하나의 Island"라는 표현은 위 Product Decision #002
  절의 "표현 수정" 항목으로 완화했다.
- Hybrid Architecture(Step 5.5)의 다음 구현 목표는 **Split**이다 — Merge는
  "언제 효과가 있는지(fragmentation)"와 "언제 아무것도 안 하는 게
  맞는지(genuinely ambiguous)"를 이미 증명했으므로, 남은 공백은 "Online
  단계에서 만들어진 과병합 Island를 어떻게 쪼갤 것인가"뿐이다.

### Status
**Resolved (Need Split).** 원인은 명확히 규명됐다 — Merge-only의 한계가
아니라 설계된 범위(Merge)를 벗어난 문제였다는 것이 확인됐다. Split을
실제로 구현해서 검증한 결과는 Finding #004에서 이어진다.

---

## Finding #004: Pairwise Threshold Graph는 Chaining에 취약하다

### Claim
"Topic(또는 Scrap) 쌍의 유사도가 threshold를 넘으면 연결한다"는 단순
pairwise threshold + Union-Find(또는 Greedy) 방식은, 밀도가 높은 "허브"
노드 하나만 있어도 원하지 않는 거대 Component로 체이닝(chaining)된다.
이건 Topic 레벨에서 새로 발견된 문제가 아니라 **Scrap 레벨(Experiment
#6~7)에서 이미 겪은 문제가 같은 구조로 재현된 것**이다 — 단일 threshold +
naive connectivity라는 알고리즘 클래스 자체의 특성이지, 특정 구현의 버그가
아니다.

### Evidence 1 — Scrap 레벨 (Experiment #6~7, 재해석)
V0 초기 Threshold Sweep에서 "언더분리 → 정확히 3개 → 오버분리"로 이어지는
안정적인 구간이 없었다(Finding #001 Evidence 1). 당시엔 이걸 "Greedy
Online의 순서 의존성" 문제로만 분류했지만, 돌이켜보면 **단일 threshold로
연결 여부를 정하는 방식 자체**가 원인의 일부였다 — HDBSCAN(밀도 기반)으로
바꾸자 이 불안정성이 정확히 0으로 사라졌다(Finding #001 Evidence 5,
Experiment #12).

### Evidence 2 — Island 단위 Split의 Local 한계 (Experiment #23)
Finding #003 이후 구현한 Split(`find_split_candidates`/`apply_split`)을
AI Researcher에 적용하자 Topic Duplication Rate가 오히려 77.8%→88.9%로
악화됐다 — 분리 대상 Island 하나만 보고 판단해서, 이미 존재하는 다른
Island와 겹치는 조각을 새로 만들어냈다. Split 직후 Island 단위 재-Merge를
시도했지만 효과가 없었다 — 기존 Island들 자체가 이미 여러 실제 주제가
섞인 애매한 다수결 라벨을 가진 상태라, Island 단위 비교로는 새로 떨어진
조각과 서로를 못 찾는다. 이 실패가 "Island를 기본 단위로 삼은 것 자체가
문제"라는 재설계(`hybrid_architecture.md` "Night Batch v2")로 이어졌다.

### Evidence 3 — Topic 레벨 Chaining (Experiment #24)
Island 대신 Topic을 기본 단위로 삼은 Topic Graph Reconstruction(모든
Topic 쌍의 유사도로 그래프를 만들고 Union-Find로 Connected Component를
Island로 재구성)을 Backend User/AI Researcher에 적용, edge_threshold를
0.24~0.60까지 스윕:

| Threshold | Backend User | AI Researcher |
|---|---|---|
| 0.24~0.35 | 1개, 중복 0% | 1개, 중복 0% |
| 0.40 | 3개, 중복 2/9 | 3개, 중복 1/9 |
| 0.45 | 7개, 중복 3/9 | 8개, 중복 4/9 |
| 0.50 | 10개, 중복 5/9 | 13개, 중복 5/9 |
| 0.55~0.60 | 13~15개, 중복 5~7/9 | 21~22개, 중복 7/9 |

두 페르소나가 거의 동일하게 움직인다 — "전부 하나"에서 "전부 쪼개지며
중복도 같이 증가"로 바로 건너뛰고, Backend(1개가 정답)와 AI
Researcher(여러 개가 정답에 가까움, Finding #003 참고)를 동시에 만족하는
안정적인 중간 구간이 없다. 원인은 RLHF 같은 "허브" Topic이 여러 다른
Topic과 동시에 높은 유사도를 가져서, A-B와 B-C가 각각 threshold를 넘으면
A-C가 안 닮았어도 Union-Find가 셋을 하나로 묶어버리는 체이닝이다.

### Root Cause
같은 문제가 세 번(Scrap Greedy+Threshold, Island Split의 local-only 판단,
Topic Union-Find+Threshold) 다른 층위에서 반복됐다 — **문제는 특정
구현이 아니라 "단일 threshold + naive pairwise connectivity"라는 접근
방식 자체다.** 이 접근은 전역 밀도 구조를 못 보고 지역적인(local) 연결
여부만 보기 때문에, 체인처럼 이어지는 경로가 하나만 있어도 서로 안 닮은
것들이 전부 하나로 묶인다. HDBSCAN 같은 밀도 기반 방법이 Scrap
레벨에서 이 문제를 해결했던 것(Finding #001)과 정확히 같은 이유로,
Topic 레벨에서도 밀도 기반 방법이 필요하다.

### Implication
Union-Find(단일 threshold)를 그대로 쓰는 대신, **Topic-level HDBSCAN**으로
교체하는 것이 다음 실험/구현 목표다 — Experiment #22에서 HDBSCAN이 AI
Researcher의 scrap 레벨 구조를 실제로 잘 나눠줬던 방법론을 이번엔 Topic
레벨(더 적고 밀도 높은 데이터 포인트)에 그대로 적용한다. 순서(Threshold
Graph 실험 → 체이닝 발견 → Finding #004 → 그래서 밀도 기반으로 교체)를
먼저 밟았기 때문에, "왜 이번에도 HDBSCAN을 쓰는가"에 대한 근거가
분명하다 — 이유 없이 HDBSCAN을 재사용하는 게 아니라, 단순한 방법이
실패하는 걸 직접 확인한 뒤의 선택이다.

### Status
**업데이트 (Experiment #25)**: Topic-level HDBSCAN을 두 가지 변형(Topic
centroid 직접 클러스터링 / scrap 레벨 HDBSCAN 라벨로 Topic 재그룹화)으로
시도했지만 **둘 다 Backend User마저 악화시켰다**(최선의 경우도 7개
Island/4~9 중복 — 원래 Merge-only의 1개/0%보다 나쁨). 원인은 체이닝이
아니라 더 근본적인 문제였다 — Finding #005 참고. Finding #004
자체(pairwise threshold의 체이닝)는 여전히 유효한 관찰이지만, 그
대안(Topic-level HDBSCAN)도 실패하면서 문제가 "어떤 알고리즘을 쓰는가"가
아니라는 게 분명해졌다.

---

## Finding #005: Aggregation Level Trade-off — Island 단위와 Topic 단위는 반대 방향으로 실패한다

### Claim
Night Batch의 의사결정을 Island 단위로 하느냐 Topic 단위로 하느냐는 단순한
구현 선택이 아니라 **Stability ↔ Resolution 트레이드오프**를 만든다. Island
단위는 여러 Topic의 스크랩을 뭉뚱그려 판단하기 때문에 embedding noise가
평균화되어 안정적이지만, 그만큼 해상도가 낮아서 진짜 여러 의미 공간이 섞인
Island(AI Researcher의 과병합)를 못 알아본다. Topic 단위는 해상도가 높아
이론적으로는 더 정확할 수 있지만, 단위당 표본(스크랩)이 너무 적어서
embedding noise가 오히려 증폭된다.

### Evidence — 오늘 시도한 4가지 접근의 정리
| 접근 | 단위 | Backend User | AI Researcher |
|---|---|---|---|
| Merge-only (Experiment #21) | Island | 1개, 0% (안정적) | 6개, 77.8% (과병합 못 고침) |
| Split + 재-Merge (Experiment #23) | Island | 후보 없음(정상) | 8개, 88.9%(악화) |
| Topic Graph, Union-Find (Experiment #24) | Topic | 안정 구간 없음(체이닝) | 안정 구간 없음(체이닝) |
| Topic HDBSCAN, 변형 A/B (Experiment #25) | Topic | 최선 7개, 4~9/9 (Merge-only보다 나쁨) | 최선 5개, 2/9 (개선됐지만 대가가 큼) |

겉보기에 4가지는 서로 다른 알고리즘(Merge, Split, Union-Find Graph,
HDBSCAN)이지만, 전부 "Island 단위냐 Topic 단위냐"라는 하나의 축 위에
있다. Island 단위는 항상 Backend User에서 강했고 AI Researcher에서
약했다. Topic 단위는 그 반대 방향으로 실패했다(AI Researcher는 개선
여지가 있었지만 Backend User가 오히려 나빠짐) — 정확히 반대 방향의
실패라는 게 이 Finding의 핵심 증거다.

### Root Cause
표본 크기 문제다. Island는 평균 10~15개 스크랩을 담고 있어 평균화 효과가
크지만, 이 프로젝트의 온라인 단계는 Topic을 21~27개까지 잘게 만들어서
(71개 스크랩 기준 Topic당 평균 3개 미만) Topic 단위 통계는 노이즈에
취약하다. Scrap 레벨 HDBSCAN 자체도 Backend User를 완벽한 1개 클러스터로
안 만든다("58+7+noise 6") — Island 단위 다수결에서는 이 노이즈가
평균화되어 가려지지만, Topic 단위로 내리면 그대로 드러난다.

### Implication
지금까지의 질문("어떤 Merge/Split/Graph 알고리즘이 더 나은가")은 잘못된
질문일 수 있다. 진짜 질문은 **"Night Batch가 어느 계층(Scrap/Topic/
Island)에서 의사결정을 내려야 하는가"**다. 그리고 이 질문 뒤에는 더 근본적인
질문이 있다:

> **Open Question**: Night Batch의 본질은 "더 좋은 클러스터링을 찾는 것"인가,
> 아니면 "문제가 있는 Island만 최소한으로 수정하는 것"인가?

지금까지의 모든 Night Batch 버전(v0 Merge/Split, v1 Union-Find Topic
Graph, v2 Topic HDBSCAN)은 암묵적으로 "세계 전체를 다시 평가한다"고
가정했다. 하지만 Backend User는 애초에 Online 결과가 이미 좋았는데,
Night Batch가 이걸 다시 건드리면서 오히려 나빠진 사례가 여러 번
나왔다(변형 A/B 둘 다). **"전체 재구성"이 아니라 "의심스러운(purity가
낮은) Island만 선택적으로 재평가"하는 방향이 다음 후보다** — 아직
설계되지 않았다.

### Status
미해결 (Open). 다음 세션은 구현이 아니라 **설계 세션**으로 시작한다 —
위 Open Question에 답하는 것이 Experiment #26 이전에 먼저 필요하다.

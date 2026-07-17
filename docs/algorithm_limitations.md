# Algorithm Limitations

이 문서는 V0에서 발견한, 알고리즘 자체의 구조적 한계를 기록한다. Threshold를 더
튜닝해서 해결되는 문제가 아니라, 접근 방식 자체를 재검토해야 하는 발견들이 여기 들어간다.

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
  신호였으나 **N=5뿐이다** — Rank가 N=1→N=20에서 겪은 것과 같은 함정에
  빠지지 않으려면 N≈20~30으로 확장 재현해야 한다. **Status: UNVALIDATED.
  Reason: Observed on N=5 only; requires larger corpus.** (다음 실험
  후보 — Experiment #19, 미실행)
- 나머지 Rank Family(Leaderboard +0.0082/4/5, Score/Standings/League는
  거의 0, Ranking -0.058/0/5, Index -0.068/1/5)는 Rating만큼 두드러지지
  않아 우선순위가 낮다.

### Status
미해결 (Open) — 질문이 두 단계로 계속 좁혀지고 있다. Backend-AI 단계에서는
"왜 알고리즘이 못 가르는가"에서 "**Backend와 AI를 반드시 서로 다른 Island로
봐야 하는가**"로 바뀌었고, Sports-Finance 단계에서는 Experiment #16으로
"문체 축"이 닫히고 Experiment #17~18로 "순위(Rank)" 가설도 재현 실패로
닫히면서, "**Rating이 재현되는가**"라는 더 구체적인 질문만 남았다. 향후
실험 백로그:
1. **Experiment #19 (미실행)** — Rating corpus를 N≈20~30으로 확장해
   재현성 검증. 재현되면 Finding #002의 Evidence로 승격, 재현되지 않으면
   Rating도 기각하고 새로운 의미 축(Rank Family 밖)을 탐색.
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
분리해서 진다. 현재는 **D 쪽으로 무게가 기울어 있으나, 아직 D를 실제로
프로토타이핑해서 검증한 실험은 없다** — 다음 실험 후보로 남겨둔다.

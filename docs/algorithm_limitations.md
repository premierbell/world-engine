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

## Finding #002: Backend와 AI 도메인이 어떤 알고리즘으로도 분리되지 않는다 (Domain Separation)

### Claim
Backend와 AI 스크랩은 Greedy, Topic-First, HDBSCAN 세 가지 서로 다른 계열의
알고리즘 전부에서 하나의 Island로 뭉쳤다. 순서 의존성(Finding #001)과는 독립된
문제로, 원인이 알고리즘이 아니라 **embedding 공간에서 두 도메인이 애초에
충분히 분리되어 있지 않을 가능성**을 가리킨다.

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

### Root Cause (미확인 — 후보만 존재)
Order Sensitivity와 달리 아직 원인을 좁히지 못했다. 후보:
1. Embedding 품질 — `text-embedding-3-small`이 이 두 도메인의 의미 차이를
   충분히 반영하지 못할 가능성
2. Summary 품질 — Product Decision #001(Summary를 기본 입력으로 사용)의
   summary 생성 프롬프트/방식이 두 도메인을 흐리게 만들 가능성
3. Golden Dataset 규모 — Backend/AI 각각 5~10개뿐이라 통계적으로 판단하기엔
   너무 작을 가능성
4. Domain 정의 자체의 모호성 — "LLM을 이용한 백엔드 개발" 같은 경계 사례가
   애초에 사람이 봐도 Backend인지 AI인지 애매할 가능성 (`golden_dataset` 백로그에
   이미 있던 우려와 연결)

### Status
미해결 (Open). Finding #001과 달리 알고리즘을 바꿔서 해결되는 문제가 아니라는
것까지는 확인됐다. 다음 조사는 알고리즘이 아니라 데이터 쪽 — golden dataset의
Backend/AI 샘플을 사람이 직접 다시 읽고 "정말 서로 다른 도메인인가"부터
재검토하는 것에서 시작해야 한다.

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

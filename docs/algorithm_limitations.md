# Algorithm Limitations

이 문서는 V0에서 발견한, 알고리즘 자체의 구조적 한계를 기록한다. Threshold를 더
튜닝해서 해결되는 문제가 아니라, 접근 방식 자체를 재검토해야 하는 발견들이 여기 들어간다.

## Finding #001: 단일 Global Threshold + Online Greedy Nearest-Neighbor는 안정적인 Domain Partition을 보장하지 못한다

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
스윕 범위 안에 없었다.

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

### Root Cause (Experiment #11로 일반화)
Nearest Neighbor + Threshold는 각 스크랩이 들어올 때마다 "지금까지 만들어진
Island들" 중 하나를 지역적(local)으로 선택하는 방식이라, 전체 구조(Global
Structure)를 보지 못한다. 어떤 스크랩이 먼저 들어와서 어떤 Island의 identity를
결정짓느냐에 따라 이후 흐름 전체가 달라진다. Offline Pairwise 실험(Experiment
#6/#7)은 이런 순서 의존성이 아예 없는 문제였기 때문에, 그 결과를 Online
알고리즘에 그대로 적용할 수 없었다.

Experiment #11 이전까지 이 Root Cause는 "이 Greedy 구현의 결함"이라는 가설
수준이었다. Evidence 4는 판단 기준을 Island 단위에서 Topic 단위로 완전히
바꿔도 variance가 그대로라는 것을 보였으므로, 이제는 더 강하게 주장할 수 있다:

**순서 의존성은 특정 구현의 버그가 아니라, "데이터를 하나씩 받아 그때그때
지역적으로 결정하는" Online Incremental Clustering이라는 접근 방식 자체의
성질일 가능성이 높다.** Threshold를 바꾸거나(Evidence 1) 비교 대상을
바꾸는(Evidence 4) 정도로는 해결되지 않고, "언제 결정을 내리는가"(스크랩이
들어올 때마다 즉시 vs 일정 주기로 전체를 다시 봄) 자체를 바꿔야 할 가능성이
크다.

### Implication
Threshold를 더 촘촘히 찾거나(Evidence 1) Greedy의 비교 기준을 바꾸는
것(Evidence 4)은 이 시점부터 의미가 크게 줄어든다. 지금까지는 온라인
알고리즘 하나만 있어서 비교 대상이 없었으므로, 다음 실험은 **같은
데이터셋·같은 embedding에 offline 밀도 기반 클러스터링(HDBSCAN 등,
Experiment #12)을 돌려 Greedy와 나란히 비교하는 것**이다 — F1, order
sensitivity(변경 시 std가 0이 될 것으로 예상), Island 개수, 실행 시간을 같은
표로 비교한다. 후보는 여전히 4가지이지만, 이제는 추측이 아니라 실험 결과로
고른다:
1. 지금 방식 유지 + 한계를 문서화하고 감내
2. 일정 주기(예: 스크랩 N개)마다 전체 재클러스터링
3. 밀도 기반(HDBSCAN 등) offline 클러스터링으로 전환 — **다음 실험(#12) 대상**
4. Online은 "생성"만 담당하고, 별도 배치(Batch) Job이 주기적으로 Merge/Split을
   수행 ("낮에는 빠른 결정, 밤에는 세계 정리") — HDBSCAN도 한계가 있다면 남는
   유일한 후보

### Status
미해결 (Open). V0의 성과는 "좋은 threshold를 찾았다"가 아니라 "이 접근 방식의
한계를 실험으로 증명했다"는 것이며, Experiment #11은 그 한계가 특정 구현이
아니라 접근 방식 자체에 있다는 것까지 증명했다.

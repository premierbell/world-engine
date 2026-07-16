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

### Root Cause (가설)
Nearest Neighbor + Threshold는 각 스크랩이 들어올 때마다 "지금까지 만들어진
Island들" 중 하나를 지역적(local)으로 선택하는 방식이라, 전체 구조(Global
Structure)를 보지 못한다. 어떤 스크랩이 먼저 들어와서 어떤 Island의 identity를
결정짓느냐에 따라 이후 흐름 전체가 달라진다. Offline Pairwise 실험(Experiment
#6/#7)은 이런 순서 의존성이 아예 없는 문제였기 때문에, 그 결과를 Online
알고리즘에 그대로 적용할 수 없었다.

### Implication
Threshold를 더 촘촘히(0.27, 0.29, ...) 찾는 것은 이 시점부터 의미가 크게
줄어든다. 대신 알고리즘 구조 자체를 바꾸는 옵션을 검토해야 한다 (후보들은 논의
중, 아직 결정 안 함):
1. 지금 방식 유지 + 한계를 문서화하고 감내
2. 일정 주기(예: 스크랩 N개)마다 전체 재클러스터링
3. 밀도 기반(HDBSCAN 등) offline 클러스터링으로 전환
4. Online은 "생성"만 담당하고, 별도 배치(Batch) Job이 주기적으로 Merge/Split을
   수행 ("낮에는 빠른 결정, 밤에는 세계 정리")

### Status
미해결 (Open). V0의 성과는 "좋은 threshold를 찾았다"가 아니라 "이 접근 방식의
한계를 실험으로 증명했다"는 것이다.

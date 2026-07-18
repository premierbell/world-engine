# Hybrid Architecture (Step 5.5)

> **업데이트 (Finding #006 이후)**: 이 문서의 Night Batch v0~v3(Merge/
> Split/Topic Graph/HDBSCAN/Selective) 설계는 **`docs/anchor_model.md`로
> 대체됐다.** v0~v3는 전부 "Greedy가 만든 Topic/Island를 입력으로 고친다"는
> 전제를 가졌는데, Finding #006에서 이 전제 자체가 틀렸다는 게 드러났다 —
> Greedy Online은 Preview UX일 뿐이고 확정은 Night Batch(Anchor 형성)에서만
> 일어나야 한다는 게 Anchor Model의 결론이다. 이 문서는 그 결론에 이르기까지의
> 실험 근거(Finding #003/#004/#005)로 남겨둔다.

Finding #001(Order Sensitivity, Resolved by Offline Clustering)과 Product
Decision #002(Programming은 하나의 상위 의미 공간으로 취급 허용) 이후 남은
가장 큰 미결정 사항 — "사용자가 스크랩하면 즉시 어디에 배치하고, 언제 다시
정리하는가" — 를 확정하는 문서다. 이 결정에 따라 Data Model, Event Flow,
API, Label 갱신 시점이 전부 함께 정해지므로, Step 6(Label Generation)보다
먼저 다룬다.

후보 C(offline 완전 전환)와 D(Online 생성 + Night Batch 정리) 중 D를
채택한다 — C는 재계산 시점마다 기존 섬 위치가 바뀔 수 있어 그 자체로 새로운
불안정성을 만들지만, D는 "낮에는 실시간 성장, 밤에는 세계 정리"로 즉각성과
정확성을 분리할 수 있다.

## Core Split: Online = 즉각성, Night = 보수(Maintenance)

**Online의 역할은 정확성이 아니라 즉각적 피드백이다.** Finding #001에서
확인된 Greedy의 순서 의존성을 Online 배치가 그대로 안고 있어도 괜찮다 —
이건 "최종 정답"이 아니라 "임시 배치"이기 때문이다.

**Night Batch의 역할은 세계를 새로 만드는 것이 아니라 보수하는 것이다.**
HDBSCAN 같은 offline 클러스터링은 "최종 결과"가 아니라 "판단을 위한 참고
자료"로만 쓴다 — Island 7개를 HDBSCAN이 6개가 이상적이라고 제안해도,
기존 구조를 거의 유지하면서 경계 Topic 하나만 옮겨도 품질 차이가 크지
않다면 후자를 선택한다(Invariant #5, Minimum Change Principle 참고). 이
태도 전환이 Hybrid를 단순 "온라인+배치"가 아니라 World Engine의 철학("세계는
안정적이어야 한다")을 가진 아키텍처로 만든다.

## Online Flow (낮, 실시간)

1. 스크랩 저장 → AI가 Summary 생성(Product Decision #001)
2. Embedding 생성
3. **임시 배치**: 기존 Greedy(`assign_scrap`, Step 5 `world.py`)를 그대로
   재사용 — identity_vector 비교로 Island 병합/생성. **Topic도 이 단계에서
   임시로 생성될 수 있다** — 완전히 새로운 스크랩이 들어오면 즉시 새 Topic이
   생기고, Night Batch가 나중에 이걸 승인/합병/분리한다.
4. growth_vector EMA 갱신, Growth Point 누적
5. 사용자에게 즉시 반영(Product Principle "모든 성장은 체감 가능해야 한다")

## Night Batch (밤, 주기적) — 재클러스터링이 아니라 보수 작업

트리거 조건(매일 고정 시각 vs 스크랩 N개 누적)은 아직 미정 — Open Question
참고.

Night Batch는 다음 5단계로 진행하며, **HDBSCAN(Experiment #12/#15에서
검증된 방식)의 결과는 2~4단계에서 "후보"를 찾는 데만 쓰고, 실제 반영 여부는
매번 Invariant #5(Minimum Change Principle)로 걸러낸다.**

1. **후보 탐색**: 최근 데이터(또는 전체)에 offline 클러스터링을 돌려 현재
   Island/Topic 구조와 얼마나 다른지 비교한다.
2. **Merge 후보**: 별개로 존재하던 Island/Topic이 밀도 상 하나로 합쳐지는
   게 더 낫다고 판단되면 후보로 올린다(Product Decision #002의 Programming
   사례가 대표적 — Growth Rule의 City 형성 조건인 "밀도=다양성×연결성"과
   직접 연결).
3. **Split 후보**: 하나의 Island/Topic 내부 밀도가 충분히 높고 이질적인
   하위 군집이 생기면(예: Backend Topic이 Spring/Kafka/Redis로 이미 나뉘어
   있던 것처럼) 분리 후보로 올린다. **이 경우 Redis Topic 같은 새 Topic이
   Night Batch에서 생성될 수 있다.**
4. **Boundary Topic 이동**: 완전한 merge/split까지는 아니지만 경계에 있는
   Topic 하나를 다른 Island로 옮기는 것만으로 전체 안정성을 크게 해치지
   않으면서 품질을 개선할 수 있는 경우 — Minimum Change Principle이 가장
   자주 적용되는 지점이다.
5. **Label 갱신**: 위 단계에서 실제로 바뀐(merge/split/rename된) Topic만
   Label을 다시 생성한다. 바뀌지 않은 Topic은 Label을 그대로 유지한다.

## Invariants (불변 조건)

**#1. Growth Point는 절대 잃지 않는다.**
Merge 시 두 Island/Topic의 Growth Point는 합산한다 — 사용자가 쌓아온
성장 서사가 Batch 한 번으로 사라지면 "세계는 안정적이어야 한다" 원칙을
정면으로 어긴다. Split 시 Growth Point를 어떻게 분배할지는 아직 미정
(Open Question).

**#2. Island ID — Merge 시 오래된/큰 쪽이 유지된다.**
Git의 merge commit처럼 역사가 이어지는 쪽으로 설계한다. 흡수되는 Island는
ID가 폐기되되 "OO 섬에 합쳐짐" 이력을 남긴다. Split 시에는 가장 큰 파편이
원래 ID를 유지하고 나머지는 새 ID를 받는다.

**#3. Topic ID — Online과 Night 둘 다에서 생성·소멸될 수 있다.**
Online에서는 임시로 즉시 생성된다(Step 5 `Island.add()` 로직). Night
Batch는 여기서 그치지 않고 **Merge/Split/Rename을 모두 수행할 수 있으며,
그 과정에서 새 Topic이 생기거나 기존 Topic이 사라질 수 있다** — Topic
생성을 Online에만 제한하면 Night Batch의 "보수" 역할이 지나치게 약해진다.

**#4. Label — Topic이 "안정된 뒤"에만 확정, 이후엔 실제로 바뀔 때만
재생성된다.**
Topic이 Online에서 처음(임시로) 생겨도 Label은 바로 확정하지 않는다.
Night Batch가 그 Topic을 승인하는 시점(또는 merge/split을 거쳐 최종
형태가 정해지는 시점)에 Label을 생성하고, 이후로는 그 Topic이 다시
merge/split/rename될 때만 재생성한다. 안정적인 Topic은 Label을 계속
유지해 "건물 이름이 자꾸 바뀌는" 불안정한 경험을 피한다.

**#5. Minimum Change Principle — Batch는 사용자의 세계를 가능한 적게
바꾼다.**
offline 클러스터링이 제안하는 "가장 이상적인 구조"보다, 기존 구조를 최대한
유지하면서 아주 조금 덜 최적이어도 안정적인 세계를 우선한다. 예: HDBSCAN이
Island 7개를 6개로 재편하라고 제안해도, 경계 Topic 하나만 옮겨서 거의
같은 품질을 얻을 수 있다면 후자를 선택한다. 이 원칙이 2~4단계 전체를
관통하며, Hybrid Architecture를 "온라인+배치"라는 기술적 조합이 아니라
World Engine만의 철학을 가진 설계로 만든다.

## 좌표 불변 원칙과의 관계

`map_layout.md`의 "기존 섬은 절대 안 움직인다"는 원칙이 Night Batch의
merge/split과 충돌할 수 있는 지점이다.

- **Merge**: 살아남는 Island의 좌표는 그대로 두고, 흡수되는 Island의
  스크랩만 그 안의 Topic으로 재배치한다 — "이동"이 아니라 "합류"라서
  원칙과 충돌하지 않는다.
- **Split**: 원래 Island는 자리를 지키고(축소만 됨), 떨어져 나온 조각만
  Nearest Neighbor 로컬 배치로 새 위치를 받는다(map_layout.md 원칙 그대로
  재사용, 결정론적 시드도 동일하게 적용).
- **진짜 위험한 경우**: offline 클러스터링이 온라인 결과와 완전히 다른
  전역 구조를 제안해서 "하나가 줄고 하나가 새로 생겼다"로 설명되지 않는
  재편이 나올 때다. 이때는 **Minimum Change Principle이 방어막 역할을
  한다** — 아무리 클러스터링 품질이 좋아져도 안정성을 크게 해치는 제안은
  후보에서 제외한다. 다만 이 방어가 실제로 충분한지는 아직 이론적으로만
  설계됐고 검증된 적이 없다 — V1 이전에 프로토타입으로 확인이 필요하다.

## Open Questions (미해결)

1. Night Batch 트리거 조건 — 고정 시각 vs 스크랩 N개 누적, 혹은 둘의 조합.
2. Split 시 Growth Point 분배 정책 — 원 스크랩 소속 비율대로 나눌지, 새
   Island는 0부터 시작하되 "역사"만 유지할지.
3. Minimum Change Principle의 "적게"를 어떻게 정량화할지 — 임계값(예:
   기존 구조와 몇 % 이상 달라지면 거부)이 필요한지, 아니면 케이스별
   휴리스틱으로 충분한지.
4. offline 클러스터링이 완전히 다른 전역 구조를 제안하는 경우의 실제
   처리 — 좌표 불변 원칙과의 관계에서 언급한 "진짜 위험한 경우"를 V1 이전에
   프로토타입으로 검증해야 한다.

**참고**: `experiments/v0_validation.md` Experiment #20(Virtual User Growth
Simulation)에서 Night Batch가 아직 없는 Online-only 상태로는 한 사용자의
자연스러운 30일 성장 과정에서도 같은 실제 주제(Redis/Kafka/Docker 등)가
여러 Island에 중복되는 **Fragmentation of User Interest** 현상이 나타나는
것을 확인했다. 이건 Night Batch가 다루려는 문제가 실제로 존재한다는
근거이지, Night Batch가 이 문제를 해결한다는 증거는 아니다.

**업데이트 (Experiment #21)**: `night_batch()`(v0, Merge-only 구현 — 위
5단계 중 1/2/5만 구현, Split·Boundary Topic 이동은 아직 없음)를 같은
Virtual User Dataset에 적용한 결과 Island 수 5→1, Topic Duplication
Rate(`evaluation_metrics.md` 참고) 88.9%→0.0%로 개선됐다. **단, 이 결과는
페르소나 1명·데이터셋 1개로만 검증됐다 — "Night Batch가 Finding #001을
해결했다"는 아직 일반화된 결론이 아니다.** 남은 검증 범위는 아래 체크리스트
참고.

### Hybrid Validation Checklist (백로그)

Night Batch v0가 다른 시나리오에서도 fragmentation을 해소하는지 확인하는
로드맵. 체크된 것 외에는 전부 미실행.

- [x] Backend User (Experiment #21) — Island 5→1, Topic 중복률 88.9%→0%
- [x] AI Researcher User (Experiment #22) — Merge-only로는 변화 없음(77.8%
      유지). Fragmentation이 아니라 Over-merge 문제였다는 게 밝혀짐 —
      **Finding #003(Status: Resolved, Need Split)**로 승격. 이 발견 덕분에
      아래 항목들의 우선순위가 바뀜(다음 섹션 참고).
- [ ] Mixed Engineering User — 여러 엔지니어링 분야가 섞인 페르소나
- [ ] Sports User — 순수 스포츠 팬, fragmentation이 안 생기는 게 정상인지 확인
- [ ] Investor User — Finance 계열
- [ ] Multi-user Shared World — 여러 사용자가 동시에 존재할 때 Night Batch가
      사용자 간 경계를 깨지 않는지
- [ ] **Sports + Finance Boundary Case** — Watch Metric #001과 직결. Night
      Batch가 "진짜 갈라져야 하는" 경우까지 과도하게 합쳐버리지는 않는지가
      핵심 리스크(Split 미구현 상태이므로 특히 중요)

### 우선순위 재조정 (Finding #003 이후)
원래는 이 체크리스트를 계속 채우는 게 다음 순서였지만, Finding #003이 Merge의
적용 범위(fragmentation은 고치고, over-merge는 못 고침)를 명확히 규명하면서
**Split Prototype(Step 5.5 v1.1)이 나머지 체크리스트보다 먼저 와야 한다**는
쪽으로 바뀌었다. Mixed Engineering User나 Sports+Finance Boundary Case 같은
나머지 항목도 Split이 없으면 AI Researcher와 똑같이 "Merge만으로는 설명 못
하는 결과"에 부딪힐 가능성이 크기 때문이다 — Split을 먼저 구현해야 나머지
검증이 의미 있는 비교가 된다.

**Split Prototype 설계 질문(아직 미설계)**:
- 언제 Split을 트리거할지 — 예: Island의 purity가 낮고(예: <0.5) 내부에
  여러 dominant HDBSCAN 클러스터가 공존할 때.
- 어떤 기준으로 나눌지 — offline 클러스터 경계를 그대로 따를지, 기존 Topic
  단위로 재배치할지.
- 좌표 불변 원칙과의 관계(위 "좌표 불변 원칙과의 관계" 절 참고) — 원래
  Island는 자리를 지키고 떨어져 나온 조각만 새 좌표를 받는다는 설계를 그대로
  적용할 수 있는지 실제 구현으로 검증해야 한다.

---

## Night Batch v2 — Topic Graph Reconstruction (Finding #004 이후, v0 대체 설계)

### 왜 v0(Island 단위 Merge/Split)를 계속 고치지 않는가

Split Prototype을 실제로 구현하고 검증하는 과정(Experiment #23, Finding #004)에서
Island를 기본 조작 단위로 삼는 접근 자체의 한계가 드러났다:

1. Merge(Island 단위)는 Backend User의 fragmentation은 해소했지만 AI
   Researcher의 over-merge는 손대지 못했다(Finding #003).
2. Split(Island 단위)을 추가하자 AI Researcher의 Topic 중복률이 오히려
   77.8%→88.9%로 **악화**됐다 — 분리 대상 Island 하나만 보고 판단해서, 이미
   존재하는 다른 Island와 겹치는 조각을 새로 만들어냈다(Finding #004).
3. Split 직후 Merge를 다시 돌려 이를 고치려 했지만 **효과가 없었다** —
   기존의 작은 Island들(#1/#2/#3) 자체가 이미 여러 실제 주제가 섞인
   덩어리라 Island 단위 "다수결 라벨" 비교로는 애초에 서로를 못 찾는다.

이 세 시도가 공통으로 가리키는 결론: **Merge/Split이 부족한 게 아니라,
Island를 기본 단위로 삼은 것 자체가 문제다.** Boundary Topic Move(Topic
단위로 옮기는 4번째 연산)를 추가로 구현해도 "Move → 관계 변화 → 다시 Merge
→ 다시 Split → 다시 Move"가 끝없이 반복되는 local optimization 패턴에
빠질 뿐이다.

### 핵심 원칙

> **Night Batch의 최소 이동 단위는 Island가 아니라 Topic이다.**

지금까지의 계층 구조(`Scrap → Topic → Island → City`)를 보면 Growth도,
Label도, Boundary Ambiguity(Finding #002/#003)도 전부 Topic 단위에서
일어난다. Island는 처음부터 "Topic들의 묶음(결과)"였을 뿐인데, Night Batch
v0만 Island를 직접 조작하는 연산(Merge/Split)으로 설계되어 있었다는 게
문제의 뿌리였다.

### 파이프라인

Merge/Split/Boundary Move를 각각 다른 연산으로 두지 않고, 전부 하나의
재계산으로 통일한다:

1. **Topic 수집**: 현재 모든 Island의 모든 Topic을 모은다(Island 소속은
   일단 무시).
2. **Topic Graph 생성**: 모든 Topic 쌍에 대해 `center_vector` cosine
   similarity를 계산하고, threshold 이상이면 두 Topic 사이에 edge를 긋는다.
3. **Connected Component**: Union-Find로 서로 연결된 Topic 묶음을 찾는다.
4. **Island 재구성**: 각 Connected Component가 새로운 Island가 된다.

Merge(여러 Island가 하나로), Split(한 Island가 여러 개로), Boundary Move
(Topic 하나가 다른 Island로) 전부 **"Topic Graph가 다시 연결되는 현상"**
하나로 통일된다 — 세 가지 별도 연산이 사라진다.

### Invariant 유지 방법 (v0의 원칙을 그대로 계승)

- **변화 없는 Island는 그대로 둔다**: 어떤 Connected Component의 Topic
  집합이 기존 Island 하나의 Topic 집합과 정확히 같으면, 그 Island의 id와
  identity_vector를 재계산하지 않고 그대로 유지한다 — 좌표 불변 원칙을
  지킨다.
- **바뀐 Component는 Minimum Change Principle로 ID를 정한다**: Component에
  기여한 원래 Island들 중 스크랩 수가 가장 많은 Island의 id를 유지한다
  (Merge v0의 "오래된/큰 Island 생존" 규칙과 동일).
- **identity_vector**: 바뀐 Component만 스크랩 평균 벡터로 다시 계산한다
  (Split v0에서 쓴 방식과 동일 - 아직 실제 화면 좌표 시스템이 없어서
  embedding 공간을 좌표 대신 쓴다).
- **Growth Point**: 여전히 미구현(Step 7 보류) — 이 설계도 그 부분은
  건드리지 않는다.

### 업데이트 (Experiment #24) — pairwise threshold + Union-Find는 기각

프로토타입(`topic_graph_reconstruct`, 순수 pairwise cosine similarity +
threshold + Union-Find)을 실제로 구현해서 Backend User/AI Researcher에
edge_threshold 0.24~0.60을 스윕해봤다. **두 페르소나가 거의 동일하게
움직였다** — "전부 하나"(threshold≤0.35)에서 "전부 쪼개지며 중복도 같이
증가"(threshold≥0.40)로 바로 건너뛰고, 안정적인 중간 구간이 없었다.
원인은 체이닝(chaining) — RLHF 같은 "허브" Topic이 여러 다른 Topic과
동시에 높은 유사도를 가져서 서로 안 닮은 것들까지 하나로 묶는다. 이건
Scrap 레벨(Experiment #6~7)에서 이미 겪은 문제가 Topic 레벨에서 그대로
재현된 것이다 — **Finding #004(Pairwise Threshold Graph exhibits chaining
instability)**로 승격, `docs/algorithm_limitations.md` 참고.

**결론: pairwise threshold + Union-Find는 기각한다.** 대신 Topic의
`center_vector`들에 **HDBSCAN**(Experiment #12/#22에서 이미 검증된 밀도
기반 방법)을 직접 돌리는 방식으로 edge/component 판단을 교체를 시도했다
(`topic_graph_reconstruct_hdbscan`, Experiment #25).

### 업데이트 (Experiment #25) — Topic-level HDBSCAN도 기각, 더 근본적인 문제 발견

두 변형(Topic centroid 직접 클러스터링 / scrap 레벨 HDBSCAN 라벨로 Topic
재그룹화)을 시도했지만 **둘 다 Backend User마저 악화시켰다** — 최선의
경우도 7개 Island(4~9 중복)로, 원래 Merge-only(v0)의 1개/0%보다 나쁘다.
체이닝 문제가 아니라 **표본 크기 문제**였다: 온라인 단계가 Topic을
21~27개까지 잘게 만들어서(스크랩 71개 기준 Topic당 평균 3개 미만) Topic
단위 통계가 embedding noise에 취약하다. Island 단위는 여러 Topic을
뭉뚱그려 이 노이즈를 평균화하지만, Topic 단위로 내리면 그 평균화 효과가
사라진다.

이걸 **Finding #005(Aggregation Level Trade-off)**로 승격했다
(`docs/algorithm_limitations.md` 참고) — Island 단위(안정적이지만 저해상도)와
Topic 단위(고해상도지만 노이즈에 취약)가 정확히 반대 방향으로 실패한다.
Merge/Split/Graph/HDBSCAN 4가지 시도가 겉보기엔 다른 알고리즘이었지만
전부 "의사결정을 어느 계층에서 내리는가"라는 하나의 축 위에 있었다는 게
이번에 드러났다.

**Open Question(다음 세션의 출발점)**: Night Batch의 본질은 "더 좋은
클러스터링을 찾는 것"인가, 아니면 "문제가 있는 Island만 최소한으로
수정하는 것"인가? 지금까지의 모든 버전은 암묵적으로 "세계 전체를 다시
평가한다"고 가정했다 — Backend User는 Online 결과가 이미 좋았는데도
Night Batch가 매번 다시 건드리면서 오히려 나빠졌다. "전체 재구성"이
아니라 "purity가 낮아 의심스러운 Island만 선택적으로 재평가"하는 방향이
다음 후보다. 다음 세션은 구현이 아니라 이 질문에 답하는 **설계 세션**으로
시작한다.

### 아직 결정 안 된 것

- 위 Open Question에 대한 답(선택적 재평가 vs 전체 재구성)이 가장 먼저
  필요하다 — 이후의 파라미터 튜닝(min_cluster_size 등)은 이 질문이
  풀리기 전까지는 의미가 크지 않다.
- v0(Merge/Split 함수), v1(pairwise threshold Topic Graph), v2(Topic-level
  HDBSCAN 변형 A/B)는 전부 삭제하지 않는다 - Finding #003/#004/#005의
  근거가 된 코드이므로 기록으로 남긴다. 다음 설계가 확정되면 실제
  파이프라인에서 어떤 버전을 쓸지(또는 완전히 새로운 v3를 만들지) 결정한다.

### 업데이트 (Finding #006) — Night Batch 설계는 여기서 일시 정지

Open Question에 답하려고 `selective_night_batch`(v3, purity 높은 Island는
안 건드리고 낮은 것만 Split 후보로)를 구현·검증했지만 AI Researcher를
여전히 못 풀었다. 원인을 추적한 결과 **Night Batch 설계의 문제가
아니었다** — Island #0의 Topic 하나가 이미 8개 실제 주제, 30개 스크랩을
섞은 채로 Online 단계에서 만들어져 있었다. Night Batch의 어떤 버전도
"Topic은 신뢰할 수 있는 단위"라는 가정 위에 서 있었기 때문에 이 문제를
원리적으로 고칠 수 없다 — `docs/algorithm_limitations.md` **Finding
#006** 참고.

**이 문서(Night Batch v2/v3)의 다음 버전 설계는 여기서 멈춘다.** 다음
세션은 Night Batch가 아니라 **Topic Formation Research**(Step
5.25, 신설)로 연구 질문을 전환한다 — Online 단계에서 Topic이 애초에 왜,
어떻게 오염되는지부터 밝혀야 Night Batch를 다시 설계하는 의미가 있다.
로드맵: Step 5(Online Topic Formation) → **Step 5.25(Topic
Validation/Repair)** → Step 5.5(Night Batch, 이 문서) → Step 6(Label).

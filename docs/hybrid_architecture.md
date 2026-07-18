# Hybrid Architecture (Step 5.5)

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
- [ ] AI Researcher User — Transformer/RLHF/Diffusion/Vector DB/Agent 등
- [ ] Mixed Engineering User — 여러 엔지니어링 분야가 섞인 페르소나
- [ ] Sports User — 순수 스포츠 팬, fragmentation이 안 생기는 게 정상인지 확인
- [ ] Investor User — Finance 계열
- [ ] Multi-user Shared World — 여러 사용자가 동시에 존재할 때 Night Batch가
      사용자 간 경계를 깨지 않는지
- [ ] **Sports + Finance Boundary Case** — Watch Metric #001과 직결. Night
      Batch가 "진짜 갈라져야 하는" 경우까지 과도하게 합쳐버리지는 않는지가
      핵심 리스크(Split 미구현 상태이므로 특히 중요)

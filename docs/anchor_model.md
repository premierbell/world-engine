# Anchor Model

Finding #006(Greedy + EMA + Threshold는 계층과 무관하게 같은 방식으로
실패한다) 이후 Night Batch v0~v3(Merge/Split/Topic Graph/HDBSCAN/
Selective, `hybrid_architecture.md`)를 대체하는 통합 설계다. v0~v3는
전부 "Greedy가 만든 구조는 대체로 맞고, 그걸 고친다"는 전제를 갖고
있었다 — 이 전제 자체가 틀렸다는 게 오늘 확인됐다(AI Researcher의 Topic
하나가 30개 스크랩, 8개 실제 주제를 이미 섞은 채로 만들어져 있었다).

## 핵심 원칙

> **Greedy Online은 UX(Preview)만 담당한다. 확정(Truth)은 오직 Night
> Batch에서만 일어난다.**

Online 단계에서 만들어지는 Topic/Island는 **Provisional**이다 — 사용자에게
즉시 보여주기 위한 임시 상태일 뿐, 다음 Night Batch가 그대로 승인한다는
보장이 없다. Night Batch는 Greedy의 결과를 "고치는" 게 아니라, 그 주기
동안 쌓인 새 스크랩을 **Greedy가 어디 배치했는지는 무시하고** 원점에서
다시 클러스터링(scrap-level HDBSCAN, Experiment #12/#22에서 검증된
방법)한다.

## Confirmed = Anchor

Night Batch가 한 번이라도 승인한 Topic/Island를 **Anchor**라고 부른다.
Anchor는 이후의 routine Night Batch에서:

- **움직이지 않는다** — identity_vector, id, 좌표가 전부 불변.
- **쪼개지지 않는다** — Split 대상이 아니다.
- **하지만 Context로는 계속 쓰인다** — 새 스크랩을 어디에 붙일지 판단할
  때 Anchor의 identity_vector/center_vector/Label을 참고 기준으로
  사용한다.

새로 들어온(아직 Confirmed 안 된) 데이터만 매 Night Batch마다 새로
클러스터링되고, 그 결과가 기존 Anchor와 충분히 가까우면 그 Anchor에
편입되며, 아니면 새로운 Anchor가 된다.

## Lifecycle (Topic과 Island가 동일한 구조를 공유한다)

```
Scrap 저장
  ↓
Provisional Topic (Online, 현재 Greedy+EMA+threshold 그대로) — 즉시 체감
  ↓  (Night Batch)
Confirmed Topic = Anchor (identity_vector 고정, Label 생성)
  ↓
Provisional Island (Online, 같은 방식)
  ↓  (Night Batch)
Confirmed Island = Anchor
```

Topic과 Island는 같은 Lifecycle(Online=Provisional, Offline=Confirmed)을
공유한다 — Finding #001(Island)과 Finding #006(Topic)이 사실 같은
계층적 문제였다는 것과 대칭을 이룬다.

## Night Batch 알고리즘 (Anchor 기준)

**입력**: `confirmed_topics`(Anchor 목록) + `new_scraps`(마지막 Night
Batch 이후 쌓인, 아직 Confirmed 안 된 스크랩)

```
candidate_clusters = HDBSCAN(new_scraps)   # Greedy 배치는 참고하지 않는다

for cluster in candidate_clusters:
    nearest_anchor = 가장 가까운 confirmed anchor 찾기
    if similarity(cluster, nearest_anchor) >= threshold:
        attach(cluster, nearest_anchor)     # Anchor 자체는 안 바뀜, 소속만 늘어남
    else:
        create_new_anchor(cluster)          # 새 Confirmed Topic/Island
```

**출력**: 기존 Anchor(변경 없음) + 새로 생긴 Anchor. Island 레벨에서는
이 과정이 Topic Anchor들을 입력으로 반복된다(Topic이 먼저 Confirmed된
뒤에야 Island Night Batch가 그 위에서 실행된다 — Step 5.25 → Step 5.5
순서와 일치).

## Immutability의 예외 — Migration Event

Anchor는 **routine Night Batch에서는** immutable이다. 하지만 이걸
절대화하면 장기적으로 개념 드리프트(concept drift)에 대응할 수 없다 —
예를 들어 2026년의 "LLM" Topic이 2년 뒤에는 Reasoning/Agents/MCP/World
Models까지 포괄하는 훨씬 큰 영역으로 자연스럽게 성장했어야 할 수도
있다.

그래서 두 계층으로 나눈다:

- **일상적인 Night Batch**: Anchor는 절대 불변. 새 데이터만 원점에서
  재계산해서 기존 Anchor에 붙이거나 새로 만든다.
- **Migration Event(신설, 예외적)**: 알고리즘 버전 업그레이드, 대규모
  재색인, 사용자의 명시적 재구성 요청 같은 경우에만 전체 재구성을
  허용한다. Migration Event는 routine Night Batch와 명확히 구분되는
  별도 트리거를 가져야 한다(자동으로 조용히 발동되면 안 됨 — "세계는
  안정적이어야 한다" 원칙을 해치지 않으려면 사용자가 인지할 수 있는
  이벤트여야 한다).

## Product Principle과의 대응

| Principle | Anchor Model에서의 구현 |
|---|---|
| 세계는 안정적이어야 한다 | Anchor는 routine Night Batch에서 절대 안 움직인다 |
| 성장은 즉시 체감 가능해야 한다 | Provisional 단계가 즉시 반영되고, 새 Anchor 생성도 눈에 보이는 성장이다 |
| Minimum Change Principle | candidate cluster는 항상 기존 Anchor 편입을 우선 시도한다 |
| 좌표는 영속 상태 (`map_layout.md`) | Anchor의 identity_vector(=좌표 대용)는 불변 |

## Research Question #0 — 최종 답 (Finding #006 이후)

> Online에서 확정되는 계층이 존재해야 하는가?

**없다.** Greedy Online(Topic이든 Island든)은 전부 Provisional(Preview
UX)이고, 확정은 오직 Night Batch(Anchor 형성)에서만 일어난다.

## Research Question #1 (신설)

> Offline 단계에서 Greedy 결과를 얼마나 재사용해야 하는가?

**새로 들어온(미확정) 데이터에 대해서는 재사용하지 않는다** — Greedy가
어디 배치했었는지 무시하고 scrap 레벨에서 원점 재계산한다. **이미
Confirmed된 Anchor는 Context로만 참고하고 routine 상황에서는 절대
수정하지 않는다.** 오늘 시도했던 Night Batch v0~v3(Merge/Split/Topic
Graph/HDBSCAN/Selective)가 전부 실패했던 공통 원인이 "Greedy 결과를
입력으로 재사용하려 했다"는 것이었다는 게 이 질문에 대한 실험적 근거다.

## Open Questions (아직 미해결)

1. **Attach 판단 기준** — candidate cluster와 Anchor 사이의 유사도를
   어떻게 계산할지(Anchor의 identity_vector vs candidate cluster의
   centroid? 아니면 다른 방식?), threshold는 얼마로 할지. 아직 검증
   안 됨.
2. **여러 candidate가 같은 Anchor를 두고 경쟁**할 때 처리 방법.
3. **Migration Event의 정확한 트리거 조건** — 완전히 수동(사용자 요청)인지,
   일정 기준(예: Provisional 데이터가 너무 오래 Anchor에 안 붙는 경우)이
   되면 자동으로 제안하는지.
4. **Provisional 상태를 사용자에게 보여줄지** — "이 건물은 아직 형성
   중입니다"를 노출하는 게 "세계가 살아있다"는 느낌을 주는 좋은 UX일지,
   아니면 불안정해 보일지. 아직 결정 안 됨.
5. **Migration Event 동안 Growth Point/역사를 어떻게 이관할지** — Growth
   Point 자체가 아직 미구현(Step 7 보류)이라 이 질문은 Step 7 이후로
   미룬다.

## 기존 코드와의 관계

`world.py`의 Night Batch v0~v3(`night_batch`, `find_split_candidates`/
`apply_split`, `run_night_batch`, `topic_graph_reconstruct*`,
`selective_night_batch`)는 삭제하지 않는다 — Finding #003~#005의 근거로
남긴다. Anchor Model을 실제로 구현할 때는 이 함수들의 부품(특히
scrap-level HDBSCAN 호출, Invariant 유지 로직)을 재사용하되, "Greedy
결과를 입력으로 반복 수정"하는 구조는 버리고 "새 데이터만 원점 재계산 +
기존 Anchor는 Context"라는 새 구조로 다시 짠다 — 아직 구현 전이다.

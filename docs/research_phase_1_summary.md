# World Engine V0 — Research Phase 1 Summary (RQ0~RQ9)

> **Phase 1: Complete.** Phase 2(Adaptive Resolution)는 아직 시작 전이다.

## 연구 목표

V0의 목표는 "스크랩이 알고리즘으로 실제 관심사 지도(Island/Topic)로
잘 모이는가"를 검증하는 것이었다. 리스크가 가장 큰 가정(클러스터링이
말이 되는가)을 최소 비용으로 먼저 검증한다는 원칙 아래, Data
Model이나 UI보다 알고리즘 자체의 구조적 타당성을 먼저 파고들었다.
Phase 1은 "Topic Identity(어떤 스크랩들이 같은 관심사인가)를 어떤
신호로, 어떤 메커니즘으로 판별할 것인가"라는 질문 하나를 10개의
Research Question(RQ0~RQ9)과 14개의 Finding을 거쳐 추적한 기록이다.

## RQ0~RQ9 요약

| RQ | 질문 | 답 |
|---|---|---|
| RQ0 | Online에서 확정되는 계층이 존재해야 하는가? | **없다** — Greedy Online은 전부 Provisional, 확정은 Night Batch(Anchor)에서만 |
| RQ1 | Offline이 Greedy 결과를 얼마나 재사용해야 하는가? | 새 데이터는 원점 재계산, Confirmed Anchor는 Context로만 참고 |
| RQ2 | Anchor는 무엇으로 표현되어야 하는가? | identity_vector(단일 centroid)는 판별력을 잃음(Finding #007) → RQ3의 하위 문제로 흡수 |
| RQ3 | Attach는 어떤 목적함수를 최적화해야 하는가? | Greedy는 전역 최적이 아니지만(Exp #33), Objective 개선은 실제 품질 개선을 보장 안 함(Exp #34) |
| RQ4 | Duplication은 어떤 신호로 근사할 수 있는가? | Pairwise similarity로도, 구조적 신호로도 불가 — Closed, 실패 |
| RQ5 | Similarity만으로 Topic Identity를 만들 수 있는가? | **아니오** — 6가지 독립 modality 전부 실패 |
| RQ6 | Topic Identity는 개별 문서 속성인가, 관계적 속성인가? | 관계(태그 그래프)는 국소적으로만 유효, 전역 연결성은 체이닝에 취약 |
| RQ7 | Topic Identity는 복원 대상인가, 형성되는 대상인가? | 반복 관측은 Bias를 못 줄인다("Stable but Wrong") |
| RQ8 | **신호 존재**: Pairwise LLM semantic judgment가 판별력 있는 신호를 만들 수 있는가? | **그렇다** — Mechanism 수준에서 강한 신호(AUC 0.82) |
| RQ9 | **신호 충분성**: 그 신호가 실제 Attach 판단에 쓸 만큼 Topic Identity를 충분히 반영하는가? | **조건부로 그렇다** — 판단 해상도가 도메인의 semantic density와 맞을 때만 |

RQ8과 RQ9는 서로 다른 질문이었다 - RQ8은 "신호가 존재하는가"(있다),
RQ9는 "그 신호가 실제로 쓸 만한가"(도메인에 따라 다르다)였다.

## Finding #001~#014 요약

| Finding | 한 줄 요약 |
|---|---|
| #001 | Greedy+단일 Threshold는 순서 의존적 — HDBSCAN(offline)으로 해결 |
| #002 | Backend/AI 경계가 원래 애매함 — Product Decision #002로 흡수 |
| #003 | Merge-only는 과병합을 못 고침 — Split 필요 |
| #004 | Pairwise Threshold Graph는 Chaining에 취약 (4개 층위에서 반복 재현) |
| #005 | Aggregation Level Trade-off (Island=저해상도/안정 vs Topic=고해상도/노이즈) |
| #006 | Greedy+EMA+Threshold는 계층 무관하게 같은 방식으로 실패 |
| #007 | Anchor 단일 벡터 표현은 판별력을 잃음 |
| #008 | Embedding Similarity는 Relatedness는 포착하지만 Identity는 아니다 |
| #009 | 독립적 문서 이해로는 공유 Topic Identity를 못 만듦 |
| #010 | Local Connectivity 자체가 Topic Identity가 아님 |
| #011 | Duplication 원인은 CREATE가 아니라 ATTACH(Assignment) |
| #012 | Pairwise LLM Judgment는 Mechanism 수준의 강한 신호(AUC 0.82) |
| #013 | 판단 해상도가 평가 해상도와 일치해야 함 — 원인은 Prompt Objective |
| #014 | 적정 해상도는 도메인마다 다름(Domain-dependent) |

## 실패한 접근과 왜 실패했는가

Phase 1 전체를 관통하는 서사는 "무엇을 판단 신호로 쓸 것인가"를 점점
더 근본적인 층위로 좁혀간 과정이다. 대부분의 프로젝트 기록은
"시도 → 성공"만 남기지만, 여기서는 "가설 → 반증 → 새 가설"의 흐름이
그대로 남아 있다 - 이게 연구 기록으로서의 가치다.

1. **Similarity 축(RQ2~RQ5, Finding #007~#008)** — embedding cosine
   similarity, margin, representation(top-k averaging), 구조적
   co-candidacy 신호까지 전부 시도했지만, 전부 "semantic relatedness"만
   포착하고 "topic identity"는 못 만들었다. Transformer/RLHF/Fine-tuning
   같은 서로 다른 실제 Topic이 전부 "LLM 연구"라는 하나의 넓은 의미
   공간에서 가깝다는 게 근본 원인이었다.
2. **Tag/Graph 축(RQ6, Finding #009~#010)** — AI가 추출한 키워드
   태그(freeform, hierarchical)로 전환했지만 문서를 독립적으로
   태깅하는 한 여러 문서가 공유할 일관된 어휘가 생기지 않았다. 태그를
   그래프로 연결해도(co-occurrence) 허브 태그가 무관한 그룹을 전부
   이어버리는 체이닝이 재현됐다.
3. **반복 관측 축(RQ7, Finding #011)** — "여러 번 관측하면 Confidence가
   쌓이지 않을까"를 시도했지만, ATTACH 판단 자체가 노이즈에 매우
   안정적(99~100% consistency)이면서 정확도는 낮았다(5.6~23.1%) —
   Variance가 아니라 Bias 문제라 반복 관측이 해결할 수 있는 종류가
   아니었다("Stable but Wrong").
4. **Pairwise LLM Judgment 축(RQ8~RQ9, Finding #012~#014)** — 문서
   쌍을 동시에 비교하는 완전히 다른 정보원으로 전환하자 처음으로 강한
   신호(AUC 0.82~0.94)를 얻었다. 하지만 이 신호가 반영하는 해상도
   (Mechanism 또는 Topic)가 평가가 요구하는 해상도와 일치해야 했고,
   그 "일치"조차 도메인마다 다른 정답을 요구했다 — Backend처럼 Topic
   간 거리가 먼 도메인은 넓은 해상도가 통하지만, AI Researcher처럼
   Topic들이 하나의 의미 공간에 밀집한 도메인은 넓은 해상도가 오히려
   해가 됐다.

## 최종 결론

> Phase 1 suggests that topic understanding is not the primary
> limitation. Instead, selecting an appropriate semantic resolution
> appears to be domain-dependent.

이 결론은 2개의 Virtual User Dataset(Backend User, AI Researcher)에서
관측된 것이다 - 더 많은 도메인에서 재현되는지는 아직 검증되지 않았다.
Finding #008(Similarity는 Topic Identity가 아니다)에서 시작해서 Finding
#014(적정 해상도는 도메인마다 다르다)로 끝나는 이 흐름을 압축하면:
문제는 "이해 능력의 부재"가 아니라 "고정된 해상도로 모든 도메인을
판단하려 한 것"에 더 가까웠다.

## 남은 Open Question: Adaptive Resolution (Research Phase 2, 미시작)

Phase 1이 답한 건 "판단 해상도가 도메인마다 달라야 한다"는 것까지다.
"그 해상도를 어떻게 도메인마다 자동으로 맞출 것인가"는 완전히 새로운
연구 프로그램이다 — RQ0~RQ9와 이어지는 하위 질문이 아니라, 그 전체
결론 위에서 새로 시작하는 **RQ10: Adaptive Resolution**으로 취급한다.

**Phase 2는 더 이상 "Topic Identity를 복원할 수 있는가"를 묻지 않는다.
"적정한 semantic resolution을 어떻게 자동으로 선택할 것인가"를 묻는다.**

Phase 2의 첫 연구 질문(RQ10-0: Ontology of Semantic Resolution)은
`research_phase_2_rq10-0.md`에서 정의한다.

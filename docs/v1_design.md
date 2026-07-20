# V1 Design: AI Recommends, User Confirms

> Phase 1/2 연구 결과(`docs/research_phase_1_summary.md`,
> `docs/research_phase_2_summary.md`)를 제품 설계로 옮기는 문서.
> V0(Validation)의 검증이 끝난 뒤 처음 쓰는 설계 문서 - `anchor_model.md`
> 가 V0 알고리즘의 상세 설계였다면, 이 문서는 V0에서 배운 것을 바탕으로
> V1(Genesis)이 실제로 무엇을 만들지 정의한다.

## Design Principle

> AI가 사용자의 조직 방식을 혼자서 복원할 수는 없다. 하지만 사용자의
> 행동 맥락을 조금 받으면 AI 추천의 품질은 개선된다. (Finding P2-003)

V0가 처음 꿈꿨던 것은 "스크랩 → 완전 자동 분류"였다. Phase 2 전체
(Measurement Family, Objective Discovery, Information Discovery)의
결론은 이게 현재 기술로는 안 된다는 것이다 - Mechanism/Topic/Neutral/
Relation/Retrieval 어떤 objective도, 얕은 저장 이유를 더해도 완전
자동화의 벽을 못 넘었다(Finding P2-002). 진짜 behavioral context를
줘야 방향성 있는 개선이 있었지만(Finding P2-003) 그것만으로도
불충분했다.

그래서 V1은 **"스크랩(+선택적 맥락) → AI 추천 → 사용자 확인"** 구조로
간다. `ai_rules.md` Rule 1("AI는 이해하고, 알고리즘은 결정한다")을
그대로 유지하되, 최종 확정 권한을 "알고리즘의 threshold 판단"에서
"사용자의 확인"으로 한 단계 옮긴다 - 이건 원칙을 어기는 게 아니라,
V0 연구가 밝힌 "알고리즘 혼자로는 threshold를 신뢰할 만큼 정확하게
못 정한다"는 사실을 반영하는 것이다.

## Scrap Flow

1. 사용자가 URL을 스크랩한다.
2. **(선택, 저마찰)** 한 줄 맥락을 물어볼 수 있다 - "왜 저장했나요?"
   같은 placeholder, 건너뛰기 가능. Round 1.5는 4개 질문(purpose/
   time_horizon/trigger/importance)을 썼지만, 실제 제품에서 스크랩할
   때마다 4개를 묻는 건 마찰이 너무 크다 - **최대 1개 자유 입력
   필드로 압축**한다(가장 정보량이 컸던 trigger 계열을 유도하는
   문구로).
3. 알고리즘이 후보 Island를 좁힌다 - Phase 1에서 확립한 Two-stage
   architecture(Experiment #48/#51) 그대로: cosine similarity로
   top-3 후보를 추리는 Recall 단계.
4. LLM pairwise judge가 그 top-3를 재정렬한다(Precision 단계) -
   objective는 **Neutral**을 기본값으로 쓴다(Phase 2에서 가상·실제
   데이터 양쪽에서 가장 일관되게 검증된 Semantic Relatedness family
   대표, Experiment #55/#56/#57). 사용자가 맥락을 입력했다면
   content_summary와 함께 넣는다(Experiment #59 방식).
5. UI는 추천 Island를 **강제가 아니라 제안**으로 보여준다 - 사용자가
   확인하거나, 다른 기존 Island를 고르거나, 새 Island를 만들 수
   있다.
6. 사용자의 정정은 기록만 해둔다(V1 스코프에서는 재학습에 안 씀 -
   "이 정정을 다음 추천에 어떻게 반영할지"는 Adaptive Resolution류의
   질문이라 의도적으로 범위 밖에 둔다).

## 하지 않을 것 (연구 결과 기준)

- **완전 자동·무음 분류에 기대지 않는다** (Finding P2-002/P2-003).
- **스크랩마다 3~4개 구조화된 질문을 강제하지 않는다** - Round 1.5는
  연구용으로 4개를 썼지만, 실제 제품은 최대 1개 자유 입력으로
  압축한다. 마찰이 정보량보다 더 큰 비용이다.
- **모든 도메인에 같은 고정 threshold를 기대하지 않는다**
  (Finding #014, Measurement Family) - Neutral을 기본값으로 삼되,
  도메인마다 다르게 튜닝해야 할 가능성은 열어둔다(Adaptive Resolution,
  V1 스코프 밖).

## V1 구현 시 남는 질문 (아직 답 없음)

- "추천에서 고르기 vs 새로 만들기" UI/UX 구체 설계
- 추천 confidence가 낮을 때(top-3 후보 점수가 다 낮을 때) 사용자에게
  어떻게 보여줄지 - cold start 취급?
- 사용자의 정정 신호를 나중에 개인화(per-user calibration)에 쓸지
  여부 - 이건 다시 Adaptive Resolution 방향이라 지금은 의도적으로
  범위 밖.

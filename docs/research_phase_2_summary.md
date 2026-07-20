# World Engine V0 — Research Phase 2 Summary (RQ10-0, RQ10-1)

> **Phase 2: Complete.** V1 설계는 `docs/v1_design.md` 참고.

## 연구 목표

Phase 1은 "Topic Identity를 어떤 신호로 판별할 것인가"를 물었고, 유일하게
유효했던 신호(Pairwise LLM Judgment)도 판단 해상도가 도메인마다 달라야
한다는 결론(Finding #014)으로 끝났다. Phase 2는 그 "적정 해상도를
도메인마다 어떻게 자동으로 맞출 것인가"(Adaptive Resolution)에서
출발했으나, 연구가 진행되며 질문 자체가 두 번 더 바뀌었다 - 이 문서는
그 세 번의 전환(Adaptive Resolution → Semantic Objective Discovery →
Information Discovery)과 최종 결론을 기록한다.

## RQ10-0 / RQ10-1 요약

| RQ | 질문 | 답 |
|---|---|---|
| RQ10-0 | Semantic resolution은 측정 방법과 독립적으로 존재하는가? | **🟢 Strongly Supported(2개 가상 도메인 재현)** - 완전히 데이터 내재적도, 완전히 측정 artifact도 아니다. Measurement Family(질문의 종류)가 관측되는 geometry 자체를 결정한다. Semantic Relatedness family(Topic/Neutral/Relation)는 서로 유사한 geometry를 만들고, Mechanism family는 별개의 Tree-like geometry를 만든다. |
| RQ10-1 Round 1 (Objective Discovery) | 어떤 semantic objective가 **실제** 사용자의 조직 방식을 가장 잘 예측하는가? | 실제 데이터(N=25)에서 Mechanism은 적용 범위 밖(AUC 0.500), Neutral/Relation/Retrieval은 서로 거의 동등(AUC 0.90~0.92)하고 그 이상 개선 안 됨 - "어떤 objective인가"는 이 지점에서 막다른 질문이었다. |
| RQ10-1 Round 1.5 (Information Discovery) | 사람이 개인 지식을 조직할 때 실제로 어떤 **정보**를 쓰는가? | 진짜 behavioral context(trigger 등)를 주면 방향성 있게 개선되지만(AUC 0.918→0.925, 오류 쌍 다수 완화) 완전 자동화를 뚫을 만큼은 아니다 - "정보가 있으면 도움되지만 불충분하다"가 최종 답. |

## Finding 요약

| Finding | 한 줄 요약 |
|---|---|
| P2-001 | Prompt Objectives Determine the Observable Semantic Geometry - 프롬프트가 관측할 지오메트리 자체를 선택한다(Mechanism→Tree, Relation→연속 relatedness) |
| P2-002 | Prompt Engineering Is Not the Bottleneck for Real Organization - 질문을 바꾸거나 얕은 저장 이유를 더해도 실제 조직 예측력이 안 오른다, 병목은 정보의 부재 |
| P2-003 | Behavioral Context Improves Semantic Organization, But Only Incrementally - 진짜 행동 맥락은 새 정보를 담고 있지만 자동 복원을 완결하기엔 부족하다 |

## 실패한 접근과 왜 실패했는가

1. **Prompt wording 축**(Mechanism/Topic/Neutral/Relation/Retrieval,
   Experiment #52~57) - 가상 데이터(AI Researcher, Backend)에서는
   Measurement Family별로 뚜렷이 구분됐지만, 실제 데이터(여러 인생
   영역이 섞인 개인 스크랩)에서는 Mechanism이 완전히 무너지고(적용
   범위 밖) 나머지 세 objective는 거의 동일한 성능에서 벽에 부딪혔다.
   질문을 아무리 정교하게 바꿔도 이 벽을 못 넘었다(Experiment #57).
2. **얕은 저장 이유 축**(personal_reason, Experiment #58) - "도커
   공부용"처럼 content에서 이미 추론 가능한 정보를 추가해봐야 LLM
   입장에서는 새로울 게 없었다. AUC도 오류 쌍도 거의 안 움직였다.
3. **(부분 성공) 진짜 behavioral context 축**(purpose/time_horizon/
   trigger, Experiment #59) - 방향은 맞았다. content 밖에 있는
   정보(언제/어떤 상황에서 다시 찾을지)를 주자 오류 쌍 다수가
   개선됐다. 하지만 diff-group 쌍도 같이 올라가는 부작용이 있었고,
   절대적인 개선폭도 threshold를 넘길 만큼은 아니었다 - "완전
   자동화"라는 목표 자체가 지금 가진 정보의 한계를 넘어선 것으로
   보인다.

## 최종 결론

> AI가 사용자의 조직 방식을 혼자서 복원할 수는 없다. 하지만 사용자의
> 행동 맥락을 조금 받으면 AI 추천의 품질은 개선된다.

Round 1을 시작할 때의 질문("AI가 사용자의 조직 방식을 복원할 수
있는가?")과 지금의 답은 다르다. 이건 실패가 아니라 **제품 설계
원칙**이다 - "스크랩 → 자동 분류"가 아니라 "스크랩 + 가벼운 행동
맥락 → AI 추천 → 사용자 확인"이라는 구조가 실험적으로 도출됐다. 이
결론은 N=25, 사용자 1명(N=1)의 Pilot에서 나온 것이라 일반화에는
명확한 한계가 있다 - 더 많은 사용자·더 큰 표본에서 재현되는지는
검증되지 않았다.

## 다음 단계

여기서 더 파고드는 것(behavioral context를 더 잘 표현하는 방법,
trigger를 vector화하는 방법 등)은 새로운 연구 질문이 아니라 이미 답이
나온 질문의 성능 개선이다 - Phase 2는 여기서 닫는다. 연구 결과를 그대로
제품 설계로 옮기는 작업이 다음이다: `docs/v1_design.md` 참고.

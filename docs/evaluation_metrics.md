# Evaluation Metrics

V0에서 알고리즘을 검증하기 위해 쓰는 지표 정의. 지표 자체도 실험을 통해 계속 다듬어진다 — 지표가 왜 바뀌었는지는 `experiments/v0_validation.md`의 "Evaluation Metric Update" 항목에 기록한다.

## Similarity Gap
**Definition**: Same-topic 쌍의 평균 Cosine Similarity − Cross-topic 쌍의 평균 Cosine Similarity
**용도**: 같은 Topic/Island가 실제로 다른 것들과 얼마나 잘 구분되는지 측정.

## Marginal Efficiency
**Definition**: ΔGap / ΔTokens — 입력 텍스트를 한 단계 늘릴 때(예: Title→Summary), 추가로 쓴 토큰당 Gap 개선량.
**용도**: 입력 텍스트 길이(Title/Summary/Body)를 얼마나 늘릴지에 대한 비용 대비 효과 판단.
**주의**: `Gap / Total Tokens`(평균 효율)는 분모가 작은 쪽이 항상 유리한 구조적 편향이 있어 사용하지 않는다 (Evaluation Metric Update #1).

## Topic Purity (Finding #006, Experiment #27에서 정의)
**Definition**: (모든 Topic의 "다수결 실제 주제" 스크랩 수 합) / (전체 스크랩 수) — 가중평균이라 큰 Topic의 오염이 더 크게 반영된다. 1.0이면 모든 Topic이 완벽히 순수, 낮을수록 오염이 심하다.
**용도**: 하나의 Topic(건물) 내부 스크랩들이 실제로 같은 하위 주제인지 측정. Island Order Sensitivity(Finding #001, Experiment #9/#10)와 같은 방법론을 Topic 레벨에 적용할 때(같은 데이터, 순서만 바꿔 반복 실행) 이 지표의 변동폭으로 Topic 형성의 순서 의존성을 정량화한다.
**주의**: "실제 주제(ground truth topic)"가 있는 golden/virtual dataset에서만 계산 가능하다 — Topic Duplication Rate와 같은 제약.

## Island Stability (TODO)
정의 미정 — 새 스크랩이 추가돼도 기존 Island 분류가 얼마나 안 흔들리는지 측정할 지표. `map_layout.md`의 "좌표는 계산 결과가 아니라 영속 상태" 원칙과 연결됨.

## Drift (TODO)
정의 미정 — centerVector가 시간이 지나며 초기 성격에서 얼마나 벗어나는지 측정할 지표. `ai_rules.md` Rule 6(Center Vector Update)과 연결됨.

## Topic Duplication Rate (Experiment #21 이후 신설)
**Definition**: (2개 이상의 Island에 걸쳐 나타나는 실제 주제 수) / (전체 distinct 실제 주제 수)
**용도**: Fragmentation of User Interest(Experiment #20)를 정량화하는 지표. Island 개수나 Pairwise F1은 알고리즘 설정에 따라 값이 크게 흔들리지만, 이 지표는 "같은 관심사가 여러 섬에 흩어져 있다"는 사용자가 직접 체감하는 UX 문제를 그대로 측정한다.
**우선순위**: Hybrid Architecture(Night Batch)를 평가할 때는 Island Count/F1보다 이 지표를 우선한다 — Experiment #21에서 Online-only 88.9% → Online+Night Batch 0.0%로 개선된 것을 핵심 결과로 기록.
**주의**: "실제 주제(ground truth topic)"가 있는 golden/virtual dataset에서만 계산 가능하다. 실사용자 데이터에는 ground truth가 없으므로 대체 측정 방법(예: 사용자 설문, Label 유사도 클러스터링)이 V1에서 별도로 필요하다.

## Evaluation Layers: Canonical Taxonomy vs Semantic Evaluation (Experiment #13 이후)

`docs/algorithm_limitations.md` Finding #002(Semantic Boundary Ambiguity)를
발견하면서, golden dataset의 라벨(Backend/AI/Sports)을 유일한 "정답"으로 쓰는
게 위험하다는 게 드러났다. Golden dataset은 진실이 아니라 하나의 관점(사람이
정의한 분류 체계)이다 — 그래서 평가를 두 층으로 분리한다. 둘은 경쟁 관계가
아니라 서로 보완하는 관계다.

### Canonical Taxonomy Evaluation (기존)
- Golden dataset의 사람이 정의한 라벨(Backend/AI/Sports 등)을 정답으로 놓고
  Pairwise F1 등을 계산한다.
- **용도**: 알고리즘 자체의 버그·불안정성(순서 의존성, threshold 민감도 등)을
  잡아내는 회귀 테스트. Finding #001(Order Sensitivity)은 이 층에서 발견되고
  해결됐다.
- **주의**: 이 층의 F1이 낮다고 알고리즘이 "틀렸다"고 단정하면 안 된다 — 라벨
  자체가 유일한 정답이 아닐 수 있다(Finding #002).

### Semantic Evaluation (신설, Experiment #13)
- 정답 라벨 없이, embedding 공간에서 자연스럽게 형성되는 구조(내부/교차 평균
  Cosine Similarity, Topic 간 거리)를 그대로 관찰한다.
- **용도**: World Engine이 "사람이 정의한 카테고리를 재현하는 것"이 아니라
  "사용자의 실제 관심사 연결 구조를 드러내는 것"을 목표로 한다는 철학과 직접
  연결된다. Redis가 Spring/JPA보다 RAG에 더 가깝다는 관찰은 이 층에서만
  보인다 — Canonical Taxonomy 층에서는 "오분류"로만 보였을 결과다.
- 두 층이 일치하지 않는 지점(Backend-AI 경계처럼) 자체가 흥미로운 발견이지
  버그가 아니다.

### 두 층을 같이 쓰는 법
알고리즘을 바꿀 때(threshold 조정, 새 clustering 방식 등)는 Canonical
Taxonomy F1로 회귀만 확인하고, 그 알고리즘이 실제로 만든 구조는 Semantic
Evaluation(내부/교차 유사도 breakdown)으로 따로 들여다봐서 "정답과 다른 게
오답인지, 다른 관점을 드러낸 것인지"를 판단한다.

## Corpus Design: Controlled Corpus vs Natural Corpus (Experiment #15 이후)

Experiment #15(Semantic Atlas, 8개 도메인 96개)에서 Sports와 Finance 일부가
같은 클러스터로 묶이는 현상이 나왔다. 원인 후보 중 하나가 register(뉴스 기사체
vs 기술 블로그체) 혼입이었다 — 아직 검증되지 않은 Hypothesis일 뿐이지만
(`docs/algorithm_limitations.md` Finding #002 Evidence 4 참고), 이 가능성
자체가 golden dataset을 만들 때 통제해야 할 새로운 변수를 알려준다.

이걸 "제거해야 할 노이즈"로만 보면 안 된다 — World Engine이 실제로 다루는
사용자 스크랩도 뉴스/블로그/공식문서/GitHub README/논문처럼 문체가 섞여
있으므로, 문체 혼입은 실제 서비스 데이터의 특성이기도 하다. 그래서 골든셋
목적에 따라 두 가지를 구분해서 관리한다:

### Controlled Corpus
- 같은 내용을 하나의 통일된 register(예: 전부 요약문 톤)로만 작성한다.
- **용도**: 순수 의미(semantic) 유사도만 비교하고 싶을 때. 지금까지의
  `golden_dataset/threshold/*`, `golden_dataset/semantic_atlas/*`는 전부
  이 계열이다(의도한 것은 아니었지만 톤을 통일해서 작성했다).

### Natural Corpus
- 뉴스/블로그/공식문서/README/논문 등 실제 사용자가 저장할 법한 다양한
  register를 의도적으로 섞어서 작성한다.
- **용도**: 실제 서비스 환경에 더 가까운 조건에서 알고리즘이 어떻게
  동작하는지 확인. Controlled Corpus에서 잘 갈리던 도메인이 여기서 안
  갈린다면, 그건 버그가 아니라 "실제 데이터의 register 다양성 자체가 만드는
  결과"로 해석해야 한다.

두 코퍼스에서 같은 실험을 반복했을 때 결과가 다르다면, 그 차이가 바로
register가 클러스터링에 미치는 영향의 크기다 — Experiment #16(Register
Control)이 이 방법론을 실제로 적용한 첫 실험이었다.

### Experiment #16: Register Control (완료, 2026-07-17)
Experiment #15의 Sports+Finance 병합 원인이 register 때문인지 검증했다. 같은
24개 사실을 뉴스 기사체 / 블로그체 / 위키 서술체 / 요약문체 네 가지 register로
각각 다시 써서 동일한 코퍼스를 4벌 만들고(`golden_dataset/register_control/
dataset.json`), 각 버전에서 Sports-Finance 클러스터가 유지되는지 비교했다.
**결과: 4개 register 전부에서 병합됨** — register가 원인이라는 가설은
기각(Rejected)됐다. 자세한 내용은 `docs/algorithm_limitations.md` Finding
#002 Evidence 5 / Rejected Hypothesis #1 참고. 이 결과로 "문체 축"은 닫혔고,
남은 질문은 "그럼 왜 의미적으로 가까운가"로 좁혀졌다 — 아직 미설계.

### 향후 계획 (백로그) — Experiment #14: Human Semantic Clustering Study
개발자 여러 명에게 Spring/Redis/RAG/Kafka/LangGraph/MCP/OpenAI API/Qdrant 같은
스택을 보여주고 직접 관심사 Island를 만들어보게 한다. 단, "Backend/AI로
나눠주세요"처럼 기존 카테고리를 먼저 제시하면 응답이 그 카테고리에 끌려가므로
2단계로 설계한다:

1. **Phase 1 (라벨 없이 자유 분류)**: 스택 목록만 주고 "비슷한 것끼리 자유롭게
   묶어보세요"라고만 요청 — Backend/AI 같은 기존 이름을 먼저 보여주지 않는다.
2. **Phase 2 (사후 질문)**: 각자 묶은 결과에 대해 "왜 그렇게 묶었나요?"를
   물어서 스스로 이름 붙이게 한다(예: 사람 A는 Backend/AI, 사람 B는
   Infra/Application/LLM, 사람 C는 "AI Engineering" 하나로 묶을 수 있음).

사람들끼리도 답이 갈린다면(inter-rater 불일치), Pairwise F1 같은 단일 정답
기반 지표를 절대 지표로 쓸 수 없다는 게 실증되고 Semantic Evaluation의
필요성이 더 강해진다. 결과가 나오면 "Embedding이 만든 구조가 사람의 직관과
얼마나 닮았는가"를 비교하는 것까지 이 실험의 목표다.

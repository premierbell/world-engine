# Evaluation Metrics

V0에서 알고리즘을 검증하기 위해 쓰는 지표 정의. 지표 자체도 실험을 통해 계속 다듬어진다 — 지표가 왜 바뀌었는지는 `experiments/v0_validation.md`의 "Evaluation Metric Update" 항목에 기록한다.

## Similarity Gap
**Definition**: Same-topic 쌍의 평균 Cosine Similarity − Cross-topic 쌍의 평균 Cosine Similarity
**용도**: 같은 Topic/Island가 실제로 다른 것들과 얼마나 잘 구분되는지 측정.

## Marginal Efficiency
**Definition**: ΔGap / ΔTokens — 입력 텍스트를 한 단계 늘릴 때(예: Title→Summary), 추가로 쓴 토큰당 Gap 개선량.
**용도**: 입력 텍스트 길이(Title/Summary/Body)를 얼마나 늘릴지에 대한 비용 대비 효과 판단.
**주의**: `Gap / Total Tokens`(평균 효율)는 분모가 작은 쪽이 항상 유리한 구조적 편향이 있어 사용하지 않는다 (Evaluation Metric Update #1).

## Topic Purity (TODO)
정의 미정 — 하나의 Topic(건물) 내부 스크랩들이 실제로 같은 하위 주제인지 측정할 지표. Step 5(Label Generation) 이후 정의 예정.

## Island Stability (TODO)
정의 미정 — 새 스크랩이 추가돼도 기존 Island 분류가 얼마나 안 흔들리는지 측정할 지표. `map_layout.md`의 "좌표는 계산 결과가 아니라 영속 상태" 원칙과 연결됨.

## Drift (TODO)
정의 미정 — centerVector가 시간이 지나며 초기 성격에서 얼마나 벗어나는지 측정할 지표. `ai_rules.md` Rule 6(Center Vector Update)과 연결됨.

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

### 향후 계획 (백로그)
Human Labeling Study — 개발자 여러 명에게 Spring/Redis/RAG/Kafka/Prompt
Engineering/Vector DB 같은 스택을 보여주고 직접 관심사 Island를 만들어보게
한다. 사람들끼리도 답이 갈린다면(예: 누구는 Backend/AI로 나누고 누구는
"AI Engineering" 하나로 묶는다면), Pairwise F1 같은 단일 정답 기반 지표를
절대 지표로 쓸 수 없다는 게 실증되고 Semantic Evaluation의 필요성이 더
강해진다.

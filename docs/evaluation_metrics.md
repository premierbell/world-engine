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

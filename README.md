# World Engine

관심사가 하나의 살아있는 세계로 성장하는 엔진.

사용자는 콘텐츠를 수집하는 것이 아니라, 자신의 세계를 성장시킨다.
AI는 이해하고, 알고리즘은 결정한다.

## Roadmap

- [x] V0 — Project initialization
- [ ] V0 — Embedding
- [ ] V0 — Cosine similarity
- [ ] V0 — Threshold classification (Island 생성/편입)
- [ ] V0 — Label generation
- [ ] V0 — Growth point
- [ ] V1 — Genesis (지도 UI)

## Structure

```
docs/            설계 문서 (vision, principles, world_rules, growth_rules, ai_rules, map_layout, world_physics)
experiments/      V0 실험 로그
golden_dataset/   회귀 테스트용 라벨링 데이터
prototype/        V0, Python (알고리즘 검증 전용, DB/UI 없음)
backend/          V1부터, Spring Boot
```

## Prototype

```bash
cd prototype
uv sync
uv run run.py
```

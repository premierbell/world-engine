# World Engine

관심사가 하나의 살아있는 세계로 성장하는 엔진.

사용자는 콘텐츠를 수집하는 것이 아니라, 자신의 세계를 성장시킨다.
AI는 이해하고, 알고리즘은 결정한다.

## Roadmap

- [x] V0 — Validation (Python, `prototype/`) — 임베딩/Cosine 유사도/threshold 분류/Label 생성/Growth Point 전부 검증 완료. 결론(Finding P2-002/P2-003): 완전 자동 분류는 현재 기술로 불가능, "AI 추천 + 사용자 확인" 구조로 V1 설계.
- [x] V1 — Genesis (Java/Spring Boot, `server/`) — Scrap Flow(추출 → 임베딩 → 추천 → 사용자 확인) 전체 루프 완주. 조회 API, 정정 기록, 최소 UI까지 완료. 회고는 `docs/v1_retrospective.md`.
- [ ] V2 — Evolution (성장 지표, 시각적 티어, Topic 분화) - Topic 후보 생성(AI)→생성 폼 연결까지 완료(PR #80~83), 성장 지표/시각적 티어/Topic 이름 AI 제안은 아직. 상세는 `docs/v2_design.md` 참고

각 Phase의 상세 근거는 `docs/research_phase_1_summary.md`, `docs/research_phase_2_summary.md`, `docs/v1_design.md`, `docs/v1_retrospective.md` 참고. PR 단위 작업 기록은 `experiments/v0_validation.md`에 누적.

## Structure

```
docs/             설계 문서 (vision, principles, world_rules, growth_rules, ai_rules, v1_design, content_extraction 등)
experiments/      작업 로그 (V0 연구 + V1 구현, PR 단위로 누적)
golden_dataset/   회귀 테스트용 라벨링 데이터
prototype/        V0, Python (알고리즘 검증 전용, DB/UI 없음)
server/           V1부터, Spring Boot(Java 21) + 최소 정적 UI
```

## Prototype (V0, Python)

```bash
cd prototype
uv sync
uv run run.py
```

## Server (V1, Java/Spring Boot)

### 준비물

- Java 21
- Docker (Postgres용 — `server/compose.yaml`을 Spring Boot가 자동으로 띄움)
- `OPENAI_API_KEY` — `prototype/.env`에 이미 있음

### 실행

```bash
cd server
set -a && source ../prototype/.env && set +a   # OPENAI_API_KEY를 환경변수로
./gradlew bootRun
```

Docker가 떠 있으면 `compose.yaml`의 Postgres 컨테이너를 Spring Boot가 자동으로 시작한다. `spring.jpa.hibernate.ddl-auto=update`라 스키마는 Entity 기준으로 자동 반영되고, 기존 데이터는 보존된다(Flyway/Liquibase 같은 정식 마이그레이션은 아직 안 씀 — 스키마 이력 관리가 필요해지면 그때 도입 검토).

떠 있는 상태에서 `http://localhost:8080`으로 들어가면 스크랩 → AI 추천 → Island 확정까지 실제로 클릭해볼 수 있는 최소 UI(`server/src/main/resources/static/`)가 뜬다.

### 테스트

```bash
./gradlew test        # 오프라인, Docker/실제 API 키 불필요 (H2 사용)
./gradlew liveTest     # 실제 외부 URL/OpenAI API를 호출하는 테스트 - OPENAI_API_KEY 필요
```

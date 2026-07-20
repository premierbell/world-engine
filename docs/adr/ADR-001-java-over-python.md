# ADR-001: V1 백엔드는 Java/Spring으로 만든다

## Context

V0(Validation)는 Python으로 진행했다 - LLM 프롬프트를 수십 번 바꾸고,
실험 스크립트를 반복 실행하고, 결과를 즉시 분석해야 하는 연구 코드였고,
컴파일 사이클 없이 빠르게 반복하는 게 중요했다(`docs/research_phase_1_
summary.md`, `docs/research_phase_2_summary.md` 참고).

V1(Genesis)은 역할이 다르다 - URL 스크랩 API, 인증, DB, Island CRUD,
추천 API, 배포·운영이 필요한 전형적인 백엔드 서비스다. Research Code가
아니라 Product Code다.

## Decision

Java 21 + Spring Boot로 V1을 만든다.

## Alternatives

- **Python 유지**: `prototype/`을 그대로 확장. 하지만 V1이 실제로 쓰는
  AI는 모델을 직접 학습시키는 게 아니라 Embedding/LLM API를 호출하는
  것뿐이라, Python의 AI 생태계(PyTorch 등) 이점이 V1에는 거의 없다.
  반면 API 서버/인증/DB/배포 같은 백엔드 인프라는 Java/Spring 쪽 경험이
  훨씬 많다.
- **Node/TypeScript**: 프론트(World 시각화)와 언어를 통일할 수 있다는
  장점은 있으나, 다른 포트폴리오 프로젝트와의 일관성 이점이 없다.

## Consequences

- 다른 포트폴리오 프로젝트(NewsMailer, BuzzerBidder, Notification
  Platform, MotiPeople)와 "Java/Spring 기반으로 여러 성격의 백엔드
  시스템을 설계·구현했다"는 일관된 스토리를 만들 수 있다.
- Content Extraction 쪽 라이브러리 생태계는 Python(`trafilatura` 등)이
  더 성숙하다 - 이 부분만 Java 생태계(jsoup+readability4j)로 검증해보고,
  품질이 명확히 부족하면 그때만 별도 Python 마이크로서비스로 분리한다
  (`docs/content_extraction.md`의 "품질 지표" 참고 - 감이 아니라
  측정된 성공률로 결정).
- V0의 Python 연구 코드(`prototype/`)는 그대로 보존한다 - V1과는 별개의
  자산이고, 재현 가능한 연구 기록으로서 계속 남겨둔다.

# ADR-002: Feature-first 패키지 구조를 쓴다

## Context

기존 Java/Spring 포트폴리오 프로젝트 두 개를 비교했다:

- `notification-platform`: `com.example.notification.{api,auth,domain,
  messaging,ratelimit,repository,scheduler,service,template}` - 레이어와
  기능이 섞인, 상대적으로 평평한 구조. `group`도 Spring Initializr
  기본값(`com.example`)이 그대로 남아있었다.
- `motipeople-server`: `com.motipeople.{feature}/{controller,dto,
  entity,repository,service}` - 기능마다 하위 패키지를 완결된 세트로
  갖추는 구조(`user`, `feed`, `routine`, `notification` 등). `common/`
  에 config/exception/response/security/util처럼 진짜 공용 코드만 모음.

World Engine V1은 앞으로 `extraction`, `scrap`, `island`,
`recommendation`, `world` 같은 여러 기능이 독립적으로 성장할 것으로
예상된다 - motipeople-server가 이미 여러 기능(user/feed/routine/
notification/...)을 가진 실제 서비스로 성장한 선례이자, 사용자가
"주로 쓰던" 컨벤션이라 앞으로의 World Engine 모습에 더 가깝다.

## Decision

`com.worldengine.{feature}/{controller,dto,model,service,strategy,
client}` 형태의 feature-first 구조를 쓴다. 진짜 공용 코드만 `common/`
에 둔다. 예를 들어 지금 만든 `extraction`은:

```
com.worldengine.extraction
├── model      (ExtractionResult, 관련 enum)
├── strategy   (ExtractionStrategy 인터페이스와 구현체들)
└── service    (ContentExtractionService)
```

controller/client는 실제로 필요해지는 시점(REST API 노출, 외부 API
호출)에 추가한다 - 아직 없는 걸 미리 만들지 않는다.

## Alternatives

- **레이어 전역 분리**(`controller/`, `service/`, `repository/`를
  최상위에 두고 그 아래 기능별 클래스를 두는 방식): notification-
  platform이 부분적으로 이 방식에 가까웠다. 기능이 몇 개 안 될 때는
  괜찮지만, 기능이 늘어날수록 하나의 기능을 수정하려면 여러 최상위
  패키지를 오가야 해서 탐색 비용이 커진다.

## Consequences

- 새 기능(scrap, island, recommendation, world)을 추가할 때마다
  독립된 패키지를 만들면 되고, 기존 기능 코드를 건드릴 일이 없다.
- motipeople-server와 동일한 규칙이라 두 프로젝트를 오갈 때 탐색
  비용이 낮다.
- `extraction`처럼 다른 기능에서도 재사용될 가능성이 있는 코드(예:
  나중에 `scrap`이 `extraction`을 호출)는 명시적으로 의존 방향을
  관리해야 한다 - 이건 기능이 늘어나면서 실제로 부딪힐 때 별도 ADR로
  다룬다.

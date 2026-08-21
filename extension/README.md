# World Engine 스크랩 확장

지금 보고 있는 탭을 클릭 한 번으로 World Engine에 스크랩하는 Chrome 확장(Manifest V3). 새 백엔드 없이 기존 `POST /api/scraps`, `POST /api/scraps/{id}/confirm`, `GET /api/islands`만 재사용한다.

로컬(`http://localhost:8080`)에서 도는 서버를 호출하므로, **서버가 켜져 있는 이 컴퓨터의 Chrome에서만 동작한다.**

## 설치 (unpacked)

1. `cd server && ./gradlew bootRun`으로 서버를 켠다.
2. Chrome에서 `chrome://extensions` 접속
3. 우측 상단 "개발자 모드" 켜기
4. "압축해제된 확장 프로그램을 로드합니다" 클릭 → 이 `extension/` 폴더 선택
5. 툴바에 확장 아이콘(기본 퍼즐 아이콘, 커스텀 아이콘은 아직 없음)이 생김 - 아무 페이지에서나 클릭하면 바로 스크랩 시작

## 구조

- `manifest.json` - MV3 설정. `host_permissions`에 `http://localhost:8080/*`을 넣어서, 팝업(확장 페이지)에서의 fetch가 서버 쪽 CORS 설정 없이도 허용되는 것을 노린 것 - **아직 실제로 검증은 안 됨, CORS 에러가 나면 서버에 CORS 설정을 추가해야 함.**
- `popup.html`/`popup.css`/`popup.js` - 팝업 UI. `client/src/components/RecommendPanel.tsx`와 같은 확정 흐름(추천 top-3 / 다른 Island 선택 / 새 Island 만들기)을 그대로 재구현.

## 알려진 제한

- 커스텀 아이콘 없음(기본 아이콘으로 동작) - 지금은 기능이 우선.
- 로컬 전용 - 배포된 서버 주소로 바꾸려면 `popup.js`의 `API_BASE`만 고치면 됨.

// World Engine 확장 팝업 - 지금 보고 있는 탭의 URL을 바로 스크랩하고,
// client/src/components/RecommendPanel.tsx와 같은 확정 흐름(추천 top-3
// + 다른 Island 선택 + 새 Island 만들기)을 팝업 하나로 압축한 것.
// 새 백엔드 없이 기존 /api/scraps, /api/scraps/{id}/confirm,
// /api/islands만 그대로 재사용한다.

const API_BASE = 'http://localhost:8080';

// client/src/pages/HomePage.tsx의 FAILURE_MESSAGES와 같은 문구.
const FAILURE_MESSAGES = {
  ROBOTS_BLOCKED: '사이트가 자동 접근을 차단했어요.',
  NETWORK_ERROR: '연결에 실패했어요.',
  TIMEOUT: '응답이 너무 늦어 시간 초과됐어요.',
  UNSUPPORTED_SOURCE: '지원하지 않는 형식의 URL이에요.',
  EMPTY_CONTENT: '본문을 찾지 못했어요.',
  LOGIN_REQUIRED: '로그인이 필요한 페이지로 보여요.',
};

const statusEl = document.getElementById('status');
const resultEl = document.getElementById('result');
const titleEl = document.getElementById('scrap-title');
const recommendationsEl = document.getElementById('recommendations');
const otherIslandSelect = document.getElementById('other-island-select');
const newIslandInput = document.getElementById('new-island-name');
const confirmMessageEl = document.getElementById('confirm-message');
const duplicateNoticeEl = document.getElementById('duplicate-notice');
const duplicateTextEl = document.getElementById('duplicate-text');
const duplicateViewButton = document.getElementById('duplicate-view');
const duplicateForceButton = document.getElementById('duplicate-force');

let currentScrapId = null;
let currentTabUrl = null;
let currentDuplicateIslandId = null;

async function apiFetch(path, options) {
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: options && options.body ? { 'Content-Type': 'application/json' } : undefined,
  });

  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error((body && body.message) || `요청 실패: ${response.status}`);
  }

  // client/src/api/client.ts의 apiFetch와 같은 이유 - confirm 응답은
  // 항상 JSON이라 이 프로젝트에선 안 걸리지만, 나중에 void 응답을
  // 재사용할 때를 대비해 같은 방어를 맞춰둔다.
  if (response.status === 204 || response.headers.get('content-length') === '0') {
    return undefined;
  }

  return response.json();
}

function renderRecommendations(recommendations) {
  recommendationsEl.innerHTML = '';

  if (!recommendations || recommendations.length === 0) {
    const empty = document.createElement('p');
    empty.className = 'empty';
    empty.textContent = '추천 후보 없음 - 아래에서 다른 Island를 골라주세요.';
    recommendationsEl.appendChild(empty);
    return;
  }

  recommendations.forEach((rec) => {
    const button = document.createElement('button');
    button.type = 'button';
    button.textContent = `${rec.islandName} (score: ${rec.llmScore.toFixed(2)})`;
    button.addEventListener('click', () => confirmScrap({ islandId: rec.islandId }));
    recommendationsEl.appendChild(button);
  });
}

async function populateIslandSelect() {
  try {
    const islands = await apiFetch('/api/islands');
    islands
      .slice()
      .sort((a, b) => a.name.localeCompare(b.name))
      .forEach((island) => {
        const option = document.createElement('option');
        option.value = String(island.id);
        option.textContent = `${island.name} (${island.scrapCount})`;
        otherIslandSelect.appendChild(option);
      });
  } catch (err) {
    // Island 목록을 못 가져와도 top-3 추천/새 Island 만들기는 여전히
    // 쓸 수 있으니 팝업 전체를 막지 않는다.
    console.error('Island 목록을 가져오지 못함', err);
  }
}

async function confirmScrap(body) {
  if (!currentScrapId) {
    return;
  }
  try {
    const data = await apiFetch(`/api/scraps/${currentScrapId}/confirm`, {
      method: 'POST',
      body: JSON.stringify(body),
    });
    confirmMessageEl.textContent = `"${data.islandName}"(으)로 확정됨`;
  } catch (err) {
    confirmMessageEl.textContent = `확정 실패: ${err.message}`;
  }
}

function applyScrapResult(data, fallbackUrl) {
  currentScrapId = data.scrapId;
  statusEl.hidden = true;
  duplicateNoticeEl.hidden = true;
  resultEl.hidden = false;
  titleEl.textContent = data.title || fallbackUrl;

  if (data.status === 'FAILED') {
    const reason = (data.failureReason && FAILURE_MESSAGES[data.failureReason]) || '본문을 가져오지 못했어요.';
    confirmMessageEl.textContent = `${reason} (URL만 저장됨)`;
  }

  renderRecommendations(data.recommendations);
  populateIslandSelect();
}

// client/src/pages/HomePage.tsx의 duplicate 처리와 같은 로직 - 이미
// 있는 URL이면 새로 만들지 않고 기존 스크랩 정보만 보여준다("그래도
// 저장" 누르면 force:true로 다시 호출).
async function captureCurrentTab(force) {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab || !tab.url) {
    statusEl.textContent = '현재 탭의 URL을 가져올 수 없어요.';
    return;
  }
  currentTabUrl = tab.url;

  try {
    const data = await apiFetch('/api/scraps', {
      method: 'POST',
      body: JSON.stringify({ url: tab.url, force: force || null }),
    });

    if (data.duplicate) {
      statusEl.hidden = true;
      duplicateNoticeEl.hidden = false;
      currentScrapId = data.scrapId;
      currentDuplicateIslandId = data.existingIslandId;
      duplicateTextEl.textContent = `이미 스크랩한 URL이에요: "${data.title || tab.url}"${
        data.existingIslandName ? ` — ${data.existingIslandName} 섬에 있음` : ' — 아직 정리할 스크랩 상태'
      }`;
      duplicateViewButton.hidden = data.existingIslandId === null;
      return;
    }

    applyScrapResult(data, tab.url);
  } catch (err) {
    statusEl.textContent = `스크랩 실패: ${err.message}`;
  }
}

duplicateViewButton.addEventListener('click', () => {
  if (currentDuplicateIslandId === null || currentDuplicateIslandId === undefined) {
    return;
  }
  chrome.tabs.create({ url: `http://localhost:5173/islands/${currentDuplicateIslandId}` });
});

duplicateForceButton.addEventListener('click', () => {
  statusEl.hidden = false;
  statusEl.textContent = '스크랩하는 중...';
  duplicateNoticeEl.hidden = true;
  captureCurrentTab(true);
});

document.getElementById('confirm-other').addEventListener('click', () => {
  const islandId = Number(otherIslandSelect.value);
  if (!islandId) {
    confirmMessageEl.textContent = 'Island를 먼저 선택해주세요.';
    return;
  }
  confirmScrap({ islandId });
});

document.getElementById('confirm-new').addEventListener('click', () => {
  const name = newIslandInput.value.trim();
  if (!name) {
    confirmMessageEl.textContent = '새 Island 이름을 입력해주세요.';
    return;
  }
  confirmScrap({ newIslandName: name });
});

captureCurrentTab();

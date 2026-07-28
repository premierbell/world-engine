const FAILURE_MESSAGES = {
  ROBOTS_BLOCKED: '사이트가 자동 접근을 차단했어요.',
  NETWORK_ERROR: '연결에 실패했어요.',
  TIMEOUT: '응답이 너무 늦어 시간 초과됐어요.',
  UNSUPPORTED_SOURCE: '지원하지 않는 형식의 URL이에요.',
  EMPTY_CONTENT: '본문을 찾지 못했어요.',
  LOGIN_REQUIRED: '로그인이 필요한 페이지로 보여요.'
};

const scrapForm = document.getElementById('scrap-form');
const urlInput = document.getElementById('url-input');
const contextInput = document.getElementById('context-input');
const scrapResult = document.getElementById('scrap-result');
const recommendSection = document.getElementById('recommend-section');
const recommendList = document.getElementById('recommend-list');
const newIslandInput = document.getElementById('new-island-input');
const newIslandConfirmBtn = document.getElementById('new-island-confirm');
const confirmResult = document.getElementById('confirm-result');
const islandList = document.getElementById('island-list');
const scrapList = document.getElementById('scrap-list');
const pendingList = document.getElementById('pending-list');
const islandDetailSection = document.getElementById('island-detail-section');
const islandDetailTitle = document.getElementById('island-detail-title');
const islandDetailVariance = document.getElementById('island-detail-variance');
const islandDetailOverride = document.getElementById('island-detail-override');
const islandDetailScraps = document.getElementById('island-detail-scraps');

let currentScrapId = null;

scrapForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  scrapResult.textContent = '스크랩하는 중...';
  confirmResult.textContent = '';
  recommendSection.hidden = true;

  const response = await fetch('/scraps', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ url: urlInput.value, userContext: contextInput.value || null })
  });

  if (!response.ok) {
    scrapResult.textContent = `실패 (HTTP ${response.status})`;
    return;
  }

  const data = await response.json();
  currentScrapId = data.scrapId;

  if (data.status === 'FAILED') {
    const reason = FAILURE_MESSAGES[data.failureReason] || '본문을 가져오지 못했어요.';
    scrapResult.textContent = `${reason} (URL만 저장됨)`;
  } else {
    scrapResult.textContent = `제목: ${data.title ?? '(없음)'}\n상태: ${data.status}`;
  }

  renderRecommendations(data.recommendations);
  recommendSection.hidden = false;
  loadScraps();
  loadPendingScraps();
});

function renderRecommendations(recommendations) {
  recommendList.innerHTML = '';

  if (recommendations.length === 0) {
    const li = document.createElement('li');
    li.textContent = '추천 후보 없음 - 새 Island를 만들어주세요.';
    recommendList.appendChild(li);
    return;
  }

  recommendations.forEach((recommendation) => {
    const li = document.createElement('li');
    const button = document.createElement('button');
    button.textContent = `${recommendation.islandName} (score: ${recommendation.llmScore.toFixed(2)})`;
    button.addEventListener('click', () => confirmScrap({ islandId: recommendation.islandId }));
    li.appendChild(button);
    recommendList.appendChild(li);
  });
}

newIslandConfirmBtn.addEventListener('click', () => {
  const name = newIslandInput.value.trim();
  if (!name) {
    confirmResult.textContent = '새 Island 이름을 입력해주세요.';
    return;
  }
  confirmScrap({ newIslandName: name });
});

async function confirmScrap(body) {
  if (!currentScrapId) {
    return;
  }

  const response = await fetch(`/scraps/${currentScrapId}/confirm`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body)
  });

  if (!response.ok) {
    const error = await response.json();
    confirmResult.textContent = `실패: ${error.message}`;
    return;
  }

  const data = await response.json();
  confirmResult.textContent = `"${data.islandName}"(으)로 확정됨`;
  newIslandInput.value = '';
  recommendSection.hidden = true;
  loadIslands();
  loadScraps();
  loadPendingScraps();
}

async function openPendingScrap(scrap) {
  currentScrapId = scrap.id;
  scrapResult.textContent = `다시 확인 중: ${scrap.title ?? scrap.url}`;
  confirmResult.textContent = '';

  const response = await fetch(`/scraps/${scrap.id}/recommendations`, { method: 'POST' });

  if (!response.ok) {
    const error = await response.json();
    scrapResult.textContent = `추천 재계산 실패: ${error.message}`;
    return;
  }

  const recommendations = await response.json();
  renderRecommendations(recommendations);
  recommendSection.hidden = false;
}

async function loadPendingScraps() {
  const response = await fetch('/scraps?confirmed=false');
  const scraps = await response.json();

  pendingList.innerHTML = '';
  if (scraps.length === 0) {
    pendingList.innerHTML = '<li>정리할 스크랩 없음</li>';
    return;
  }

  scraps.slice().reverse().forEach((scrap) => {
    const li = document.createElement('li');
    const button = document.createElement('button');
    button.textContent = scrap.title ?? scrap.url;
    button.addEventListener('click', () => openPendingScrap(scrap));
    li.appendChild(button);
    pendingList.appendChild(li);
  });
}

async function loadIslands() {
  const response = await fetch('/islands');
  const islands = await response.json();

  islandList.innerHTML = '';
  if (islands.length === 0) {
    islandList.innerHTML = '<li>아직 없음</li>';
    return;
  }

  islands.forEach((island) => {
    const li = document.createElement('li');
    const button = document.createElement('button');
    button.textContent = `${island.name} (${island.scrapCount})`;
    button.addEventListener('click', () => openIslandDetail(island.id));
    li.appendChild(button);
    islandList.appendChild(li);
  });
}

async function openIslandDetail(islandId) {
  const response = await fetch(`/islands/${islandId}`);
  const island = await response.json();

  islandDetailTitle.textContent = island.name;
  islandDetailVariance.textContent = island.cosineVariance == null
    ? '스크랩 2개 미만'
    : island.cosineVariance.toFixed(3);
  islandDetailOverride.textContent = island.overrideRate == null
    ? '추천 이력 없음'
    : `${Math.round(island.overrideRate * 100)}%`;

  islandDetailScraps.innerHTML = '';
  island.scraps.slice().reverse().forEach((scrap) => {
    const li = document.createElement('li');
    const correctedMark = scrap.wasCorrected ? ' ⚠️정정됨' : '';
    li.textContent = `${scrap.title ?? scrap.url}${correctedMark}`;
    islandDetailScraps.appendChild(li);
  });

  islandDetailSection.hidden = false;
}

async function loadScraps() {
  const response = await fetch('/scraps');
  const scraps = await response.json();

  scrapList.innerHTML = '';
  if (scraps.length === 0) {
    scrapList.innerHTML = '<li>아직 없음</li>';
    return;
  }

  scraps.slice().reverse().forEach((scrap) => {
    const li = document.createElement('li');
    const correctedMark = scrap.wasCorrected ? ' ⚠️정정됨' : '';
    li.textContent = `${scrap.title ?? scrap.url}${correctedMark}`;
    scrapList.appendChild(li);
  });
}

document.getElementById('refresh-islands').addEventListener('click', loadIslands);
document.getElementById('refresh-scraps').addEventListener('click', loadScraps);
document.getElementById('refresh-pending').addEventListener('click', loadPendingScraps);

loadIslands();
loadScraps();
loadPendingScraps();

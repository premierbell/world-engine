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
  scrapResult.textContent = `제목: ${data.title ?? '(없음)'}\n상태: ${data.status}`;

  renderRecommendations(data.recommendations);
  recommendSection.hidden = false;
  loadScraps();
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
  loadIslands();
  loadScraps();
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
    li.textContent = `${island.name} (${island.scrapCount})`;
    islandList.appendChild(li);
  });
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

loadIslands();
loadScraps();

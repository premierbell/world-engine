import { useEffect, useRef, useState } from 'react';
import type { MouseEvent as ReactMouseEvent, PointerEvent as ReactPointerEvent } from 'react';
import { formatTier } from '../types/island';
import type { IslandSummary } from '../types/island';
import { composeIsland, OBJECT_SCALE } from '../islandGrowth/compose';
import { countrysideAssetsByCategory, countrysideTerrains } from '../islandGrowth/countryside';

interface MapViewProps {
  islands: IslandSummary[];
  onIslandClick: (islandId: number) => void;
  selectedIslandId?: number | null;
  // 섬이 선택된 상태에서 지도 배경(섬이 아닌 빈 곳)을 클릭했을 때 호출된다 -
  // "지도를 클릭하면 패널이 닫힌다"는 동작을 위한 훅.
  onBackgroundClick?: () => void;
}

interface Camera {
  zoom: number;
  translateX: number;
  translateY: number;
}

interface WorldBounds {
  minX: number;
  maxX: number;
  minY: number;
  maxY: number;
}

const SIZE = 600;
const CENTER = SIZE / 2;
const MIN_CIRCLE_RADIUS = 18;
const MAX_CIRCLE_RADIUS = 50;
const ZOOM_LEVEL = 2.5;
const FIT_PADDING = 150; // World Unit - 섬 원+라벨이 화면 가장자리에 안 붙도록 여백
const MAX_ZOOM = 10;
const WHEEL_ZOOM_SENSITIVITY = 0.0015;
const CLICK_DRAG_THRESHOLD_PX = 6; // 화면 픽셀 기준 - 이 이상 움직여야 "드래그"로 인정(손떨림에도 클릭이 씹히지 않을 정도)

// 조합 에셋(client/src/islandGrowth/)의 지형은 전부 같은 가이드라인
// 범위(x:32~154, y:74~152, docs/island_growth_visual.md "통일된 이미지
// 양식") 안에서 그려진다 - 그 범위의 중심/반너비를 기준으로 기존 원
// 반지름(r)과 맞먹는 크기가 되도록 scale을 계산한다.
const TERRAIN_CENTER_X = 93;
const TERRAIN_CENTER_Y = 113;
const TERRAIN_HALF_EXTENT = 61;

function computeBounds(islands: IslandSummary[]): WorldBounds {
  return {
    minX: Math.min(...islands.map((island) => island.x)),
    maxX: Math.max(...islands.map((island) => island.x)),
    minY: Math.min(...islands.map((island) => island.y)),
    maxY: Math.max(...islands.map((island) => island.y)),
  };
}

// fit-to-bounds 카메라(전체 섬이 화면에 들어오는 최소 줌) - 기본 카메라이자
// 동시에 "이보다 더 축소할 수 없는" 하한선이기도 하다.
function computeFitCamera(bounds: WorldBounds): Camera {
  const width = bounds.maxX - bounds.minX + FIT_PADDING * 2;
  const height = bounds.maxY - bounds.minY + FIT_PADDING * 2;
  const zoom = Math.min(SIZE / width, SIZE / height);
  const targetX = CENTER + (bounds.minX + bounds.maxX) / 2;
  const targetY = CENTER + (bounds.minY + bounds.maxY) / 2;
  return { zoom, translateX: CENTER - zoom * targetX, translateY: CENTER - zoom * targetY };
}

// 휠/드래그로 만들어진 카메라 값을 "화면 밖으로 완전히 벗어나지 않는" 범위로
// 눌러 담는다 - 축소는 fit-to-bounds보다 더 못 나가고(전체 섬이 항상 보임),
// 이동은 섬이 있는 영역이 화면에서 완전히 사라지지 않는 선까지만 허용한다.
function clampCamera(camera: Camera, bounds: WorldBounds, fitZoom: number): Camera {
  const zoom = Math.min(MAX_ZOOM, Math.max(fitZoom, camera.zoom));

  const paddedMinX = CENTER + bounds.minX - FIT_PADDING;
  const paddedMaxX = CENTER + bounds.maxX + FIT_PADDING;
  const paddedMinY = CENTER + bounds.minY - FIT_PADDING;
  const paddedMaxY = CENTER + bounds.maxY + FIT_PADDING;

  const translateX = clampAxis(camera.translateX, zoom, paddedMinX, paddedMaxX);
  const translateY = clampAxis(camera.translateY, zoom, paddedMinY, paddedMaxY);

  return { zoom, translateX, translateY };
}

function clampAxis(translate: number, zoom: number, paddedMin: number, paddedMax: number): number {
  const contentSize = (paddedMax - paddedMin) * zoom;
  if (contentSize <= SIZE) {
    // 내용물이 화면보다 작으면 이동 여지가 없다 - 항상 가운데로
    return CENTER - zoom * ((paddedMin + paddedMax) / 2);
  }
  const min = SIZE - zoom * paddedMax;
  const max = -zoom * paddedMin;
  return Math.min(max, Math.max(min, translate));
}

export function MapView({ islands, onIslandClick, selectedIslandId = null, onBackgroundClick }: MapViewProps) {
  const svgRef = useRef<SVGSVGElement>(null);
  const wasDraggedRef = useRef(false);

  // 사용자가 휠/드래그로 직접 조작한 카메라 - null이면 fit-to-bounds(자동)를
  // 그대로 쓴다. 섬을 선택하거나 선택 해제할 때마다(=selectedIslandId가
  // 바뀔 때마다) 초기화해서, 섬 하나를 봤다가 지도로 돌아오면 자연스럽게
  // fit-to-bounds로 리셋되게 한다.
  const [manualCamera, setManualCamera] = useState<Camera | null>(null);

  useEffect(() => {
    setManualCamera(null);
  }, [selectedIslandId]);

  const maxScrapCount = Math.max(...islands.map((island) => island.scrapCount), 1);
  const selectedIsland = islands.find((island) => island.id === selectedIslandId) ?? null;
  const bounds = islands.length > 0 ? computeBounds(islands) : null;
  const fitCamera = bounds ? computeFitCamera(bounds) : null;

  // 카메라: 화면에 어떻게 보여줄지(줌/이동)만 결정한다 - 섬의 World
  // Unit 좌표(x,y) 자체는 전혀 안 바뀐다. 섬을 선택하면 그 섬으로
  // 확대하고, 선택이 없으면(홈 화면) 모든 섬이 화면 안에 들어오도록
  // 자동으로 축소한다(fit-to-bounds) - 세계가 계속 커져도 항상 전체를
  // 볼 수 있어야 한다. 홈 화면에서는 휠/드래그로 이 자동 카메라 위에
  // 수동 조작(manualCamera)을 얹을 수 있는데, fit-to-bounds보다 더
  // 축소하거나 섬들이 화면 밖으로 완전히 나가도록 이동할 수는 없다
  // (clampCamera). docs/map_home_redesign.md 참고.
  let zoom = 1;
  let translateX = 0;
  let translateY = 0;

  if (selectedIsland) {
    zoom = ZOOM_LEVEL;
    const targetX = CENTER + selectedIsland.x;
    const targetY = CENTER + selectedIsland.y;
    translateX = CENTER - zoom * targetX;
    translateY = CENTER - zoom * targetY;
  } else if (manualCamera) {
    ({ zoom, translateX, translateY } = manualCamera);
  } else if (fitCamera) {
    ({ zoom, translateX, translateY } = fitCamera);
  }

  // 화면 픽셀(clientX/Y) → SVG viewBox 좌표. .map-view가 CSS로
  // 600×600보다 작게 렌더링될 수 있어서(반응형) 1:1 변환이 아니다 -
  // getScreenCTM으로 실제 렌더링 배율을 반영해 변환한다.
  function clientToSvgPoint(clientX: number, clientY: number) {
    const svg = svgRef.current;
    const ctm = svg?.getScreenCTM();
    if (!svg || !ctm) {
      return { x: clientX, y: clientY };
    }
    const point = svg.createSVGPoint();
    point.x = clientX;
    point.y = clientY;
    return point.matrixTransform(ctm.inverse());
  }

  // 휠 줌은 네이티브 리스너로 직접 건다 - React의 onWheel은 기본적으로
  // passive 리스너라 preventDefault()가 조용히 무시되고, 그러면 줌과
  // 동시에 페이지 자체도 스크롤돼버린다(실사용 중 발견).
  useEffect(() => {
    const svg = svgRef.current;
    if (!svg || selectedIsland || !bounds || !fitCamera) {
      return;
    }

    function onWheel(event: WheelEvent) {
      event.preventDefault();
      const cursor = clientToSvgPoint(event.clientX, event.clientY);
      const zoomFactor = Math.exp(-event.deltaY * WHEEL_ZOOM_SENSITIVITY);

      // prev를 기준으로 계산 - 트랙패드처럼 휠 이벤트가 한 프레임 안에
      // 여러 번 들어와도 직전 렌더의 오래된 zoom/translate를 계속
      // 참조하지 않고 항상 최신 상태 위에 누적되게 한다.
      setManualCamera((prev) => {
        const base = prev ?? fitCamera!;
        const nextZoom = base.zoom * zoomFactor;
        const worldX = (cursor.x - base.translateX) / base.zoom;
        const worldY = (cursor.y - base.translateY) / base.zoom;
        return clampCamera(
          { zoom: nextZoom, translateX: cursor.x - nextZoom * worldX, translateY: cursor.y - nextZoom * worldY },
          bounds!,
          fitCamera!.zoom,
        );
      });
    }

    svg.addEventListener('wheel', onWheel, { passive: false });
    return () => svg.removeEventListener('wheel', onWheel);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedIsland, bounds?.minX, bounds?.maxX, bounds?.minY, bounds?.maxY]);

  function handlePointerDown(event: ReactPointerEvent<SVGSVGElement>) {
    if (selectedIsland || !bounds || !fitCamera) {
      return;
    }
    // setPointerCapture는 일부러 안 쓴다 - Chrome에서 pointer capture가
    // 걸린 동안 click 이벤트의 대상이 실제로 클릭한 섬이 아니라 capture를
    // 건 svg 자신으로 재지정되는 경우가 있어서, 그러면 섬 클릭이 아예 안
    // 먹는다(실사용 중 발견). 대신 드래그 추적은 window 레벨 리스너로
    // 한다 - 포인터가 svg 밖으로 나가도 계속 따라간다.
    const start = clientToSvgPoint(event.clientX, event.clientY);
    const pointerId = event.pointerId;
    const startClientX = event.clientX;
    const startClientY = event.clientY;
    const startSvgX = start.x;
    const startSvgY = start.y;
    const startTranslateX = translateX;
    const startTranslateY = translateY;
    const dragZoom = zoom;
    const dragBounds = bounds;
    const dragFitCamera = fitCamera;

    wasDraggedRef.current = false;

    function onWindowPointerMove(moveEvent: PointerEvent) {
      if (moveEvent.pointerId !== pointerId) {
        return;
      }

      // 클릭/드래그 판별은 화면 픽셀로 - SVG 내부 단위로 비교하면 반응형
      // 크기에 따라 몇 픽셀밖에 안 될 수 있어서 손떨림에도 클릭이
      // 드래그로 오인될 수 있다.
      const clientDeltaX = moveEvent.clientX - startClientX;
      const clientDeltaY = moveEvent.clientY - startClientY;
      if (Math.hypot(clientDeltaX, clientDeltaY) > CLICK_DRAG_THRESHOLD_PX) {
        wasDraggedRef.current = true;
      }

      const current = clientToSvgPoint(moveEvent.clientX, moveEvent.clientY);
      const deltaX = current.x - startSvgX;
      const deltaY = current.y - startSvgY;

      setManualCamera(
        clampCamera(
          { zoom: dragZoom, translateX: startTranslateX + deltaX, translateY: startTranslateY + deltaY },
          dragBounds,
          dragFitCamera.zoom,
        ),
      );
    }

    function onWindowPointerUp() {
      window.removeEventListener('pointermove', onWindowPointerMove);
      window.removeEventListener('pointerup', onWindowPointerUp);
      window.removeEventListener('pointercancel', onWindowPointerUp);
    }

    window.addEventListener('pointermove', onWindowPointerMove);
    window.addEventListener('pointerup', onWindowPointerUp);
    window.addEventListener('pointercancel', onWindowPointerUp);
  }

  function handleIslandClick(event: ReactMouseEvent, islandId: number) {
    event.stopPropagation(); // 배경 클릭(패널 닫기)으로 안 번지게
    if (wasDraggedRef.current) {
      return; // 드래그 끝의 클릭은 무시 - 지도 이동과 섬 선택을 구분
    }
    onIslandClick(islandId);
  }

  function handleBackgroundClick() {
    if (selectedIsland) {
      onBackgroundClick?.();
    }
  }

  if (islands.length === 0) {
    return null;
  }

  return (
    <svg
      ref={svgRef}
      className="map-view"
      viewBox={`0 0 ${SIZE} ${SIZE}`}
      role="img"
      aria-label="Island 지도"
      onPointerDown={handlePointerDown}
      onClick={handleBackgroundClick}
    >
      <defs>
        <radialGradient id="map-ocean" cx="30%" cy="15%" r="90%">
          <stop offset="0%" stopColor="#8fb3ae" />
          <stop offset="46%" stopColor="#5c8188" />
          <stop offset="100%" stopColor="#3d5c63" />
        </radialGradient>
        {/* 물결 타일 - world unit 기준(userSpaceOnUse)이라 카메라
            group 안에 두면 확대/축소·이동에 실제로 반응한다(줌 아웃할수록
            타일이 더 촘촘하게 반복되어 보이고, 줌 인하면 파도 하나하나가
            커 보임). 계속 흐르듯 움직이는 애니메이션은 다음 과제 -
            지금은 "줌에 따라 다르게 보인다"까지만.
            각 곡선은 타일 경계(x=0/110/220)에서 접선이 정확히 수평이
            되도록(cubic Bezier 제어점 y를 시작/끝점과 같게) 만들었다 -
            그래야 타일이 옆으로 반복될 때 이음매가 안 끊겨 보인다. */}
        <pattern id="map-waves" width={220} height={110} patternUnits="userSpaceOnUse">
          <path className="wave-line" d="M 0,30 C 55,30 55,45 110,45 C 165,45 165,30 220,30" />
          <path className="wave-line" d="M 0,85 C 55,85 55,100 110,100 C 165,100 165,85 220,85" />
        </pattern>
      </defs>
      <g
        className={`map-camera${manualCamera ? ' map-camera--manual' : ''}`}
        style={{ transform: `translate(${translateX}px, ${translateY}px) scale(${zoom})`, transformOrigin: '0 0' }}
      >
        {/* 바다 배경 - world unit 좌표계라 카메라 group 안에 둬서 섬과
            같이 확대/축소·이동된다(예전엔 화면 고정 배경이라 줌을
            해도 파도 무늬가 똑같아 보이는 문제가 있었음). 섬이 아무리
            멀리 배치돼도 항상 화면을 덮도록 넉넉히 큰 사각형 하나로
            깔아둔다 - 세계가 이 범위를 넘어설 만큼 커지면 그때 키운다. */}
        <rect x={-6000} y={-6000} width={12000} height={12000} fill="url(#map-ocean)" />
        <rect x={-6000} y={-6000} width={12000} height={12000} fill="url(#map-waves)" aria-hidden="true" />
        {islands.map((island) => {
          const x = CENTER + island.x;
          const y = CENTER + island.y;
          const r =
            MIN_CIRCLE_RADIUS + (island.scrapCount / maxScrapCount) * (MAX_CIRCLE_RADIUS - MIN_CIRCLE_RADIUS);
          const islandScale = r / TERRAIN_HALF_EXTENT;

          // 섬을 원 하나가 아니라 지형+나무+건물 등을 조합해서 그린다
          // (client/src/islandGrowth/, docs/island_growth_visual.md).
          // islandId를 시드로 써서 같은 섬은 항상 같은 조합이 나온다.
          const composed = composeIsland(
            island.id,
            island.tier,
            island.topicIds,
            countrysideTerrains,
            countrysideAssetsByCategory,
          );
          const Terrain = composed.terrain.Component;

          return (
            <g
              key={island.id}
              className={`map-island map-island--${island.tier.toLowerCase()}`}
              transform={`translate(${x}, ${y})`}
              onClick={(event) => handleIslandClick(event, island.id)}
            >
              {/* 물그림자 - 섬이 바다 위에 떠 있는 느낌을 주는 용도라
                  지형의 실제 실루엣과 안 맞아도 된다(hit-circle과 같은
                  이유로 반지름 r 기준 단순 타원 하나면 충분). */}
              <ellipse cx={0} cy={r * 0.78} rx={r * 0.92} ry={r * 0.24} className="map-island-water-shadow" />
              {/* 클릭 판정 전용 - 지형이 원이 아니라 불규칙한 모양이라
                  실루엣 밖의 빈틈도 전부 클릭되게 투명 원을 깔아둔다.
                  인라인 style로 줘야 CSS보다 우선순위가 높아서 투명이
                  실제로 유지된다. */}
              <circle r={r} style={{ fill: 'transparent' }} />
              <g transform={`scale(${islandScale}) translate(${-TERRAIN_CENTER_X}, ${-TERRAIN_CENTER_Y})`}>
                <Terrain />
                {composed.objects.map((placed, index) => {
                  const Asset = placed.asset.Component;
                  return (
                    <g key={index} transform={`translate(${placed.x}, ${placed.y}) scale(${OBJECT_SCALE})`}>
                      <Asset />
                    </g>
                  );
                })}
              </g>
              {/* 라벨은 카메라 zoom과 무관하게 항상 같은 화면 크기로 보여야
                  읽을 수 있다(지도가 커질수록 fit-to-bounds가 계속
                  축소시키기 때문). translate로 위치를 먼저 잡고 나서
                  scale(1/zoom)으로 카메라의 확대/축소를 상쇄한다 - 배치
                  카메라의 scale(zoom)과 상쇄되어 최종 렌더 크기는 항상
                  12px 고정, 위치(원과의 간격)는 기존과 동일하다. */}
              <g transform={`translate(0, ${r + 16}) scale(${1 / zoom})`}>
                <text textAnchor="middle">
                  {island.name} ({island.scrapCount}) · {formatTier(island.tier)}
                </text>
              </g>
            </g>
          );
        })}
      </g>
    </svg>
  );
}

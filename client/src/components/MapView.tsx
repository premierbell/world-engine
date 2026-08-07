import { useEffect, useRef, useState } from 'react';
import type { PointerEvent as ReactPointerEvent, WheelEvent as ReactWheelEvent } from 'react';
import type { IslandSummary } from '../types/island';

interface MapViewProps {
  islands: IslandSummary[];
  onIslandClick: (islandId: number) => void;
  selectedIslandId?: number | null;
}

interface Camera {
  zoom: number;
  translateX: number;
  translateY: number;
}

const SIZE = 600;
const CENTER = SIZE / 2;
const MIN_CIRCLE_RADIUS = 18;
const MAX_CIRCLE_RADIUS = 50;
const ZOOM_LEVEL = 2.5;
const FIT_PADDING = 150; // World Unit - 섬 원+라벨이 화면 가장자리에 안 붙도록 여백
const MIN_ZOOM = 0.05; // 실제로 만져보며 튜닝할 값(가안)
const MAX_ZOOM = 10;
const WHEEL_ZOOM_SENSITIVITY = 0.0015;
const DRAG_THRESHOLD = 3; // 이 이상 움직여야 "드래그"로 인정 - 섬 클릭과 구분하는 기준

export function MapView({ islands, onIslandClick, selectedIslandId = null }: MapViewProps) {
  const svgRef = useRef<SVGSVGElement>(null);
  const dragRef = useRef<{
    pointerId: number;
    startSvgX: number;
    startSvgY: number;
    startTranslateX: number;
    startTranslateY: number;
  } | null>(null);
  const wasDraggedRef = useRef(false);

  // 사용자가 휠/드래그로 직접 조작한 카메라 - null이면 fit-to-bounds(자동)를
  // 그대로 쓴다. 섬을 선택하거나 선택 해제할 때마다(=selectedIslandId가
  // 바뀔 때마다) 초기화해서, 섬 하나를 봤다가 지도로 돌아오면 자연스럽게
  // fit-to-bounds로 리셋되게 한다(별도 "리셋" 버튼 없이 이 경로로 대체).
  const [manualCamera, setManualCamera] = useState<Camera | null>(null);

  useEffect(() => {
    setManualCamera(null);
  }, [selectedIslandId]);

  if (islands.length === 0) {
    return null;
  }

  const maxScrapCount = Math.max(...islands.map((island) => island.scrapCount), 1);
  const selectedIsland = islands.find((island) => island.id === selectedIslandId) ?? null;

  // 카메라: 화면에 어떻게 보여줄지(줌/이동)만 결정한다 - 섬의 World
  // Unit 좌표(x,y) 자체는 전혀 안 바뀐다. 섬을 선택하면 그 섬으로
  // 확대하고, 선택이 없으면(홈 화면) 모든 섬이 화면 안에 들어오도록
  // 자동으로 축소한다(fit-to-bounds) - 세계가 계속 커져도 항상 전체를
  // 볼 수 있어야 한다. 홈 화면에서는 휠/드래그로 이 자동 카메라 위에
  // 수동 조작(manualCamera)을 얹을 수 있다. docs/map_home_redesign.md 참고.
  let zoom: number;
  let translateX: number;
  let translateY: number;

  if (selectedIsland) {
    zoom = ZOOM_LEVEL;
    const targetX = CENTER + selectedIsland.x;
    const targetY = CENTER + selectedIsland.y;
    translateX = CENTER - zoom * targetX;
    translateY = CENTER - zoom * targetY;
  } else if (manualCamera) {
    zoom = manualCamera.zoom;
    translateX = manualCamera.translateX;
    translateY = manualCamera.translateY;
  } else {
    const minX = Math.min(...islands.map((island) => island.x));
    const maxX = Math.max(...islands.map((island) => island.x));
    const minY = Math.min(...islands.map((island) => island.y));
    const maxY = Math.max(...islands.map((island) => island.y));

    const width = maxX - minX + FIT_PADDING * 2;
    const height = maxY - minY + FIT_PADDING * 2;

    zoom = Math.min(SIZE / width, SIZE / height);
    const targetX = CENTER + (minX + maxX) / 2;
    const targetY = CENTER + (minY + maxY) / 2;
    translateX = CENTER - zoom * targetX;
    translateY = CENTER - zoom * targetY;
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

  function handleWheel(event: ReactWheelEvent<SVGSVGElement>) {
    if (selectedIsland) {
      return;
    }
    event.preventDefault();

    const cursor = clientToSvgPoint(event.clientX, event.clientY);
    const zoomFactor = Math.exp(-event.deltaY * WHEEL_ZOOM_SENSITIVITY);
    const nextZoom = Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, zoom * zoomFactor));

    // 커서 아래의 World 좌표가 줌 이후에도 같은 화면 위치에 남도록 translate 보정
    const worldX = (cursor.x - translateX) / zoom;
    const worldY = (cursor.y - translateY) / zoom;

    setManualCamera({
      zoom: nextZoom,
      translateX: cursor.x - nextZoom * worldX,
      translateY: cursor.y - nextZoom * worldY,
    });
  }

  function handlePointerDown(event: ReactPointerEvent<SVGSVGElement>) {
    if (selectedIsland) {
      return;
    }
    event.currentTarget.setPointerCapture(event.pointerId);
    const start = clientToSvgPoint(event.clientX, event.clientY);
    wasDraggedRef.current = false;
    dragRef.current = {
      pointerId: event.pointerId,
      startSvgX: start.x,
      startSvgY: start.y,
      startTranslateX: translateX,
      startTranslateY: translateY,
    };
  }

  function handlePointerMove(event: ReactPointerEvent<SVGSVGElement>) {
    const drag = dragRef.current;
    if (!drag || drag.pointerId !== event.pointerId) {
      return;
    }
    const current = clientToSvgPoint(event.clientX, event.clientY);
    const deltaX = current.x - drag.startSvgX;
    const deltaY = current.y - drag.startSvgY;
    if (Math.abs(deltaX) > DRAG_THRESHOLD || Math.abs(deltaY) > DRAG_THRESHOLD) {
      wasDraggedRef.current = true;
    }

    setManualCamera({
      zoom,
      translateX: drag.startTranslateX + deltaX,
      translateY: drag.startTranslateY + deltaY,
    });
  }

  function handlePointerUp() {
    dragRef.current = null;
  }

  function handleIslandClick(islandId: number) {
    if (wasDraggedRef.current) {
      return; // 드래그 끝의 클릭은 무시 - 지도 이동과 섬 선택을 구분
    }
    onIslandClick(islandId);
  }

  return (
    <svg
      ref={svgRef}
      className="map-view"
      viewBox={`0 0 ${SIZE} ${SIZE}`}
      role="img"
      aria-label="Island 지도"
      onWheel={handleWheel}
      onPointerDown={handlePointerDown}
      onPointerMove={handlePointerMove}
      onPointerUp={handlePointerUp}
      onPointerCancel={handlePointerUp}
    >
      <g
        className={`map-camera${manualCamera ? ' map-camera--manual' : ''}`}
        style={{ transform: `translate(${translateX}px, ${translateY}px) scale(${zoom})`, transformOrigin: '0 0' }}
      >
        {islands.map((island) => {
          const x = CENTER + island.x;
          const y = CENTER + island.y;
          const r =
            MIN_CIRCLE_RADIUS + (island.scrapCount / maxScrapCount) * (MAX_CIRCLE_RADIUS - MIN_CIRCLE_RADIUS);

          return (
            <g
              key={island.id}
              className="map-island"
              transform={`translate(${x}, ${y})`}
              onClick={() => handleIslandClick(island.id)}
            >
              <circle r={r} />
              {Array.from({ length: island.topicCount }).map((_, topicIndex) => {
                const dotAngle = (2 * Math.PI * topicIndex) / island.topicCount;
                const dotX = (r - 6) * Math.cos(dotAngle);
                const dotY = (r - 6) * Math.sin(dotAngle);
                return <circle key={topicIndex} cx={dotX} cy={dotY} r={2.5} className="map-island-topic-dot" />;
              })}
              <text y={r + 16} textAnchor="middle">
                {island.name} ({island.scrapCount})
              </text>
            </g>
          );
        })}
      </g>
    </svg>
  );
}

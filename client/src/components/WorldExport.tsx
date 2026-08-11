import { useState } from 'react';
import { fetchWorldExport } from '../api/export';

/**
 * "내 세계 내보내기" - 전체 데이터를 JSON 파일로 다운로드만 한다.
 * Import는 아직 없음(필요해지는 시점에 추가) - 2026-08-06 로컬 DB
 * 소실 사고 이후로 사용자가 직접 스냅샷을 떠둘 수 있는 안전장치.
 */
export function WorldExport() {
  const [status, setStatus] = useState('');
  const [isExporting, setIsExporting] = useState(false);

  const handleExport = async () => {
    setIsExporting(true);
    setStatus('내보내는 중...');
    try {
      const data = await fetchWorldExport();
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement('a');
      anchor.href = url;
      anchor.download = `world-engine-export-${new Date().toISOString().slice(0, 10)}.json`;
      anchor.click();
      URL.revokeObjectURL(url);
      setStatus(`완료 - Island ${data.islands.length}개 · Topic ${data.topics.length}개 · Scrap ${data.scraps.length}개`);
    } catch (err) {
      setStatus(`실패: ${err instanceof Error ? err.message : String(err)}`);
    } finally {
      setIsExporting(false);
    }
  };

  return (
    <section className="card">
      <button type="button" className="world-export-button" onClick={handleExport} disabled={isExporting}>
        🗂 내 세계 내보내기
      </button>
      {status && <p className="result">{status}</p>}
    </section>
  );
}

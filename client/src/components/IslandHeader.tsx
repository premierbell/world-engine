import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import type { IslandDetail } from '../types/island';
import { useDeleteIsland } from '../hooks/useDeleteIsland';
import { useRenameIsland } from '../hooks/useRenameIsland';

interface IslandHeaderProps {
  island: IslandDetail;
}

// 삭제 확인은 window.confirm() 대신 인라인 2단계 버튼으로 처리한다 -
// 이 프로젝트 UI에는 모달 확인창이 없다(claude-in-chrome 자동화도
// 막힘, 기존 확립된 패턴).
export function IslandHeader({ island }: IslandHeaderProps) {
  const navigate = useNavigate();
  const renameMutation = useRenameIsland();
  const deleteMutation = useDeleteIsland();

  const [isEditingName, setIsEditingName] = useState(false);
  const [nameDraft, setNameDraft] = useState(island.name);
  const [isConfirmingDelete, setIsConfirmingDelete] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');

  const startEditing = () => {
    setNameDraft(island.name);
    setIsEditingName(true);
    setErrorMessage('');
  };

  const handleRename = () => {
    const name = nameDraft.trim();
    if (!name || name === island.name) {
      setIsEditingName(false);
      return;
    }
    renameMutation.mutate(
      { islandId: island.id, name },
      {
        onSuccess: () => setIsEditingName(false),
        onError: (err) => setErrorMessage(`이름 변경 실패: ${err.message}`),
      },
    );
  };

  const handleDelete = () => {
    deleteMutation.mutate(island.id, {
      onSuccess: () => navigate('/'),
      onError: (err) => setErrorMessage(`삭제 실패: ${err.message}`),
    });
  };

  return (
    <>
      {isEditingName ? (
        <div className="island-name-edit">
          <input
            type="text"
            value={nameDraft}
            onChange={(event) => setNameDraft(event.target.value)}
            autoFocus
          />
          <button type="button" onClick={handleRename} disabled={renameMutation.isPending}>
            저장
          </button>
          <button type="button" onClick={() => setIsEditingName(false)}>
            취소
          </button>
        </div>
      ) : (
        <div className="island-name-row">
          <h2>{island.name}</h2>
          <button type="button" className="icon-button" onClick={startEditing} aria-label="이름 수정">
            ✏️
          </button>
          {isConfirmingDelete ? (
            <button type="button" className="danger-button" onClick={handleDelete} disabled={deleteMutation.isPending}>
              정말 삭제
            </button>
          ) : (
            <button
              type="button"
              className="icon-button"
              onClick={() => setIsConfirmingDelete(true)}
              aria-label="Island 삭제"
            >
              🗑️
            </button>
          )}
          {isConfirmingDelete && (
            <button type="button" onClick={() => setIsConfirmingDelete(false)}>
              취소
            </button>
          )}
        </div>
      )}
      {isConfirmingDelete && (
        <p className="signal-note">삭제하면 이 안의 Topic도 같이 지워지고, 스크랩은 "정리할 스크랩"으로 돌아갑니다.</p>
      )}
      {errorMessage && <p className="result">{errorMessage}</p>}
      <div className="island-signals">
        <div className="signal">
          <span className="signal-label">Cosine Variance</span>
          <span className="signal-value">
            {island.cosineVariance == null ? '스크랩 2개 미만' : island.cosineVariance.toFixed(3)}
          </span>
        </div>
        <div className="signal">
          <span className="signal-label">Override Rate</span>
          <span className="signal-value">
            {island.overrideRate == null ? '추천 이력 없음' : `${Math.round(island.overrideRate * 100)}%`}
          </span>
        </div>
      </div>
      <p className="signal-note">참고용 관찰 지표입니다 - 이 값이 무언가를 자동으로 결정하지 않습니다.</p>
    </>
  );
}

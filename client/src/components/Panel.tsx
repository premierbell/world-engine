import type { ReactNode } from 'react';

interface PanelProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  children: ReactNode;
}

export function Panel({ isOpen, onClose, title, children }: PanelProps) {
  if (!isOpen) {
    return null;
  }

  return (
    <div className="panel">
      <div className="panel-header">
        <h2>{title}</h2>
        <button type="button" className="panel-close" onClick={onClose} aria-label="닫기">
          ✕
        </button>
      </div>
      <div className="panel-body">{children}</div>
    </div>
  );
}

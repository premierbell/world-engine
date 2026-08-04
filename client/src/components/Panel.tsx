import type { ReactNode } from 'react';

interface PanelProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  children: ReactNode;
  position?: 'left' | 'right' | 'top';
}

const POSITION_CLASS: Record<'left' | 'right' | 'top', string> = {
  left: 'panel-left',
  right: '',
  top: 'panel-top',
};

export function Panel({ isOpen, onClose, title, children, position = 'right' }: PanelProps) {
  if (!isOpen) {
    return null;
  }

  const className = ['panel', POSITION_CLASS[position]].filter(Boolean).join(' ');

  return (
    <div className={className}>
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

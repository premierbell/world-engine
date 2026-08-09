import { useState } from 'react';

// 사이드바 카드(Islands/정리할 스크랩/최근 Scraps)를 접었다 폈다 할 때
// 쓰는 훅 - localStorage에 저장해서 새로고침/재방문해도 사용자가 접어둔
// 상태가 유지된다. key는 카드마다 다른 값을 줘서 서로 독립적으로 기억되게.
export function useCollapsible(key: string, defaultOpen: boolean) {
  const storageKey = `we-card-open:${key}`;
  const [open, setOpen] = useState(() => {
    const saved = localStorage.getItem(storageKey);
    return saved === null ? defaultOpen : saved === 'true';
  });

  const toggle = () => {
    setOpen((prev) => {
      const next = !prev;
      localStorage.setItem(storageKey, String(next));
      return next;
    });
  };

  return [open, toggle] as const;
}

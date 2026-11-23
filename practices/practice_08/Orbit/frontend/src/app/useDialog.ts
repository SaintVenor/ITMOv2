import { useCallback, useRef, useState } from 'react';

export function useDialog<T>() {
  const [value, setValue] = useState<T | null>(null);
  const trigger = useRef<HTMLElement | null>(null);

  const open = useCallback((next: T, returnTo?: HTMLElement | null) => {
    const focused = document.activeElement;
    trigger.current = returnTo ?? (focused instanceof HTMLElement ? focused : null);
    setValue(next);
  }, []);

  function close() {
    const target = trigger.current;
    setValue(null);
    if (target) requestAnimationFrame(() => { if (target.isConnected) target.focus(); });
  }

  return { value, open, close };
}

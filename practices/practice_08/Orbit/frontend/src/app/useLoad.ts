import { useEffect, useReducer, useState } from 'react';

interface Result<T> {
  key: number;
  load: (signal: AbortSignal) => Promise<T>;
  data?: T;
  failed: boolean;
}

export function useLoad<T>(load: (signal: AbortSignal) => Promise<T>, enabled = true) {
  const [key, refresh] = useReducer(value => value + 1, 0);
  const [result, setResult] = useState<Result<T>>();

  useEffect(() => {
    if (!enabled) return;
    const controller = new AbortController();
    load(controller.signal).then(data => {
      if (!controller.signal.aborted) setResult({ key, load, data, failed: false });
    }).catch(() => {
      if (!controller.signal.aborted) setResult({ key, load, failed: true });
    });
    return () => controller.abort();
  }, [enabled, key, load]);

  const sameSource = enabled && result?.load === load ? result : undefined;
  const current = sameSource?.key === key ? sameSource : undefined;
  return { data: sameSource?.data, failed: current?.failed ?? false, loading: enabled && !current, refresh };
}

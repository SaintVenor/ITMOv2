import { useRef, useState } from 'react';
import { ApiError } from './api';

export function useMutation() {
  const lock = useRef(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<ApiError>();

  async function submit<T>(operation: () => Promise<T>, saved: (result: T) => void) {
    if (lock.current) return;
    lock.current = true;
    setBusy(true);
    setError(undefined);
    try {
      const result = await operation();
      saved(result);
    } catch (failure) {
      setError(failure instanceof ApiError ? failure : new ApiError('Не удалось связаться с сервером. Повторите попытку.'));
    } finally {
      lock.current = false;
      setBusy(false);
    }
  }

  return { busy, error, submit, isLocked: () => lock.current, clearError: () => setError(undefined) };
}

export function useOperationId() {
  const operation = useRef<{ id: string; payload: string } | undefined>(undefined);
  return (value: object) => {
    const payload = JSON.stringify(value);
    if (operation.current?.payload !== payload) operation.current = { id: crypto.randomUUID(), payload };
    return operation.current.id;
  };
}

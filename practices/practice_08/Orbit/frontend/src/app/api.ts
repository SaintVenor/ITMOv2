export type Area = 'study' | 'personal';
export type EntryKind = 'deadline' | 'event' | 'birthday';
export type Kind = EntryKind | 'step';
export type Frequency = 'daily' | 'weekly' | 'monthly' | 'yearly';
export type DeletionScope = 'all' | 'one' | 'before' | 'after';

export interface EntryFields {
  title: string;
  kind: EntryKind;
  area: Area;
  startDate: string | null;
  endDate: string | null;
  startTime: string | null;
  endTime: string | null;
  birthMonth: number | null;
  birthDay: number | null;
  frequency?: Frequency | null;
}

export interface CalendarItem {
  id: string;
  kind: Kind;
  title: string;
  area: Area;
  startDate: string;
  endDate: string;
  startTime?: string | null;
  endTime?: string | null;
  planId?: string;
  planTitle?: string;
  done?: boolean;
  frequency?: Frequency;
  occurrenceDate?: string;
  seriesStart?: string | null;
  seriesEnd?: string | null;
}

export class ApiError extends Error {
  constructor(message: string, public fields: Record<string, string> = {}) {
    super(message);
  }
}

export async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch('/api' + path, options);
  if (!response.ok) {
    const failure = await response.json().catch(() => null);
    const detail = failure?.detail;
    const fields: Record<string, string> = {};
    if (Array.isArray(detail)) {
      for (const item of detail) {
        const field = item?.loc?.at(-1);
        if (typeof field === 'string' && typeof item.msg === 'string') fields[field] = item.msg;
      }
    }
    throw new ApiError(typeof detail === 'string' ? detail : 'Сервер не смог выполнить запрос.', fields);
  }
  return response.status === 204 ? undefined as T : response.json();
}

export function json(method: string, payload: object): RequestInit {
  return { method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) };
}

export const api = {
  calendar(from: string, to: string, signal: AbortSignal) {
    return request<{ items: CalendarItem[] }>('/calendar?' + new URLSearchParams({ from, to }), { signal });
  },
  createEntry(id: string, fields: EntryFields) {
    return request<EntryFields & { id: string }>('/entries', json('POST', { id, ...fields }));
  },
  editEntry(id: string, fields: EntryFields) {
    return request<EntryFields & { id: string }>('/entries/' + encodeURIComponent(id), json('PATCH', fields));
  },
  deleteEntry(id: string, scope: DeletionScope, occurrence?: string) {
    const query = scope === 'all' ? '' : '?' + new URLSearchParams({ scope, occurrence: occurrence ?? '' });
    return request<void>('/entries/' + encodeURIComponent(id) + query, { method: 'DELETE' });
  },
};

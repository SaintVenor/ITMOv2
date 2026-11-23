import { getISODay } from 'date-fns';
import { json, request } from '../../app/api';
import { asDate, daysBetween, moveDay } from './dates';

export const lessonTypes = {
  lecture: 'Лекция', practice: 'Практика', lab: 'Лабораторная', consultation: 'Консультация',
} as const;
export type LessonType = keyof typeof lessonTypes;
export const lessonLabel = (type?: LessonType | null) => type ? lessonTypes[type] : 'Пара';

export interface LessonFields {
  weekday: number;
  subject: string;
  room: string;
  startTime: string;
  endTime: string;
  termStart: string;
  termEnd: string;
  weekInterval?: 1 | 2;
  firstDate?: string | null;
  lessonType?: LessonType | null;
}

export interface Lesson extends LessonFields {
  id: string;
}

export const weekdays = ['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота', 'Воскресенье'];

export function firstLessonDate(lesson: LessonFields) {
  return lesson.firstDate ?? moveDay(lesson.termStart, (lesson.weekday - getISODay(asDate(lesson.termStart)) + 7) % 7);
}

export function lessonsOn(items: Lesson[], day: string) {
  const weekday = getISODay(asDate(day));
  return items.filter(item => {
    if (item.weekday !== weekday || item.termStart > day || day > item.termEnd) return false;
    const elapsed = daysBetween(day, firstLessonDate(item));
    return elapsed >= 0 && elapsed % (7 * (item.weekInterval ?? 1)) === 0;
  });
}

const plural = new Intl.PluralRules('ru');

export function lessonCount(count: number) {
  const form = plural.select(count);
  return count + ' ' + (form === 'one' ? 'пара' : form === 'few' ? 'пары' : 'пар');
}

export const lessonApi = {
  list(from: string, to: string, signal: AbortSignal) {
    return request<{ items: Lesson[] }>('/lessons?' + new URLSearchParams({ from, to }), { signal });
  },
  create(id: string, fields: LessonFields) {
    return request<Lesson>('/lessons', json('POST', { id, ...fields }));
  },
  edit(id: string, fields: LessonFields) {
    return request<Lesson>('/lessons/' + encodeURIComponent(id), json('PUT', fields));
  },
  remove(id: string) {
    return request<void>('/lessons/' + encodeURIComponent(id), { method: 'DELETE' });
  },
};

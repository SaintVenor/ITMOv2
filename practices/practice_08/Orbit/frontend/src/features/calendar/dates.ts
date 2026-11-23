import {
  addDays, differenceInCalendarDays, eachDayOfInterval, endOfMonth, endOfWeek, format,
  isValid, parseISO, startOfMonth, startOfWeek,
} from 'date-fns';
import { ru } from 'date-fns/locale';
import type { CalendarItem, Kind } from '../../app/api';

export const dateKey = (date: Date) => format(date, 'yyyy-MM-dd');
export const monthKey = (date: Date) => format(date, 'yyyy-MM');
export const asDate = (value: string) => parseISO(value);
export const longDate = (value: string) => format(asDate(value), 'd MMMM', { locale: ru });
export const fullDate = (value: string) => format(asDate(value), 'EEEE, d MMMM yyyy', { locale: ru });
const shortMonths = ['янв', 'фев', 'мар', 'апр', 'май', 'июн', 'июл', 'авг', 'сен', 'окт', 'ноя', 'дек'];
export function shortDate(value: string) {
  const date = asDate(value);
  return date.getDate() + ' ' + shortMonths[date.getMonth()];
}
export const daysBetween = (later: string, earlier: string) => differenceInCalendarDays(asDate(later), asDate(earlier));

export function isDateKey(value: string | null): value is string {
  return value !== null && /^(?!0000)\d{4}-\d{2}-\d{2}$/.test(value) && isValid(asDate(value));
}

export function monthDays(month: Date) {
  const first = startOfMonth(month);
  const last = endOfMonth(month);
  const start = startOfWeek(first, { weekStartsOn: 1 });
  const end = endOfWeek(last, { weekStartsOn: 1 });
  const days = eachDayOfInterval({ start, end }).map(dateKey);
  return { first: dateKey(first), last: dateKey(last), from: dateKey(start), to: dateKey(end), days };
}

export const moveDay = (date: string, offset: number) => dateKey(addDays(asDate(date), offset));

export function birthdayInViewYear(day: string, month: number, date: number) {
  const suffix = [month, date].map(value => String(value).padStart(2, '0')).join('-');
  const year = Number(day.slice(0, 4));
  for (let candidate = year; candidate <= Math.min(year + 8, 9999); candidate += 1) {
    const occurrence = String(candidate).padStart(4, '0') + '-' + suffix;
    if (isDateKey(occurrence)) return occurrence;
  }
  return day;
}

export const kindLabels: Record<Kind, string> = {
  deadline: 'Дедлайн', event: 'Событие', birthday: 'День рождения', step: 'Шаг плана',
};
export const kindMarks: Record<Kind, string> = {
  deadline: '⚑', event: '◆', birthday: '🎁', step: '○',
};
const plurals: Record<Kind, [string, string, string]> = {
  deadline: ['дедлайн', 'дедлайна', 'дедлайнов'],
  event: ['событие', 'события', 'событий'],
  birthday: ['день рождения', 'дня рождения', 'дней рождения'],
  step: ['запланированный шаг', 'запланированных шага', 'запланированных шагов'],
};
const plural = new Intl.PluralRules('ru');

export function intersects(item: CalendarItem, start: string, end = start) {
  return item.startDate <= end && item.endDate >= start;
}

export function monthSummary(items: CalendarItem[], start: string, end: string) {
  return (Object.keys(kindLabels) as Kind[]).flatMap(kind => {
    const count = items.filter(item => item.kind === kind && intersects(item, start, end)).length;
    const category = plural.select(count);
    const index = category === 'one' ? 0 : category === 'few' ? 1 : 2;
    return count ? [count + ' ' + plurals[kind][index]] : [];
  }).join(' · ');
}

export function itemKey(item: CalendarItem) {
  return item.kind + ':' + item.id + (item.occurrenceDate ? ':' + item.occurrenceDate
    : item.kind === 'birthday' ? ':' + item.startDate.slice(0, 4) : '');
}

export function dayTime(item: CalendarItem, day: string) {
  if (item.kind === 'deadline') return item.startTime ?? '';
  if (item.kind !== 'event') return '';
  if (item.startDate === day) return item.startTime ?? '';
  if (item.endDate === day) return item.endTime ?? '';
  return '';
}

export function scheduleLabel(item: CalendarItem, day: string) {
  if (item.kind === 'deadline') return item.startTime ? 'Сдать до ' + item.startTime : 'Весь день';
  if (item.kind !== 'event') return '';
  if (item.startDate === item.endDate) return item.startTime ? item.startTime + '–' + item.endTime : 'Весь день';

  const range = shortDate(item.startDate) + ' — ' + shortDate(item.endDate)
    + ' · день ' + (daysBetween(day, item.startDate) + 1) + ' из ' + (daysBetween(item.endDate, item.startDate) + 1);
  if (item.startTime && day === item.startDate) return range + ' · Начало в ' + item.startTime;
  if (item.endTime && day === item.endDate) return range + ' · Окончание в ' + item.endTime;
  return range;
}

export function formatDuration(minutes: number) {
  if (minutes <= 60) return minutes + ' мин';
  const rest = minutes % 60;
  return Math.floor(minutes / 60) + ' ч' + (rest ? ' ' + rest + ' мин' : '');
}

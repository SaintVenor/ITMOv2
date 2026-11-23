import type { CalendarItem } from '../../app/api';
import { fullDate, intersects, itemKey } from './dates';
import { lessonsOn, type Lesson } from './lessons';
import styles from './weekRibbon.module.css';

interface Props {
  days: string[];
  selected: string;
  today: string;
  items: CalendarItem[];
  lessons: Lesson[];
  ready: boolean;
  onSelect: (day: string) => void;
}

const labels = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс'];
const plural = new Intl.PluralRules('ru');
function countLabel(count: number) {
  if (!count) return 'Свободно';
  const form = plural.select(count);
  return count + (form === 'one' ? ' дело' : form === 'few' ? ' дела' : ' дел');
}
function minute(time: string) {
  const [hours, minutes] = time.split(':').map(Number);
  return hours * 60 + minutes;
}

export function WeekRibbon({days, selected, today, items, lessons, ready, onSelect}: Props) {
  return <nav className={styles.ribbon} aria-label="Дни недели">
    {days.map((day, index) => {
      const entries = items.filter(item => intersects(item, day));
      const classes = lessonsOn(lessons, day);
      const count = entries.length + classes.length;
      const caption = ready ? countLabel(count) : '—';
      const intervals = classes.map(lesson => ({
        key: 'pair:' + lesson.id, start: minute(lesson.startTime), end: minute(lesson.endTime),
      }));
      for (const item of entries) {
        if (!item.startTime) continue;
        const start = item.startDate < day ? 0 : minute(item.startTime);
        const end = item.endDate > day ? 1440 : minute(item.endTime ?? item.startTime);
        intervals.push({key: itemKey(item), start, end});
      }
      const hasUntimed = entries.some(item => !item.startTime);
      const description = fullDate(day) + (day === today ? ', сегодня' : '') + (ready ? ' · ' + caption : '');
      return <button key={day} type="button" aria-label={description} title={description}
        aria-current={day === today ? 'date' : undefined} aria-pressed={day === selected} onClick={() => onSelect(day)}>
        <span className={styles.date}><small>{labels[index]}</small><strong>{Number(day.slice(-2))}</strong></span>
        <span className={styles.caption}>{caption}</span>
        <span className={styles.rail} aria-hidden="true">
          {ready && hasUntimed && <i className={styles.untimed} />}
          {ready && intervals.map(slot => <i key={slot.key} className={styles.slot} style={{
            left: 'min(calc(100% - 3px), ' + slot.start / 14.4 + '%)', width: (slot.end - slot.start) / 14.4 + '%',
          }} />)}
        </span>
      </button>;
    })}
  </nav>;
}

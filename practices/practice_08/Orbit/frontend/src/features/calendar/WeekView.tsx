import type { CalendarItem } from '../../app/api';
import { asDate, dayTime, fullDate, intersects, itemKey, kindLabels, scheduleLabel } from './dates';
import { lessonLabel, lessonsOn, type Lesson, type LessonType } from './lessons';
import css from './week.module.css';

interface Block {
  key: string;
  title: string;
  kind: CalendarItem['kind'] | 'lesson';
  lessonType?: LessonType | null;
  detail: string;
  start: string;
  end: string;
  open: () => void;
}

interface Props {
  days: string[];
  selected: string;
  today: string;
  items: CalendarItem[];
  lessons: Lesson[];
  onSelect: (day: string) => void;
  onOpen: (item: CalendarItem) => void;
  onLesson: (lesson: Lesson) => void;
}

function hasConflict(block: Block, others: Block[]) {
  return Boolean(block.start && others.some(other => other.key !== block.key && other.start
    && ((block.start === other.start) || (block.start < other.end && other.start < block.end))));
}

export function WeekView({ days, selected, today, items, lessons, onSelect, onOpen, onLesson }: Props) {
  const visible = days.map(day => [
    ...items.filter(item => intersects(item, day)).map((item): Block => {
      const time = dayTime(item, day);
      return {
        key: itemKey(item), title: item.title, kind: item.kind, start: time,
        end: time && item.kind === 'event' && item.startDate === day
          ? (item.endDate > day ? '24:00' : item.endTime ?? time) : time,
        detail: scheduleLabel(item, day) || kindLabels[item.kind],
        open: () => { if (item.kind === 'step') onSelect(day); else onOpen(item); },
      };
    }),
    ...lessonsOn(lessons, day).map((lesson): Block => ({
      key: 'lesson:' + lesson.id, title: lesson.subject, kind: 'lesson', lessonType: lesson.lessonType,
      start: lesson.startTime, end: lesson.endTime,
      detail: lesson.startTime + '–' + lesson.endTime + ' · Ауд. ' + lesson.room,
      open: () => onLesson(lesson),
    })),
  ]);
  const times = [...new Set(visible.flat().map(block => block.start))].sort();
  const selectedIndex = days.indexOf(selected);
  const labels = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс'];

  return <section className={css.week} aria-label="Неделя">
    <div className={css.dayStrip}>
      <span aria-hidden="true" className={css.timeHead}>Время</span>
      {days.map((day, index) => <button key={day} type="button" className={css.day}
        aria-label={fullDate(day)} aria-current={day === today ? 'date' : undefined} aria-pressed={day === selected}
        onClick={() => onSelect(day)}>
        <span>{labels[index]}</span><strong>{asDate(day).getDate()}</strong>
      </button>)}
    </div>
    {!times.length && <p className={css.empty}>На этой неделе нет записей.</p>}
    {visible[selectedIndex]?.length === 0 && times.length > 0 && <p className={css.mobileEmpty}>На выбранный день нет записей.</p>}
    {times.map(time => {
      const cells = visible.map(list => list.filter(block => block.start === time));
      return <div className={css.timeBand} key={time || 'all-day'} data-empty-day={!cells[selectedIndex]?.some(block => block.kind !== 'step') || undefined}>
        <div className={css.time}>{time || 'Весь день'}</div>
        {cells.map((blocks, index) => <div className={css.cell} key={days[index]} data-current={index === selectedIndex || undefined}>
          {blocks.map(block => {
            const conflict = hasConflict(block, visible[index]);
            return <button className={css.block + (block.kind === 'lesson' ? '' : ' kind-' + block.kind)}
              data-lesson={block.kind === 'lesson' ? block.lessonType ?? 'other' : undefined} key={block.key} type="button" onClick={block.open}>
              {block.kind === 'lesson' && <span className={css.type}>{lessonLabel(block.lessonType)}</span>}
              <strong>{block.title}</strong><span>{block.detail}</span>
              {conflict && <small>Пересечение</small>}
            </button>;
          })}
        </div>)}
      </div>;
    })}
  </section>;
}

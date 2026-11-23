import { useEffect, useRef, useState, type KeyboardEvent } from 'react';
import type { CalendarItem } from '../../app/api';
import { asDate, fullDate, itemKey, kindLabels, kindMarks, moveDay } from './dates';
import { layoutWeek } from './layout';
import { lessonCount } from './lessons';
import styles from './calendar.module.css';

const weekdays = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс'];
const movements: Record<string, number> = { ArrowLeft: -1, ArrowRight: 1, ArrowUp: -7, ArrowDown: 7 };

interface Props {
  days: string[];
  month: string;
  today: string;
  selected: string;
  items: CalendarItem[];
  lessonCounts: Map<string, number>;
  onSelect: (day: string) => void;
  onOpen: (item: CalendarItem) => void;
  onAgenda: (day: string) => void;
}

export function MonthGrid({ days, month, today, selected, items, lessonCounts, onSelect, onOpen, onAgenda }: Props) {
  const [cursor, setCursor] = useState(selected);
  const dateButtons = useRef(new Map<string, HTMLButtonElement>());
  const pendingFocus = useRef<string | null>(null);

  useEffect(() => {
    setCursor(selected);
    if (pendingFocus.current === selected) {
      dateButtons.current.get(selected)?.focus();
      pendingFocus.current = null;
    }
  }, [selected]);

  function move(event: KeyboardEvent<HTMLButtonElement>, day: string) {
    const offset = movements[event.key];
    if (!offset) return;
    event.preventDefault();
    const target = moveDay(day, offset);
    const button = dateButtons.current.get(target);
    if (button) {
      setCursor(target);
      button.focus();
    } else {
      pendingFocus.current = target;
      onSelect(target);
    }
  }

  const weeks = Array.from({ length: days.length / 7 }, (_, index) => days.slice(index * 7, index * 7 + 7));
  const active = days.includes(cursor) ? cursor : selected;

  return <section className={styles.calendar} aria-label="Месяц">
    <div className={styles.weekdays} aria-hidden="true">{weekdays.map(day => <span key={day}>{day}</span>)}</div>
    {weeks.map(week => {
      const { segments, hidden } = layoutWeek(week, items);
      const lessonOverflow = week.some((day, index) => hidden[index] > 0 && (lessonCounts.get(day) ?? 0) > 0);
      return <div className={styles.week} data-lesson-overflow={lessonOverflow || undefined} key={week[0]}>
        {week.map((day, index) => <button
          key={day}
          ref={button => { if (button) dateButtons.current.set(day, button); else dateButtons.current.delete(day); }}
          type="button"
          tabIndex={day === active ? 0 : -1}
          className={styles.day}
          data-other={!day.startsWith(month) || undefined}
          style={{ gridColumn: index + 1 }}
          aria-label={fullDate(day)}
          aria-current={day === today ? 'date' : undefined}
          aria-pressed={day === selected}
          onClick={() => { setCursor(day); onSelect(day); }}
          onKeyDown={event => move(event, day)}
        ><span>{asDate(day).getDate()}</span></button>)}
        {segments.map(({ item, first, last, lane, continuesBefore, continuesAfter }) =>
          <button
            key={itemKey(item)}
            className={styles.segment + ' kind-' + item.kind}
            type="button"
            tabIndex={-1}
            data-span={item.startDate !== item.endDate || undefined}
            data-continuation-start={continuesBefore || undefined}
            data-continuation-end={continuesAfter || undefined}
            style={{ gridColumn: (first + 1) + ' / ' + (last + 2), gridRow: lane + 2 }}
            aria-label={item.title + ' · ' + kindLabels[item.kind]}
            title={item.title}
            onClick={() => item.kind === 'step' ? onAgenda(week[first]) : onOpen(item)}
          ><span className={styles.segmentLabel} aria-hidden="true">
            {continuesBefore && '‹ '}{item.done ? '✓' : kindMarks[item.kind]} {item.title}{continuesAfter && ' ›'}
          </span></button>)}
        {hidden.map((count, index) => count > 0 && <button
          key={week[index]}
          className={styles.more}
          type="button"
          tabIndex={-1}
          style={{ gridColumn: index + 1 }}
          aria-label={'Ещё ' + count + ' · ' + fullDate(week[index])}
          onClick={() => onAgenda(week[index])}
        >ещё {count}</button>)}
        {week.map((day, index) => {
          const count = lessonCounts.get(day) ?? 0;
          if (!count) return null;
          const label = lessonCount(count);
          return <button key={'lessons-' + day} className={styles.lessonCount} type="button" tabIndex={-1}
            style={{ gridColumn: index + 1 }} aria-label={label + ' · ' + fullDate(day)}
            onClick={() => onAgenda(day)}>{label}</button>;
        })}
      </div>;
    })}
  </section>;
}

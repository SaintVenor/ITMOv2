import { Button, Skeleton } from '@mantine/core';
import type { CSSProperties } from 'react';
import type { CalendarItem } from '../../app/api';
import { Link } from 'react-router-dom';
import { daysBetween, formatDuration, intersects, itemKey, kindLabels, kindMarks, longDate, scheduleLabel } from './dates';
import { lessonLabel, type Lesson, type LessonType } from './lessons';
import css from './day.module.css';

interface Props {
  day: string;
  today: string;
  now: Date;
  items: CalendarItem[];
  lessons: Lesson[];
  loading: boolean;
  failed: boolean;
  filtered: boolean;
  calendarHref: string;
  stepPending: boolean;
  onPick: () => void;
  onAdd: () => void;
  onOpen: (item: CalendarItem) => void;
  onLesson: (lesson: Lesson) => void;
  onComplete: (item: CalendarItem) => void;
}

interface Block {
  title: string;
  kind: string;
  key: string;
  start: number;
  end: number;
  item?: CalendarItem;
  room?: string;
  lessonType?: LessonType | null;
  open: () => void;
}
const entryPlural = new Intl.PluralRules('ru');
const minutes = (time: string) => Number(time.slice(0, 2)) * 60 + Number(time.slice(3));
const clock = (n: number) => [Math.floor(n / 60), n % 60].map(v => String(v).padStart(2, '0')).join(':');
const interval = (b: Block) => clock(b.start) + (b.end > b.start ? '–' + clock(b.end) : '');

function clusters(blocks: Block[]) {
  const groups: {start: number; end: number; lanes: number[]; entries: {block: Block; lane: number}[]}[] = [];
  for (const block of blocks) {
    let group = groups.at(-1);
    if (!group || (block.start >= group.end && block.start !== group.start)) {
      group = {start: block.start, end: block.end, lanes: [], entries: []};
      groups.push(group);
    }
    let lane = group.lanes.findIndex(end => end <= block.start);
    if (lane < 0) lane = group.lanes.length;
    group.lanes[lane] = Math.max(block.start + 1, block.end);
    group.end = Math.max(group.end, block.end);
    group.entries.push({block, lane});
  }
  return groups;
}

export function DayView(props: Props) {
  const {day, today, now, loading, failed, filtered, calendarHref, stepPending, onOpen, onComplete} = props;
  const blocks: Block[] = props.lessons.map(l => ({
    key: 'lesson:' + l.id, kind: lessonLabel(l.lessonType), title: l.subject, room: l.room, lessonType: l.lessonType,
    start: minutes(l.startTime), end: minutes(l.endTime), open: () => props.onLesson(l),
  }));
  const untimed: CalendarItem[] = [];
  const allDay: CalendarItem[] = [];
  for (const item of props.items.filter(i => intersects(i, day))) {
    if ((item.kind !== 'event' && item.kind !== 'deadline') || !item.startTime) {
      if (item.kind === 'event' || item.kind === 'birthday') allDay.push(item);
      else untimed.push(item);
      continue;
    }
    const start = item.startDate < day ? 0 : minutes(item.startTime);
    const end = item.kind === 'deadline' ? start : item.endDate > day ? 1440 : minutes(item.endTime ?? item.startTime);
    blocks.push({key: itemKey(item), kind: kindLabels[item.kind], title: item.title, start, end, item, open: () => onOpen(item)});
  }
  blocks.sort((a, b) => a.start - b.start || b.end - a.end || a.title.localeCompare(b.title, 'ru'));
  const time = now.getHours() * 60 + now.getMinutes();
  const current = day === today && blocks.find(b => b.start <= time && (b.end > time || b.start === time));
  const upcoming = blocks.find(b => day > today || (day === today && b.start > time));
  const focus = current || upcoming;
  const featured = allDay[0];
  const pendingCount = untimed.filter(item => !item.done).length;
  let headline = 'Свободный день';
  if (pendingCount) headline = 'Дела без времени';
  else if (blocks.length || untimed.length) headline = day === today ? 'Всё на сегодня закончилось' : 'Расписание на день завершено';
  else if (filtered) headline = 'Нет записей по выбранным фильтрам.';
  const label = current ? '● Сейчас' : upcoming ? (day === today
    ? '→ Далее · через ' + formatDuration(upcoming.start - time) : '→ Первое дело')
    : featured ? 'Весь день' : 'Обзор дня';

  let progress: {fraction: number; stamp: string; description: string} | undefined;
  let remaining = '';
  if (current && current.end > current.start) {
    const start = current.item?.startTime
      ? minutes(current.item.startTime) - daysBetween(day, current.item.startDate) * 1440 : current.start;
    const end = current.item?.endTime
      ? minutes(current.item.endTime) + daysBetween(current.item.endDate, day) * 1440 : current.end;
    const fraction = (time - start) / (end - start);
    const stamp = Math.floor(fraction * 100) + '%';
    remaining = ' · до конца ' + formatDuration(end - time);
    progress = {fraction, stamp, description: 'Прошло ' + stamp + ' события'};
  } else if (!focus && featured && featured.endDate > featured.startDate) {
    const total = daysBetween(featured.endDate, featured.startDate) + 1;
    const position = daysBetween(day, featured.startDate) + 1;
    progress = {fraction: position / total, stamp: position + '/' + total,
      description: 'День ' + position + ' из ' + total};
  }

  const groups = clusters(blocks);
  const nowLabel = <div className={css.now}>● Сейчас {clock(time)}</div>;

  return <section aria-label="Повестка" className={css.layout}>
    <div className={css.overview}>
      {loading ? <Skeleton height={200} aria-label="Загрузка расписания" /> : !failed &&
        <section className={css.hero} aria-label="Что дальше">
          <div className={css.heroTop}>
            <small>{label}{remaining}</small>
            {progress && <span className={css.orbit} role="img" aria-label={progress.description}
              style={{'--sweep': progress.fraction + 'turn'} as CSSProperties}>
              <span>{progress.stamp}</span>
            </span>}
          </div>
          <h2>{focus?.title ?? featured?.title ?? headline}</h2>
          <dl className={css.meta}>
            {focus && <div><dt>{focus.kind}</dt><dd>{interval(focus)}</dd></div>}
            {!focus && featured && <div><dt>{kindLabels[featured.kind]}</dt><dd>{scheduleLabel(featured, day) || longDate(day)}</dd></div>}
            {!focus && !featured && <div><dt>{pendingCount ? 'К выполнению' : 'Дата'}</dt><dd>{pendingCount || longDate(day)}</dd></div>}
            {focus?.room && <div><dt>Аудитория</dt><dd>{focus.room}</dd></div>}
          </dl>
        </section>}
      <section className={css.tasks} aria-label="Без времени">
        <h2>Без времени <small>{untimed.length}</small></h2>
        {untimed.map(item => <article className={css.task} key={itemKey(item)} data-done={item.done || undefined}
          id={item.kind === 'step' ? 'agenda-step-' + item.id : undefined} tabIndex={-1}>
          {item.kind === 'step'
            ? <label className={css.check}><input type="checkbox" checked={Boolean(item.done)} disabled={stepPending || item.done}
                aria-label={'Выполнить шаг «' + item.title + '»'} onChange={() => onComplete(item)} /></label>
            : <span className={css.mark} aria-hidden="true">{kindMarks[item.kind]}</span>}
          <div>
            {item.kind === 'step' ? <><strong>{item.title}</strong>
              <Link to={'/plans/' + encodeURIComponent(item.planId ?? '')} state={{calendarHref}}>{item.planTitle}</Link></>
              : <><button type="button" onClick={() => onOpen(item)}>{item.title}</button>
                <small>{[kindLabels[item.kind], scheduleLabel(item, day)].filter(Boolean).join(' · ')}</small></>}
          </div>
        </article>)}
        {!loading && !failed && !untimed.length && <p className={css.empty}>Нет записей без времени.</p>}
        <div className={css.actions}><Button onClick={props.onPick}>Выбрать шаг из планов</Button>
          <Button variant="default" onClick={props.onAdd}>Добавить запись</Button></div>
      </section>
    </div>
    <div className={css.sheet}><h2>Шкала дня <small>{longDate(day)}</small></h2>
      {allDay.length > 0 && <section aria-label="Весь день" className={css.allDay}>
        <h3>Весь день</h3>
        {allDay.map(item => <button className={'kind-' + item.kind} type="button" key={itemKey(item)} onClick={() => onOpen(item)}>
          <span>{kindMarks[item.kind]} {item.title}</span>
          <small>{scheduleLabel(item, day) || kindLabels[item.kind]}</small>
        </button>)}
      </section>}
      {!loading && !failed && !blocks.length && !allDay.length && <p className={css.state}>Нет дел с указанным временем.</p>}
      {!loading && !failed && !focus && blocks.length > 0 && pendingCount > 0 && <h3 className={css.state}>Расписание на день завершено</h3>}
      {groups.map((g, index) => {
        const prev = groups[index - 1];
        const stops = [...new Set(g.entries.flatMap(({block}) => [block.start, block.end]))].sort((a, b) => a - b);
        const overlaps = stops.flatMap((start, i) => {
          const end = stops[i + 1];
          if (end === undefined) return [];
          const active = g.entries.filter(({block}) => block.start <= start && block.end >= end);
          return active.length > 1 ? [{start, end, active}] : [];
        });
        // Keep real boundaries aligned, with enough room to select even a one-minute entry.
        const positions = new Map<number, number>();
        let height = 0;
        for (const [i, stop] of stops.entries()) {
          if (i) height += Math.max(24, Math.min(210, (stop - stops[i-1]) * 1.6));
          for (const {block} of g.entries) {
            if (block.start < stop && block.end === stop) height = Math.max(height, positions.get(block.start)! + 56);
          }
          positions.set(stop, height);
        }
        const nextStop = stops.find(stop => stop > time);
        const lastStop = stops.filter(stop => stop <= time).at(-1);
        const currentY = nextStop !== undefined && lastStop !== undefined
          ? positions.get(lastStop)! + (time-lastStop)/(nextStop-lastStop) * (positions.get(nextStop)! - positions.get(lastStop)!)
          : undefined;
        return <section key={g.start} className={css.group}>
          {prev && g.start > prev.end && <div className={css.gap}>Окно · {formatDuration(g.start - prev.end)}</div>}
          {day === today && time < g.start && (!prev || time >= prev.end) && nowLabel}

          {overlaps.length > 0 && <div className={css.clash}>
            {overlaps.map(({start, end, active}) => <div key={start}>
              <strong>△ Пересечение {clock(start)}–{clock(end)}</strong>
              <span> · {active.length} {entryPlural.select(active.length) === 'few' ? 'записи' : 'записей'}</span>
            </div>)}
          </div>}
          <div className={css.track} data-dense={g.lanes.length >= 3 || undefined}
            data-crowded={g.lanes.length >= 5 || undefined} style={{height: Math.max(height, ...g.entries.map(({block}) => positions.get(block.start)! + 56))}}>
            {stops.map(stop=>
              <time className={css.tick} data-end={stop === g.end && stop !== g.start || undefined} key={stop} style={{top:positions.get(stop)}}>{clock(stop)}</time>)}
            {day === today && currentY !== undefined &&
              <span className={css.line} style={{top:currentY}}>● Сейчас {clock(time)}</span>}
            {g.entries.map(({block, lane}) => {
              const top = positions.get(block.start)!;
              return <button className={block.item ? 'kind-' + block.item.kind : undefined} type="button" key={block.key} title={block.title + ' · ' + interval(block)}
                data-next={block === focus || undefined} data-lesson={block.room ? block.lessonType ?? 'other' : undefined}
                onClick={block.open} style={{top, height: Math.max(56, positions.get(block.end)! - top),
                  left: (lane * 100 / g.lanes.length) + '%', width: 'calc(' + (100 / g.lanes.length) + '% - 3px)'}}>
                <small>{block.kind} {block === focus && (current ? '· Сейчас' : '· Далее')}</small>
                <b>{block.title}</b><time>{interval(block)}{block.room && ' · Ауд. ' + block.room}</time>
              </button>;
            })}
          </div>

        </section>;
      })}
      {groups.length > 0 && day === today && time >= groups[groups.length-1].end && nowLabel}
    </div>
  </section>;
}

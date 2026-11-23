import { ActionIcon, Alert, Button, NativeSelect, Portal, SegmentedControl, Switch } from '@mantine/core';
import { addMonths, format, getISODay } from 'date-fns';
import { ru } from 'date-fns/locale';
import { useCallback, useEffect, useReducer, useRef, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { api, type Area, type CalendarItem, type EntryFields, type Kind } from '../../app/api';
import { Header } from '../../app/Header';
import { useDialog } from '../../app/useDialog';
import { useLoad } from '../../app/useLoad';
import { useMutation } from '../../app/useMutation';
import { planApi, type AvailableStep } from '../plans/planApi';
import { DayView } from './DayView';
import { Agenda } from './Agenda';
import { EntryDialog } from './EntryDialog';
import { MonthGrid } from './MonthGrid';
import { LessonDialog } from './LessonDialog';
import { firstLessonDate, lessonApi, lessonsOn, type Lesson } from './lessons';
import { WeekRibbon } from './WeekRibbon';
import { WeekView } from './WeekView';
import { StepPicker } from './StepPicker';
import { asDate, birthdayInViewYear, dateKey, daysBetween, isDateKey, kindLabels, longDate, monthDays, monthKey, monthSummary, moveDay, shortDate } from './dates';
import styles from './calendar.module.css';

interface LoadedCalendar {
  range: string;
  items: CalendarItem[];
}

function useCalendar(from: string, to: string) {
  const range = from + '/' + to;
  const [revision, refresh] = useReducer(value => value + 1, 0);
  const requestKey = range + '/' + revision;
  const [data, setData] = useState<LoadedCalendar>();
  const [completed, setCompleted] = useState<{ key: string; failed: boolean }>();

  useEffect(() => {
    const controller = new AbortController();
    api.calendar(from, to, controller.signal).then(response => {
      if (controller.signal.aborted) return;
      setData({ range, items: response.items });
      setCompleted({ key: requestKey, failed: false });
    }).catch(() => {
      if (!controller.signal.aborted) setCompleted({ key: requestKey, failed: true });
    });
    return () => controller.abort();
  }, [from, to, range, requestKey]);

  return {
    items: data?.range === range ? data.items : [],
    loading: completed?.key !== requestKey,
    failed: completed?.key === requestKey && completed.failed,
    refresh,
  };
}

export function CalendarPage() {
  const [query, setQuery] = useSearchParams();
  const [now, setNow] = useState(() => new Date());
  useEffect(() => {
    const timer = window.setInterval(() => setNow(new Date()), 1000 * 15);
    return () => window.clearInterval(timer);
  }, []);
  const today = dateKey(now);
  const requestedDate = query.get('date');
  const requestedMonth = query.get('month');
  const monthDate = requestedMonth ? requestedMonth + '-01' : null;
  const selected = isDateKey(requestedDate) ? requestedDate : today;
  const defaultMonth = asDate(selected);
  const candidate = isDateKey(monthDate) ? monthDays(asDate(monthDate)) : null;
  const month = candidate?.days.includes(selected) && monthDate ? asDate(monthDate) : defaultMonth;
  const range = monthDays(month);
  const monthId = monthKey(month);
  const daily = query.get('view') === 'day' || (!query.has('view') && !requestedDate && !requestedMonth);
  const [filtersOpen, setFiltersOpen] = useState(false);
  const weekly = query.get('view') === 'week';
  const monday = moveDay(selected, 1 - getISODay(asDate(selected)));
  const week = Array.from({ length: 7 }, (_, index) => moveDay(monday, index));
  const weekTitle = week[0].slice(0, 7) === week[6].slice(0, 7)
    ? asDate(week[0]).getDate() + '–' + longDate(week[6])
    : shortDate(week[0]) + ' — ' + shortDate(week[6]);
  const weekYear = week[0].slice(0, 4) === week[6].slice(0, 4)
    ? week[0].slice(0, 4) : week[0].slice(0, 4) + '/' + week[6].slice(0, 4);
  const { items, loading, failed, refresh } = useCalendar(range.from, range.to);
  const [area, setArea] = useState<Area | ''>('');
  const [kind, setKind] = useState<Kind | ''>('');
  const [dialog, setDialog] = useState<{ item?: CalendarItem } | null>(null);
  const [notice, setNotice] = useState<{ message: string } | null>(null);
  useEffect(() => {
    if (!notice) return;
    const timer = window.setTimeout(() => setNotice(null), 4000);
    return () => window.clearTimeout(timer);
  }, [notice]);

  function notify(message: string) {
    setNotice({ message });
  }
  const dialogTrigger = useRef<HTMLElement | null>(null);
  const picker = useDialog<true>();
  const [showLessons, setShowLessons] = useState(false);
  const lessonDialog = useDialog<Lesson | 'new'>();
  const { from, to } = range;
  const loadLessons = useCallback((signal: AbortSignal) => lessonApi.list(from, to, signal), [from, to]);
  const { data: lessonData, loading: lessonsLoading, failed: lessonsFailed, refresh: refreshLessons } = useLoad(loadLessons, showLessons);
  const lessons = lessonData?.items ?? [];
  const dayLessons = lessonsOn(lessons, selected);
  const lessonCounts = new Map(range.days.map(day => [day, lessonsOn(lessons, day).length]));
  const stepAction = useMutation();
  const filtered = Boolean(area || kind);
  const visible = items.filter(item => (!area || item.area === area) && (!kind || item.kind === kind));
  const summary = monthSummary(visible, weekly ? week[0] : range.first, weekly ? week[6] : range.last);

  function go(day: string, view = day.slice(0, 7)) {
    const next = new URLSearchParams({ date: day });
    if (!day.startsWith(view)) next.set('month', view);
    if (daily) next.set('view', 'day');
    else if (weekly) next.set('view', 'week');
    setQuery(next);
    setNotice(null);
    stepAction.clearError();
  }

  function select(day: string) {
    go(day, range.days.includes(day) ? monthId : undefined);
  }

  function openAgenda(day: string) {
    select(day);
    document.getElementById('agenda-date')?.focus();
  }

  function shift(offset: number) {
    if (daily) go(moveDay(selected, offset));
    else if (weekly) go(moveDay(selected, offset * 7));
    else go(monthKey(addMonths(month, offset)) + '-01');
  }

  function clearFilters() {
    setArea('');
    setKind('');
  }

  function closeDialog() {
    const trigger = dialogTrigger.current;
    setDialog(null);
    requestAnimationFrame(() => {
      if (trigger?.isConnected) trigger.focus();
      else document.getElementById('agenda-date')?.focus();
    });
  }

  function saved(record: EntryFields) {
    closeDialog();
    if (record.kind === 'birthday' && record.birthMonth && record.birthDay) {
      select(birthdayInViewYear(selected, record.birthMonth, record.birthDay));
    } else if ((!record.frequency || !dialog?.item?.occurrenceDate) && record.startDate && record.endDate && (selected < record.startDate || selected > record.endDate)) {
      select(record.startDate);
    }
    if ((area && area !== record.area) || (kind && kind !== record.kind)) clearFilters();
    notify('Запись сохранена.');
    refresh();
  }

  function open(item?: CalendarItem) {
    dialogTrigger.current = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    setDialog({ item });
  }

  const pendingStepFocus = useRef<{day: string; id: string} | null>(null);
  useEffect(() => {
    const target = pendingStepFocus.current;
    if (!target) return;
    if (target.day !== selected || !daily || failed) {
      pendingStepFocus.current = null;
      return;
    }
    if (loading) return;
    const entry = document.getElementById('agenda-step-' + target.id);
    if (entry) {
      entry.focus();
      pendingStepFocus.current = null;
    }
  }, [daily, selected, loading, failed, items]);

  function assigned(step: AvailableStep) {
    picker.close();
    if ((area && area !== step.area) || (kind && kind !== 'step')) clearFilters();
    if (daily) pendingStepFocus.current = {day: selected, id: step.id};
    notify('Шаг «' + step.title + '» назначен на ' + longDate(selected) + '.');
    refresh();
  }

  function complete(item: CalendarItem) {
    void stepAction.submit(() => planApi.editStep(item.id, { done: true }), () => {
      notify('Шаг выполнен.');
      refresh();
      requestAnimationFrame(() => document.getElementById('agenda-date')?.focus());
    });
  }

  function savedLesson(lesson: Lesson) {
    lessonDialog.close();
    if (!lessonsOn([lesson], selected).length) {
      const first = firstLessonDate(lesson);
      const interval = 7 * (lesson.weekInterval ?? 1);
      const steps = Math.max(0, Math.ceil(daysBetween(range.first, first) / interval));
      const next = moveDay(first, steps * interval);
      select(next <= lesson.termEnd ? next : first);
    }
    notify('Пара сохранена.');
    refreshLessons();
  }

  const add = () => open();
  const calendarHref = '/calendar' + (query.size ? '?' + query.toString() : '');

  return <>
    <Header onAdd={daily ? undefined : add} />
    <main className="shell content">
      <div className={styles.heading}>
        <div className={styles.controls}>
          <ActionIcon variant="default" size="lg" aria-label={daily ? 'Предыдущий день' : weekly ? 'Предыдущая неделя' : 'Предыдущий месяц'} onClick={() => shift(-1)}>‹</ActionIcon>
          <ActionIcon variant="default" size="lg" aria-label={daily ? 'Следующий день' : weekly ? 'Следующая неделя' : 'Следующий месяц'} onClick={() => shift(1)}>›</ActionIcon>
          <Button variant="default" onClick={() => go(today)}>Сегодня</Button>
        </div>
        <div className={styles.calendarTitle} data-week-title={weekly || undefined}>
          {daily ? <h1 id="agenda-date" className={styles.dayTitle} tabIndex={-1}>{selected === today ? 'Сегодня' : longDate(selected)}</h1> : <h1>{weekly ? weekTitle : format(month, 'LLLL', { locale: ru })} <span>{weekly ? weekYear : format(month, 'yyyy')}</span></h1>}
          <p className={styles.summary} aria-live="polite">{daily ? format(asDate(selected), 'EEEE, d MMMM yyyy', {locale: ru}) : summary || (loading
            ? 'Загрузка записей…' : failed ? '' : filtered ? 'Нет записей по выбранным фильтрам.'
              : weekly ? 'На этой неделе пока нет записей.' : 'В этом месяце пока нет записей.')}</p>
        </div>
        <SegmentedControl aria-label="Вид календаря" value={daily ? 'day' : weekly ? 'week' : 'month'}
          data={[{ value: 'day', label: 'День' }, { value: 'week', label: 'Неделя' }, { value: 'month', label: 'Месяц' }]}
          onChange={value => {
            const next = new URLSearchParams(query);
            next.set('view', value);
            next.set('date', selected);
            setQuery(next);
          }} />
      </div>
      {daily && <WeekRibbon days={week} selected={selected} today={today} items={visible} lessons={lessons}
        ready={!loading && !failed && !lessonsLoading && !lessonsFailed} onSelect={select} />}
      <div className={styles.filters}>
        <Button className={styles.filterToggle} variant="default" aria-expanded={filtersOpen}
          onClick={() => setFiltersOpen(!filtersOpen)}>Фильтры{filtered && ' (' + (Number(Boolean(area)) + Number(Boolean(kind))) + ')'}</Button>
        <div className={styles.filterFields} data-open={filtersOpen || undefined}>
        <NativeSelect aria-label="Сфера" value={area}
          data={[{ value: '', label: 'Все сферы' }, { value: 'study', label: 'Учёба' }, { value: 'personal', label: 'Личное' }]}
          onChange={event => setArea(event.currentTarget.value as Area | '')} />
        <NativeSelect aria-label="Тип" value={kind}
          data={[{ value: '', label: 'Все типы' }, ...Object.entries(kindLabels).map(([value, label]) => ({ value, label }))]}
          onChange={event => setKind(event.currentTarget.value as Kind | '')} />
        {filtered && <Button variant="subtle" onClick={clearFilters}>Сбросить фильтры</Button>}
        </div>
        <div className={styles.scheduleControls}>
          <Switch label="Учебные пары" checked={showLessons} onChange={event => setShowLessons(event.currentTarget.checked)} />
          <div className={styles.lessonAction}>
            {showLessons && <Button variant="default" size="compact-md" onClick={() => lessonDialog.open('new')}>Добавить пару</Button>}
          </div>
        </div>
      </div>
      {lessonsFailed && <Alert color="red" role="alert" className={styles.alert}>
        Не удалось загрузить учебное расписание. <Button variant="subtle" size="compact-sm" onClick={refreshLessons}>Повторить</Button>
      </Alert>}
      {notice && <Portal>
        <div className={styles.toast} role="status">{notice.message}</div>
      </Portal>}
      {stepAction.error && <Alert color="red" role="alert" className={styles.alert}>{stepAction.error.message}</Alert>}
      {failed && <Alert color="red" role="alert" className={styles.alert}>
        Не удалось загрузить календарь. <Button variant="subtle" size="compact-sm" onClick={refresh}>Повторить</Button>
      </Alert>}
      {daily ? <DayView day={selected} today={today} now={now} items={visible} lessons={dayLessons}
        loading={loading || lessonsLoading} failed={failed || lessonsFailed} filtered={filtered}
        calendarHref={calendarHref} stepPending={stepAction.busy} onPick={() => picker.open(true)}
        onAdd={add} onOpen={open} onLesson={lesson => lessonDialog.open(lesson)} onComplete={complete} />
        : <div className={styles.layout} data-week={weekly || undefined}>
        {weekly ? <WeekView days={week} selected={selected} today={today} items={visible} lessons={lessons}
          onSelect={select} onOpen={open} onLesson={lesson => lessonDialog.open(lesson)} />
          : <MonthGrid days={range.days} month={monthId} today={today} selected={selected}
            items={visible} lessonCounts={lessonCounts} onSelect={select} onAgenda={openAgenda} onOpen={open} />}
        <Agenda day={selected} items={visible} loading={loading && !items.length} failed={failed} filtered={filtered}
          calendarHref={calendarHref} onAdd={add} onOpen={open} onPick={() => picker.open(true)}
          onComplete={complete} stepPending={stepAction.busy}
          lessons={dayLessons} lessonsLoading={lessonsLoading} onLessonOpen={lesson => lessonDialog.open(lesson)} />
      </div>}
    </main>
    {lessonDialog.value && <LessonDialog day={selected} lesson={lessonDialog.value === 'new' ? undefined : lessonDialog.value}
      onClose={lessonDialog.close} onSaved={savedLesson} onRemoved={() => {
        lessonDialog.close();
        notify('Пара удалена.');
        refreshLessons();
        requestAnimationFrame(() => document.getElementById('agenda-date')?.focus());
      }} />}
    {picker.value && <StepPicker day={selected} calendarHref={calendarHref} onClose={picker.close} onAssigned={assigned} />}
    {dialog && <EntryDialog day={selected} item={dialog.item} onClose={closeDialog}
      onSaved={saved} onDeleted={() => {
        dialogTrigger.current = document.getElementById('agenda-date');
        closeDialog();
        notify('Запись удалена.');
        refresh();
      }} />}
  </>;
}

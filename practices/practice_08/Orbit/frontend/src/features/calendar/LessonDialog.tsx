import { Alert, Button, Modal, NativeSelect, TextInput } from '@mantine/core';
import { getISODay } from 'date-fns';
import { useState, type FormEvent } from 'react';
import { useMutation, useOperationId } from '../../app/useMutation';
import { asDate, daysBetween, isDateKey } from './dates';
import { lessonApi, lessonTypes, weekdays, type Lesson, type LessonFields, type LessonType } from './lessons';
import styles from './calendar.module.css';

interface Props {
  day: string;
  lesson?: Lesson;
  onClose: () => void;
  onSaved: (lesson: Lesson) => void;
  onRemoved: () => void;
}

function initialFields(day: string, lesson?: Lesson): LessonFields {
  if (lesson) {
    const { id: _id, ...fields } = lesson;
    return fields;
  }
  return {
    weekday: getISODay(asDate(day)), subject: '', room: '', startTime: '', endTime: '',
    termStart: day, termEnd: day, weekInterval: 1, firstDate: null,
  };
}

function validate(fields: LessonFields) {
  const errors: Partial<Record<keyof LessonFields, string>> = {};
  if (!fields.subject.trim()) errors.subject = 'Введите название предмета.';
  if (!fields.room.trim()) errors.room = 'Введите аудиторию.';
  if (!fields.startTime) errors.startTime = 'Укажите время начала.';
  if (!fields.endTime) errors.endTime = 'Укажите время окончания.';
  else if (fields.startTime && fields.endTime <= fields.startTime) errors.endTime = 'Окончание пары должно быть позже начала.';
  if (!isDateKey(fields.termStart)) errors.termStart = 'Укажите начало семестра.';
  if (!isDateKey(fields.termEnd)) errors.termEnd = 'Укажите конец семестра.';
  else if (!errors.termStart) {
    const length = daysBetween(fields.termEnd, fields.termStart);
    const offset = (fields.weekday - getISODay(asDate(fields.termStart)) + 7) % 7;
    if (length < 0) errors.termEnd = 'Конец семестра раньше начала.';
    else if (offset > length) errors.termEnd = 'В этом периоде нет выбранного дня недели.';
  }
  if (fields.firstDate && (!isDateKey(fields.firstDate) || fields.firstDate < fields.termStart
    || fields.firstDate > fields.termEnd || getISODay(asDate(fields.firstDate)) !== fields.weekday)) {
    errors.firstDate = 'Первая пара должна быть в семестре и выпадать на выбранный день недели.';
  }
  return errors;
}

export function LessonDialog({ day, lesson, onClose, onSaved, onRemoved }: Props) {
  const [draft, setDraft] = useState(() => initialFields(day, lesson));
  const [errors, setErrors] = useState<ReturnType<typeof validate>>({});
  const [confirm, setConfirm] = useState(false);
  // A one-day semester represents exactly one occurrence in the existing API.
  const [once, setOnce] = useState(Boolean(lesson && lesson.termStart === lesson.termEnd));
  const [singleDate, setSingleDate] = useState(lesson?.termStart ?? day);
  const [semester, setSemester] = useState('manual');
  const { submit, busy, error, isLocked, clearError } = useMutation();
  const operationId = useOperationId();

  function change<Key extends keyof LessonFields>(key: Key, value: LessonFields[Key]) {
    setDraft(previous => ({ ...previous, [key]: value }));
    setErrors(previous => ({ ...previous, [key]: undefined }));
    clearError();
  }

  function chooseSemester(value: string) {
    setSemester(value);
    if (value === 'manual') return;
    const year = day.slice(0, 4);
    const autumn = value === 'autumn';
    setDraft(old => ({ ...old, termStart: year + (autumn ? '-09-01' : '-02-01'),
      termEnd: year + (autumn ? '-12-31' : '-05-31'), firstDate: null }));
    setErrors({});
    clearError();
  }

  function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (isLocked()) return;
    if (once && !isDateKey(singleDate)) {
      setErrors({ termStart: 'Укажите дату пары.' });
      const input = event.currentTarget.elements.namedItem('termStart');
      if (input instanceof HTMLElement) input.focus();
      return;
    }
    const schedule: LessonFields = once ? { ...draft, weekday: getISODay(asDate(singleDate)),
      termStart: singleDate, termEnd: singleDate, weekInterval: 1, firstDate: null } : draft;
    const issues = validate(schedule);
    setErrors(issues);
    const first = Object.keys(issues)[0];
    if (first) {
      const control = event.currentTarget.elements.namedItem(first);
      if (control instanceof HTMLElement) control.focus();
      return;
    }

    const fields = { ...schedule, subject: draft.subject.trim(), room: draft.room.trim() };
    void submit(() => lesson
      ? lessonApi.edit(lesson.id, fields)
      : lessonApi.create(operationId(fields), fields), onSaved);
  }

  const fieldError = (name: keyof LessonFields) => errors[name] || error?.fields[name];
  const title = confirm ? 'Удалить пару?' : lesson ? 'Редактировать пару' : 'Добавить пару';

  return <Modal opened centered radius="lg" title={title} closeButtonProps={{ 'aria-label': 'Закрыть' }}
    closeOnClickOutside={!busy} closeOnEscape={!busy} withCloseButton={!busy}
    styles={{ content: { background: 'var(--surface)' }, header: { background: 'var(--surface)' }, title: { fontSize: 22 } }}
    onClose={() => { if (!isLocked()) onClose(); }}>
    {error && <Alert className={styles.alert} color="red" role="alert">{error.message}</Alert>}
    {confirm && lesson ? <>
      <p>Из расписания исчезнут все занятия по записи «{lesson.subject}».</p>
      <div className={styles.formActions}>
        <Button variant="default" disabled={busy} onClick={() => { clearError(); setConfirm(false); }}>Назад</Button>
        <Button color="red" loading={busy} onClick={() => void submit(() => lessonApi.remove(lesson.id), onRemoved)}>Удалить пару</Button>
      </div>
    </> : <form className={styles.form} onSubmit={save} noValidate aria-busy={busy}>
      <TextInput name="subject" label="Предмет" value={draft.subject} readOnly={busy} data-autofocus
        required maxLength={120} error={fieldError('subject')} onChange={event => change('subject', event.currentTarget.value)} />
      <TextInput name="room" label="Аудитория" value={draft.room} readOnly={busy}
        required maxLength={80} error={fieldError('room')} onChange={event => change('room', event.currentTarget.value)} />
      <NativeSelect name="lessonType" label="Тип пары" value={draft.lessonType ?? ''} disabled={busy}
        data={[{ value: '', label: 'Без типа' }, ...Object.entries(lessonTypes).map(([value, label]) => ({ value, label }))]}
        error={fieldError('lessonType')} onChange={event => change('lessonType', (event.currentTarget.value || null) as LessonType | null)} />
      {!once && <NativeSelect name="weekday" label="День недели" value={String(draft.weekday)} disabled={busy}
        data={weekdays.map((label, index) => ({ value: String(index + 1), label }))}
        error={fieldError('weekday')} onChange={event => change('weekday', Number(event.currentTarget.value))} />}
      <div className={styles.pair}>
        <TextInput name="startTime" label="Начало пары" type="time" value={draft.startTime} readOnly={busy}
          required withAsterisk={false} error={fieldError('startTime')} onChange={event => change('startTime', event.currentTarget.value)} />
        <TextInput name="endTime" label="Конец пары" type="time" value={draft.endTime} readOnly={busy}
          required withAsterisk={false} error={fieldError('endTime')} onChange={event => change('endTime', event.currentTarget.value)} />
      </div>
      <div className={styles.pair}>
        <NativeSelect name="weekInterval" label="Повторение пары" value={once ? 'once' : String(draft.weekInterval ?? 1)} disabled={busy}
          data={[{ value: 'once', label: 'Однократно' }, { value: '1', label: 'Каждую неделю' }, { value: '2', label: 'Раз в две недели' }]}
          onChange={event => {
            const value = event.currentTarget.value;
            setOnce(value === 'once');
            change('weekInterval', value === '2' ? 2 : 1);
            setErrors({});
          }} />
        {!once && <NativeSelect label="Семестр" value={semester} disabled={busy}
          data={[{ value: 'manual', label: 'Свои даты' }, { value: 'autumn', label: 'Осенний' }, { value: 'spring', label: 'Весенний' }]}
          onChange={event => chooseSemester(event.currentTarget.value)} />}
      </div>
      {once ? <TextInput name="termStart" label="Дата пары" type="date" value={singleDate} readOnly={busy}
        error={fieldError('termStart')} onChange={event => {
          setSingleDate(event.currentTarget.value);
          setErrors({});
          clearError();
        }} /> : <div className={styles.pair}>
        <TextInput name="termStart" label="Начало семестра" type="date" value={draft.termStart} readOnly={busy}
          required withAsterisk={false} error={fieldError('termStart')} onChange={event => { setSemester('manual'); change('termStart', event.currentTarget.value); }} />
        <TextInput name="termEnd" label="Конец семестра" type="date" value={draft.termEnd} readOnly={busy}
          required withAsterisk={false} error={fieldError('termEnd')} onChange={event => { setSemester('manual'); change('termEnd', event.currentTarget.value); }} />
      </div>}
      {!once && (draft.weekInterval === 2 || draft.firstDate) && <TextInput name="firstDate" label="Дата первой пары" type="date"
        description="Задаёт, с какой недели начнутся повторы. Можно оставить пустой."
        value={draft.firstDate ?? ''} readOnly={busy} error={fieldError('firstDate')}
        onChange={event => change('firstDate', event.currentTarget.value || null)} />}
      <div className={styles.formActions}>
        {lesson && <Button variant="subtle" color="red" disabled={busy}
          onClick={() => { clearError(); setConfirm(true); }}>Удалить</Button>}
        <Button type="submit" loading={busy}>{busy ? 'Сохраняем…' : 'Сохранить'}</Button>
      </div>
    </form>}
  </Modal>;
}

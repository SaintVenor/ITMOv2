import { Alert, Button, Checkbox, Modal, NativeSelect, TextInput } from '@mantine/core';
import { useRef, useState, type FormEvent } from 'react';
import { api, ApiError, type Area, type CalendarItem, type DeletionScope, type EntryFields, type EntryKind, type Frequency } from '../../app/api';
import { asDate, isDateKey, kindLabels } from './dates';
import styles from './calendar.module.css';

interface Draft {
  kind: EntryKind;
  title: string;
  area: Area;
  startDate: string;
  endDate: string;
  startTime: string;
  endTime: string;
  allDay: boolean;
  birthMonth: string;
  birthDay: string;
  frequency: Frequency | '';
}

function initialDraft(day: string, item?: CalendarItem): Draft {
  const start = item?.seriesStart ?? item?.startDate ?? day;
  const date = asDate(start);
  return {
    kind: item?.kind as EntryKind ?? 'event',
    title: item?.title ?? '',
    area: item?.area ?? 'personal',
    startDate: start,
    endDate: item?.seriesEnd ?? item?.endDate ?? start,
    startTime: item?.startTime ?? '',
    endTime: item?.endTime ?? '',
    allDay: !item?.startTime,
    birthMonth: String(date.getMonth() + 1),
    birthDay: String(date.getDate()),
    frequency: item?.frequency ?? '',
  };
}

function validate(draft: Draft) {
  const errors: Record<string, string> = {};
  if (!draft.title.trim()) errors.title = 'Введите название.';

  if (draft.kind === 'birthday') {
    const month = Number(draft.birthMonth);
    const day = Number(draft.birthDay);
    const check = new Date(2000, month - 1, day);
    if (!Number.isInteger(day) || day < 1 || check.getMonth() !== month - 1) {
      errors.birthDay = 'Укажите существующий день месяца.';
    }
    return errors;
  }

  if (!isDateKey(draft.startDate)) errors.startDate = 'Укажите дату.';
  if (draft.kind === 'event') {
    if (!isDateKey(draft.endDate)) errors.endDate = 'Укажите дату окончания.';
    else if (draft.endDate < draft.startDate) errors.endDate = 'Окончание раньше начала.';
    if (!draft.allDay) {
      if (!draft.startTime) errors.startTime = 'Укажите время начала.';
      if (!draft.endTime) errors.endTime = 'Укажите время окончания.';
      else if (draft.startTime && draft.startDate === draft.endDate && draft.endTime <= draft.startTime) {
        errors.endTime = 'Время окончания должно быть позже начала.';
      }
    }
  }
  return errors;
}

function entryFields(draft: Draft): EntryFields {
  const birthday = draft.kind === 'birthday';
  const event = draft.kind === 'event';
  return {
    kind: draft.kind,
    title: draft.title.trim(),
    area: draft.area,
    startDate: birthday ? null : draft.startDate,
    endDate: birthday ? null : event ? draft.endDate : draft.startDate,
    startTime: birthday || (event && draft.allDay) ? null : draft.startTime || null,
    endTime: event && !draft.allDay ? draft.endTime : null,
    birthMonth: birthday ? Number(draft.birthMonth) : null,
    birthDay: birthday ? Number(draft.birthDay) : null,
    frequency: birthday ? null : draft.frequency || null,
  };
}

interface Props {
  day: string;
  item?: CalendarItem;
  onClose: () => void;
  onSaved: (record: EntryFields) => void;
  onDeleted: () => void;
}

export function EntryDialog({ day, item, onClose, onSaved, onDeleted }: Props) {
  const [draft, setDraft] = useState(() => initialDraft(day, item));
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [failure, setFailure] = useState('');
  const [pending, setPending] = useState(false);
  const [confirm, setConfirm] = useState(false);
  const [scope, setScope] = useState<DeletionScope>('one');
  const editedEnd = useRef(Boolean(item && item.startDate !== item.endDate));
  const locked = useRef(false);
  const formElement = useRef<HTMLFormElement>(null);
  const operation = useRef<{ id: string; payload: string } | undefined>(undefined);

  function change<Key extends keyof Draft>(field: Key, value: Draft[Key]) {
    setDraft(previous => ({
      ...previous,
      ...(field === 'startDate' && typeof value === 'string' && !editedEnd.current ? { endDate: value } : {}),
      [field]: value,
    }));
    setErrors(previous => ({ ...previous, [field]: '' }));
  }

  function focusError(fieldErrors: Record<string, string>) {
    for (const control of Array.from(formElement.current?.elements ?? [])) {
      if (control instanceof HTMLElement && fieldErrors[control.getAttribute('name') ?? '']) {
        control.focus();
        break;
      }
    }
  }

  function showFailure(error: unknown) {
    if (error instanceof ApiError && Object.keys(error.fields).length > 0) {
      setErrors(error.fields);
      focusError(error.fields);
      setFailure('Проверьте выделенные поля.');
    } else {
      setFailure(error instanceof ApiError ? error.message : 'Не удалось связаться с сервером. Повторите попытку.');
    }
  }

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (locked.current || confirm) return;
    setFailure('');
    const nextErrors = validate(draft);
    setErrors(nextErrors);
    if (Object.keys(nextErrors).length) {
      focusError(nextErrors);
      return;
    }

    locked.current = true;
    setPending(true);
    try {
      const fields = entryFields(draft);
      let saved: EntryFields;
      if (item) {
        saved = await api.editEntry(item.id, fields);
      } else {
        const payload = JSON.stringify(fields);
        if (operation.current?.payload !== payload) operation.current = { id: crypto.randomUUID(), payload };
        saved = await api.createEntry(operation.current.id, fields);
      }
      onSaved(saved);
    } catch (error) {
      showFailure(error);
    } finally {
      locked.current = false;
      setPending(false);
    }
  }

  async function remove() {
    if (!item || locked.current) return;
    locked.current = true;
    setPending(true);
    setFailure('');
    try {
      await api.deleteEntry(item.id, item.occurrenceDate ? scope : 'all', item.occurrenceDate);
      onDeleted();
    } catch (error) {
      showFailure(error);
    } finally {
      locked.current = false;
      setPending(false);
    }
  }

  return <Modal
    opened
    centered
    radius="lg"
    styles={{ content: { background: 'var(--surface)' }, header: { background: 'var(--surface)' }, title: { fontSize: 22 } }}
    title={confirm ? 'Удалить запись?' : item ? 'Редактировать запись' : 'Добавить запись'}
    closeButtonProps={{ 'aria-label': 'Закрыть' }}
    closeOnClickOutside={!pending}
    closeOnEscape={!pending}
    withCloseButton={!pending}
    onClose={() => { if (!locked.current) onClose(); }}
  >
    {failure && <Alert color="red" role="alert" className={styles.alert}>{failure}</Alert>}
    {confirm ? <>
      {item?.occurrenceDate ? <NativeSelect label="Что удалить" value={scope} disabled={pending}
        data={[
          { value: 'one', label: 'Только это повторение' }, { value: 'before', label: 'Это и все предыдущие' },
          { value: 'after', label: 'Это и все следующие' }, { value: 'all', label: 'Всю серию' },
        ]} onChange={event => setScope(event.currentTarget.value as DeletionScope)} />
        : <p>{item?.kind === 'event' && item.startDate !== item.endDate
          ? 'Будет удалено всё событие «' + item.title + '» со всех дней диапазона.'
          : 'Запись «' + item?.title + '» будет удалена.'}</p>}
      <div className={styles.formActions}>
        <Button variant="default" disabled={pending} onClick={() => { setConfirm(false); setFailure(''); }}>Назад</Button>
        <Button color="red" loading={pending} onClick={remove}>Удалить запись</Button>
      </div>
    </> : <form ref={formElement} className={styles.form} onSubmit={save} noValidate aria-busy={pending}>
      <NativeSelect label="Тип записи" name="kind" value={draft.kind}
        data={(['event', 'deadline', 'birthday'] as const).map(value => ({ value, label: kindLabels[value] }))}
        disabled={pending} onChange={event => change('kind', event.currentTarget.value as EntryKind)} />
      <TextInput label={draft.kind === 'birthday' ? 'Имя' : 'Название'} name="title" required data-autofocus
        maxLength={180} value={draft.title} readOnly={pending} error={errors.title}
        onChange={event => change('title', event.currentTarget.value)} />
      <NativeSelect label="Сфера" name="area" value={draft.area}
        data={[{ value: 'personal', label: 'Личное' }, { value: 'study', label: 'Учёба' }]}
        disabled={pending} onChange={event => change('area', event.currentTarget.value as Area)} />
      {draft.kind === 'birthday' ? <p className={styles.repeatHint}>День рождения повторяется каждый год.</p>
        : <NativeSelect label="Повторение" value={draft.frequency} disabled={pending}
          data={[
            { value: '', label: 'Без повторения' }, { value: 'daily', label: 'Каждый день' },
            { value: 'weekly', label: 'Каждую неделю' }, { value: 'monthly', label: 'Каждый месяц' },
            { value: 'yearly', label: 'Каждый год' },
          ]} onChange={event => change('frequency', event.currentTarget.value as Frequency | '')} />}
      {item?.occurrenceDate && <p className={styles.repeatHint}>Изменения формы применяются ко всей серии.</p>}
      {draft.kind === 'birthday' ? <div className={styles.pair}>
        <TextInput label="День" type="number" name="birthDay" required min={1} max={31}
          value={draft.birthDay} readOnly={pending} error={errors.birthDay}
          onChange={event => change('birthDay', event.currentTarget.value)} />
        <NativeSelect label="Месяц" name="birthMonth" required value={draft.birthMonth}
          data={Array.from({ length: 12 }, (_, index) => ({
            value: String(index + 1),
            label: new Intl.DateTimeFormat('ru', { month: 'long' }).format(new Date(2000, index, 1)),
          }))}
          disabled={pending} error={errors.birthMonth}
          onChange={event => change('birthMonth', event.currentTarget.value)} />
      </div> : <div className={styles.pair}>
        <TextInput label={draft.kind === 'deadline' ? 'Дата сдачи' : 'Начало'} type="date" name="startDate" required withAsterisk={false}
          value={draft.startDate} readOnly={pending} error={errors.startDate}
          onChange={event => change('startDate', event.currentTarget.value)} />
        {draft.kind === 'event' && <TextInput label="Окончание" type="date" name="endDate" required withAsterisk={false}
          value={draft.endDate} readOnly={pending} error={errors.endDate}
          onChange={event => { editedEnd.current = true; change('endDate', event.currentTarget.value); }} />}
        {draft.kind === 'deadline' && <TextInput label="Время сдачи" type="time" name="startTime"
          value={draft.startTime} readOnly={pending} error={errors.startTime}
          onChange={event => change('startTime', event.currentTarget.value)} />}
      </div>}
      {draft.kind === 'event' && <>
        <Checkbox label="Весь день" checked={draft.allDay} disabled={pending}
          onChange={event => change('allDay', event.currentTarget.checked)} />
        {!draft.allDay && <div className={styles.pair}>
          <TextInput label="Время начала" type="time" name="startTime" required
            value={draft.startTime} readOnly={pending} error={errors.startTime}
            onChange={event => change('startTime', event.currentTarget.value)} />
          <TextInput label="Время окончания" type="time" name="endTime" required
            value={draft.endTime} readOnly={pending} error={errors.endTime}
            onChange={event => change('endTime', event.currentTarget.value)} />
        </div>}
      </>}
      <div className={styles.formActions}>
        {item && <Button variant="subtle" color="red" disabled={pending} onClick={() => { setConfirm(true); setFailure(''); }}>Удалить</Button>}
        <Button type="submit" loading={pending}>{pending ? 'Сохраняем…' : 'Сохранить'}</Button>
      </div>
    </form>}
  </Modal>;
}

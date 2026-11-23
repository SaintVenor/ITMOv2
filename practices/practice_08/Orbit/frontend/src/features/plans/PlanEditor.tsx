import { Alert, Button, FileInput, Modal, NativeSelect, Textarea, TextInput } from '@mantine/core';
import { useState, type FormEvent } from 'react';
import type { Area } from '../../app/api';
import { useMutation, useOperationId } from '../../app/useMutation';
import { isDateKey } from '../calendar/dates';
import { planApi, type PlanDetail, type Resource, type Step } from './planApi';
import { covers, PlanCover } from './PlanCover';
import styles from './plans.module.css';

type Mode =
  | { kind: 'plan'; plan?: PlanDetail; saved: (plan: PlanDetail) => void }
  | { kind: 'step'; planId: string; step?: Step; saved: (step: Step) => void }
  | { kind: 'resource'; planId: string; saved: (resource: Resource) => void };

function isWebUrl(value: string) {
  try {
    const url = new URL(value);
    return (url.protocol === 'https:' || url.protocol === 'http:') && /^https?:\/\//i.test(value);
  } catch {
    return false;
  }
}

export function PlanEditor({ mode, onClose }: { mode: Mode; onClose: () => void }) {
  const plan = mode.kind === 'plan' ? mode.plan : undefined;
  const step = mode.kind === 'step' ? mode.step : undefined;
  const [title, setTitle] = useState(plan?.title ?? step?.title ?? '');
  const [area, setArea] = useState<Area>(plan?.area ?? 'personal');
  const [note, setNote] = useState(plan?.note ?? '');
  const [date, setDate] = useState(step?.scheduledDate ?? '');
  const [url, setUrl] = useState('');
  const [cover, setCover] = useState(plan?.cover ?? '');
  const [reading, setReading] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const { submit, busy, error, isLocked, clearError } = useMutation();
  const operationId = useOperationId();

  function change(field: string, value: string, update: (value: string) => void) {
    update(value);
    setErrors(old => ({ ...old, [field]: '' }));
    clearError();
  }

  function upload(file: File | null) {
    if (!file) return;
    if (!['image/png', 'image/jpeg', 'image/webp'].includes(file.type) || file.size > 400_000) {
      setErrors(old => ({ ...old, cover: 'Выберите PNG, JPEG или WebP до 400 КБ.' }));
      return;
    }
    const reader = new FileReader();
    setReading(true);
    reader.onload = () => change('cover', String(reader.result), setCover);
    reader.onerror = () => setErrors(old => ({ ...old, cover: 'Не удалось прочитать файл.' }));
    reader.onloadend = () => setReading(false);
    reader.readAsDataURL(file);
  }

  function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (isLocked() || reading) return;

    const name = title.trim();
    const nextErrors: Record<string, string> = {};
    if (!name) nextErrors.title = 'Введите название.';
    if (mode.kind === 'step' && date && !isDateKey(date)) nextErrors.scheduledDate = 'Укажите корректную дату.';
    if (mode.kind === 'resource' && !isWebUrl(url.trim())) nextErrors.url = 'Введите ссылку http:// или https://.';
    setErrors(nextErrors);
    if (Object.keys(nextErrors).length) {
      const first = event.currentTarget.elements.namedItem(Object.keys(nextErrors)[0]);
      if (first instanceof HTMLElement) first.focus();
      return;
    }

    switch (mode.kind) {
      case 'plan': {
        const fields = { title: name, area, note: note.trim(), cover: cover || null };
        void submit(() => mode.plan
          ? planApi.edit(mode.plan.id, fields)
          : planApi.create(operationId(fields), fields), mode.saved);
        break;
      }
      case 'step': {
        const fields = { title: name, scheduledDate: date || null, done: mode.step?.done ?? false };
        void submit(() => mode.step
          ? planApi.editStep(mode.step.id, { title: fields.title, scheduledDate: fields.scheduledDate })
          : planApi.addStep(mode.planId, operationId(fields), fields), mode.saved);
        break;
      }
      case 'resource': {
        const fields = { title: name, url: url.trim() };
        void submit(() => planApi.addResource(mode.planId, operationId(fields), fields), mode.saved);
        break;
      }
    }
  }

  const heading = mode.kind === 'plan' ? (plan ? 'Редактировать план' : 'Новый план')
    : mode.kind === 'step' ? (step ? 'Редактировать шаг' : 'Новый шаг') : 'Добавить материал';
  const fieldError = (field: string) => errors[field] || error?.fields[field];

  return <Modal opened centered radius="lg" title={heading} closeButtonProps={{ 'aria-label': 'Закрыть' }}
    closeOnClickOutside={!busy} closeOnEscape={!busy} withCloseButton={!busy}
    styles={{ content: { background: 'var(--surface)' }, header: { background: 'var(--surface)' }, title: { fontSize: 22 } }}
    onClose={() => { if (!isLocked()) onClose(); }}>
    <form className={styles.form} onSubmit={save} noValidate aria-busy={busy}>
      {error && <Alert color="red" role="alert">{error.message}</Alert>}
      <TextInput name="title" label="Название" data-autofocus required value={title}
        maxLength={180} readOnly={busy} error={fieldError('title')}
        onChange={event => change('title', event.currentTarget.value, setTitle)} />
      {mode.kind === 'plan' && <>
        <NativeSelect label="Сфера" disabled={busy} value={area} error={fieldError('area')}
          data={[{ value: 'personal', label: 'Личное' }, { value: 'study', label: 'Учёба' }]}
          onChange={event => setArea(event.currentTarget.value as Area)} />
        <Textarea label="Заметка" value={note} maxLength={4000} readOnly={busy} minRows={3}
          error={fieldError('note')} onChange={event => change('note', event.currentTarget.value, setNote)} />
        <div className={styles.coverPreview}><PlanCover motif={plan?.motif ?? 'film'} cover={cover} /></div>
        <NativeSelect label="Обложка" disabled={busy || reading}
          value={cover.startsWith('data:') ? 'custom' : cover}
          data={[{ value: '', label: 'По умолчанию' }, ...covers.map(([value, label]) => ({ value, label })),
            ...(cover.startsWith('data:') ? [{ value: 'custom', label: 'Моя картинка' }] : [])]}
          onChange={event => { if (event.currentTarget.value !== 'custom') change('cover', event.currentTarget.value, setCover); }} />
        <FileInput label="Загрузить свою картинку" accept="image/png,image/jpeg,image/webp" disabled={busy || reading}
          error={fieldError('cover')} onChange={upload} />
      </>}
      {mode.kind === 'step' && <>
        <TextInput type="date" name="scheduledDate" label="Дата шага" value={date} readOnly={busy} error={fieldError('scheduledDate')}
          onChange={event => change('scheduledDate', event.currentTarget.value, setDate)} />
        {date && <Button variant="subtle" size="compact-sm" disabled={busy} onClick={() => change('scheduledDate', '', setDate)}>Снять дату</Button>}
      </>}
      {mode.kind === 'resource' && <TextInput type="url" name="url" label="Ссылка" required value={url}
        readOnly={busy} error={fieldError('url')} onChange={event => change('url', event.currentTarget.value, setUrl)} />}
      <Button className={styles.save} type="submit" disabled={reading} loading={busy}>{busy ? 'Сохраняем…' : 'Сохранить'}</Button>
    </form>
  </Modal>;
}

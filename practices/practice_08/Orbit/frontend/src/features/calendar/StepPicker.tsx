import { Alert, Button, Modal, Skeleton, Stack, Text } from '@mantine/core';
import { Link } from 'react-router-dom';
import { useLoad } from '../../app/useLoad';
import { useMutation } from '../../app/useMutation';
import { planApi, type AvailableStep } from '../plans/planApi';
import { fullDate } from './dates';
import styles from './calendar.module.css';

interface Props {
  day: string;
  calendarHref: string;
  onClose: () => void;
  onAssigned: (step: AvailableStep) => void;
}

export function StepPicker({ day, calendarHref, onClose, onAssigned }: Props) {
  const { data, failed, loading, refresh } = useLoad(planApi.available);
  const { busy, error, submit, isLocked } = useMutation();

  function assign(step: AvailableStep) {
    void submit(() => planApi.editStep(step.id, { scheduledDate: day }), () => onAssigned(step));
  }

  const groups = new Map<string, AvailableStep[]>();
  for (const step of data?.items ?? []) {
    const group = groups.get(step.planId);
    if (group) group.push(step);
    else groups.set(step.planId, [step]);
  }

  return <Modal opened centered radius="lg" title="Выбрать шаг из планов" closeButtonProps={{ 'aria-label': 'Закрыть' }}
    closeOnClickOutside={!busy} closeOnEscape={!busy} withCloseButton={!busy}
    styles={{ content: { background: 'var(--surface)' }, header: { background: 'var(--surface)' }, title: { fontSize: 22 } }}
    onClose={() => { if (!isLocked()) onClose(); }}>
    <Stack gap="sm">
      <Text c="var(--muted)">{fullDate(day)}</Text>
      {loading && <Skeleton height={52} role="status" aria-label="Загрузка шагов" />}
      {failed && <Alert color="red" role="alert">
        Не удалось загрузить шаги. <Button variant="subtle" size="compact-sm" onClick={refresh}>Повторить</Button>
      </Alert>}
      {error && <Alert color="red" role="alert">{error.message}</Alert>}
      {data?.items.length === 0 && <>
        <Text>Нет незавершённых шагов без даты.</Text>
        <Button component={Link} to="/plans" state={{ calendarHref }}>К планам</Button>
      </>}
      {[...groups].map(([planId, steps]) => <Stack key={planId} gap={6}>
        <Text size="sm" c="var(--muted)">{steps[0].planTitle}</Text>
        {steps.map(step => <Button key={step.id} variant="light" fullWidth disabled={busy}
          classNames={{ root: styles.pickButton, label: styles.pickLabel }}
          onClick={() => assign(step)}>{step.title}</Button>)}
      </Stack>)}
      {busy && <Text size="sm" role="status">Назначаем шаг…</Text>}
    </Stack>
  </Modal>;
}

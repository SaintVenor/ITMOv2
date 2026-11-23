import { Alert, Button, Card, Checkbox, Modal, Skeleton } from '@mantine/core';
import { useCallback, useEffect, useRef, useState } from 'react';
import { Link, useLocation, useNavigate, useParams, useSearchParams } from 'react-router-dom';
import { Header } from '../../app/Header';
import { useDialog } from '../../app/useDialog';
import { useLoad } from '../../app/useLoad';
import { useMutation } from '../../app/useMutation';
import { fullDate } from '../calendar/dates';
import { PlanEditor } from './PlanEditor';
import { PlanCover } from './PlanCover';
import { planApi, type PlanDetail, type Resource, type Step } from './planApi';
import styles from './plans.module.css';

type Editor = { kind: 'plan' } | { kind: 'step'; step?: Step } | { kind: 'resource' };

function PlanContent({ initial }: { initial: PlanDetail }) {
  const [plan, setPlan] = useState(initial);
  const [query, setQuery] = useSearchParams();
  const addFirstStep = query.get('add') === 'step';
  const dialog = useDialog<Editor>();
  const { open } = dialog;
  const addStepButton = useRef<HTMLButtonElement>(null);
  const { busy, error, submit, isLocked, clearError } = useMutation();
  const navigate = useNavigate();
  const { state } = useLocation();
  const removal = useDialog<Step | 'plan'>();
  const dragged = useRef<string | null>(null);
  const [dropTarget, setDropTarget] = useState<string | null>(null);

  function moveStep(id: string, destination: number) {
    const ids = plan.steps.map(step => step.id);
    const source = ids.indexOf(id);
    if (source === -1 || destination < 0 || destination >= ids.length || source === destination) return;
    ids.splice(source, 1);
    ids.splice(destination, 0, id);
    void submit(() => planApi.reorder(plan.id, ids), setPlan);
  }

  function remove() {
    const target = removal.value;
    if (target === 'plan') {
      void submit(() => planApi.removePlan(plan.id), () => navigate('/plans', { state, replace: true }));
    } else if (target) {
      void submit(() => planApi.removeStep(target.id), () => {
        setPlan(current => ({ ...current, steps: current.steps.filter(step => step.id !== target.id) }));
        removal.close();
        requestAnimationFrame(() => addStepButton.current?.focus());
      });
    }
  }

  useEffect(() => {
    if (addFirstStep) open({ kind: 'step' }, addStepButton.current);
  }, [addFirstStep, open]);

  function close() {
    dialog.close();
    if (addFirstStep) setQuery({}, { replace: true });
  }

  function updateStep(step: Step) {
    setPlan(previous => ({
      ...previous,
      steps: [...previous.steps.filter(item => item.id !== step.id), step].sort((left, right) => left.position - right.position),
    }));
  }

  function saveResource(resource: Resource) {
    setPlan(previous => ({
      ...previous,
      resources: previous.resources.some(item => item.id === resource.id)
        ? previous.resources.map(item => item.id === resource.id ? resource : item)
        : [...previous.resources, resource],
    }));
    close();
  }

  const editing = dialog.value;
  const count = plan.steps.filter(step => step.done).length;

  return <>
    <Card component="article" withBorder radius="lg" className={styles.detail}>
      <PlanCover motif={plan.motif} cover={plan.cover} />
      <div className={styles.heading}>
        <h1>{plan.title}</h1>
        <div className={styles.rowActions}>
          <Button variant="default" disabled={busy} onClick={() => dialog.open({ kind: 'plan' })}>Редактировать план</Button>
          <Button variant="subtle" color="red" disabled={busy} onClick={() => { clearError(); removal.open('plan'); }}>Удалить план</Button>
        </div>
      </div>
      {plan.note && <p className={styles.note}>{plan.note}</p>}
      {plan.steps.length > 0 && <div className={styles.progress}>
        <label htmlFor="plan-progress">{count} из {plan.steps.length}</label>
        <progress id="plan-progress" value={count} max={plan.steps.length} />
      </div>}

      {error && <Alert color="red" role="alert">{error.message}</Alert>}
      <section className={styles.section} aria-labelledby="steps-heading">
        <div className={styles.sectionHeading}>
          <h2 id="steps-heading">Шаги</h2>
          <Button ref={addStepButton} variant="light" disabled={busy} onClick={() => open({ kind: 'step' })}>
            {plan.steps.length ? 'Добавить шаг' : 'Добавить первый шаг'}
          </Button>
        </div>
        {plan.steps.length === 0 && <p className={styles.sectionEmpty}>Шагов пока нет.</p>}
        {plan.steps.length > 0 && <ol className={styles.list}>
          {plan.steps.map((step, index) => <li className={styles.row} key={step.id} data-drop={dropTarget === step.id || undefined}
            onDragOver={event => { if (dragged.current) { event.preventDefault(); setDropTarget(step.id); } }}
            onDrop={event => {
              event.preventDefault();
              if (dragged.current) moveStep(dragged.current, index);
              dragged.current = null;
              setDropTarget(null);
            }}>
            <div className={styles.stepContent}>
              <span className={styles.handle} aria-hidden="true" draggable={!busy}
                onDragStart={event => {
                  dragged.current = step.id;
                  event.dataTransfer.setData('text/plain', step.id);
                  event.dataTransfer.effectAllowed = 'move';
                }}
                onDragEnd={() => { dragged.current = null; setDropTarget(null); }}>⠿</span>
              <Checkbox label={step.title} checked={step.done} disabled={busy}
                onChange={event => {
                  const done = event.currentTarget.checked;
                  void submit(() => planApi.editStep(step.id, { done }), updateStep);
                }} />
              {step.scheduledDate && <Link className={styles.stepDate} to={'/calendar?date=' + step.scheduledDate}>
                {fullDate(step.scheduledDate)}
              </Link>}
            </div>
            <div className={styles.rowActions}>
              <Button size="compact-sm" variant="subtle" disabled={busy || index === 0}
                aria-label={'Поднять шаг «' + step.title + '»'} onClick={() => moveStep(step.id, index - 1)}>↑</Button>
              <Button size="compact-sm" variant="subtle" disabled={busy || index === plan.steps.length - 1}
                aria-label={'Опустить шаг «' + step.title + '»'} onClick={() => moveStep(step.id, index + 1)}>↓</Button>
              <Button size="compact-sm" variant="default" disabled={busy} onClick={() => dialog.open({ kind: 'step', step })}
                aria-label={'Редактировать шаг «' + step.title + '»'}>Править</Button>
              <Button size="compact-sm" variant="subtle" color="red" disabled={busy}
                aria-label={'Удалить шаг «' + step.title + '»'} onClick={() => { clearError(); removal.open(step); }}>Удалить</Button>
            </div>
          </li>)}
        </ol>}
      </section>

      <section className={styles.section} aria-labelledby="materials-heading">
        <div className={styles.sectionHeading}>
          <h2 id="materials-heading">Материалы</h2>
          <Button variant="light" disabled={busy} onClick={() => dialog.open({ kind: 'resource' })}>Добавить материал</Button>
        </div>
        {plan.resources.length === 0 && <p className={styles.sectionEmpty}>Материалов пока нет.</p>}
        {plan.resources.length > 0 && <ul className={styles.list}>
          {plan.resources.map(resource => <li className={styles.row} key={resource.id}>
            <a href={resource.url} target="_blank" rel="noreferrer">{resource.title}</a>
            <Button color="red" variant="subtle" size="compact-sm" disabled={busy}
              aria-label={'Удалить материал «' + resource.title + '»'}
              onClick={() => void submit(() => planApi.removeResource(resource.id), () =>
                setPlan(previous => ({ ...previous, resources: previous.resources.filter(item => item.id !== resource.id) })),
              )}>Удалить</Button>
          </li>)}
        </ul>}
      </section>
    </Card>
    {removal.value && <Modal opened centered title={removal.value === 'plan' ? 'Удалить план?' : 'Удалить шаг?'}
      closeButtonProps={{ 'aria-label': 'Закрыть' }} closeOnEscape={!busy} closeOnClickOutside={!busy}
      onClose={() => { if (!isLocked()) { clearError(); removal.close(); } }}>
      <p>{removal.value === 'plan'
        ? 'План, шаги, связанные записи в календаре и материалы будут удалены.'
        : 'Шаг и связанная запись в календаре будут удалены.'}</p>
      {error && <Alert role="alert" color="red">{error.message}</Alert>}
      <div className={styles.rowActions}>
        <Button variant="default" disabled={busy} onClick={removal.close}>Отмена</Button>
        <Button color="red" loading={busy} onClick={remove}>Подтвердить удаление</Button>
      </div>
    </Modal>}
    {editing?.kind === 'plan' && <PlanEditor mode={{ kind: 'plan', plan, saved: saved => { setPlan(saved); close(); } }} onClose={close} />}
    {editing?.kind === 'step' && <PlanEditor mode={{ kind: 'step', planId: plan.id, step: editing.step,
      saved: step => { updateStep(step); close(); } }} onClose={close} />}
    {editing?.kind === 'resource' && <PlanEditor mode={{ kind: 'resource', planId: plan.id, saved: saveResource }} onClose={close} />}
  </>;
}

export function PlanDetailPage() {
  const { id = '' } = useParams();
  const { state } = useLocation();
  const load = useCallback((signal: AbortSignal) => planApi.detail(id, signal), [id]);
  const { data, loading, failed, refresh } = useLoad(load);

  return <>
    <Header />
    <main className="shell content">
      <Link className={styles.back} to="/plans" state={state}>Все планы</Link>
      {loading && <Skeleton height={300} role="status" aria-label="Загрузка плана" />}
      {failed && <Alert color="red" role="alert">
        Не удалось открыть план. <Button variant="subtle" size="compact-sm" onClick={refresh}>Повторить</Button>
      </Alert>}
      {data && <PlanContent key={id} initial={data} />}
    </main>
  </>;
}

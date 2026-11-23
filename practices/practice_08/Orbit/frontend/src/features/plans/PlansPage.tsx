import { Alert, Button, Card, Skeleton } from '@mantine/core';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { Header } from '../../app/Header';
import { useDialog } from '../../app/useDialog';
import { useLoad } from '../../app/useLoad';
import { PlanCover } from './PlanCover';
import { PlanEditor } from './PlanEditor';
import { planApi, type PlanCard } from './planApi';
import styles from './plans.module.css';

function PlanGroup({ title, plans, state }: { title: string; plans: PlanCard[]; state: unknown }) {
  return <section className={styles.planGroup} aria-label={title}>
    <h2>{title} <span>{plans.length}</span></h2>
    <div className={styles.gallery}>
      {plans.map(plan => {
        const href = '/plans/' + encodeURIComponent(plan.id);
        const done = plan.steps.filter(step => step.done).length;
        const next = plan.steps.find(step => !step.done);
        return <Card className={styles.card} key={plan.id} withBorder padding="lg" radius="lg">
          <PlanCover motif={plan.motif} cover={plan.cover} />
          <h3><Link className={styles.cardLink} to={href} state={state}>{plan.title}</Link></h3>
          {plan.steps.length > 0 && <div className={styles.cardProgress}>
            <progress aria-label="Прогресс плана" value={done} max={plan.steps.length || 1} />
            <span>{done} из {plan.steps.length}</span>
          </div>}
          {next ? <p className={styles.next}><span>Далее</span> <strong>{next.title}</strong></p>
            : plan.steps.length ? <p className={styles.next}>Все шаги выполнены</p>
              : <Button className={styles.firstStep} component={Link} to={href + '?add=step'} state={state}
                variant="light" size="compact-sm">Добавить первый шаг</Button>}
        </Card>;
      })}
    </div>
  </section>;
}

export function PlansPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const dialog = useDialog<true>();
  const { data, loading, failed, refresh } = useLoad(planApi.list);
  const finished = (plan: PlanCard) => plan.steps.length > 0 && plan.steps.every(step => step.done);
  const pending = data?.items.filter(plan => !finished(plan)) ?? [];
  const completed = data?.items.filter(finished) ?? [];

  return <>
    <Header />
    <main className="shell content">
      <div className={styles.heading}>
        <h1>Планы</h1>
        <Button onClick={() => dialog.open(true)}>＋ Новый план</Button>
      </div>
      {loading && <Skeleton height={220} role="status" aria-label="Загрузка планов" />}
      {failed && <Alert color="red" role="alert">
        Не удалось загрузить планы. <Button variant="subtle" size="compact-sm" onClick={refresh}>Повторить</Button>
      </Alert>}
      {data?.items.length === 0 && <p>Планов пока нет.</p>}
      {data && <PlanGroup title="Запланированные" plans={pending} state={location.state} />}
      {data && <PlanGroup title="Выполненные" plans={completed} state={location.state} />}
    </main>
    {dialog.value && <PlanEditor mode={{ kind: 'plan', saved: plan => {
      dialog.close();
      navigate('/plans/' + encodeURIComponent(plan.id), { state: location.state });
    } }} onClose={dialog.close} />}
  </>;
}

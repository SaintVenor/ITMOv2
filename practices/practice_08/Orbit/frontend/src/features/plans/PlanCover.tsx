import type { Motif } from './planApi';
import styles from './plans.module.css';

export const covers = [
  ['dawn', 'Рассвет'], ['rings', 'Кольца'], ['reef', 'Риф'],
  ['atlas', 'Атлас'], ['comet', 'Комета'], ['field', 'Ночное поле'],
] as const;

export function PlanCover({ motif, cover }: { motif: Motif; cover?: string | null }) {
  const isImage = cover?.startsWith('data:image/');
  return <div className={styles.cover} data-motif={isImage ? motif : cover ?? motif} aria-hidden="true">
    {isImage && <img src={cover ?? undefined} alt="" />}
  </div>;
}

import { expect, test } from '@playwright/test';

test('из пустого выбора можно открыть планы и вернуться к выбранной дате', async ({ page }) => {
  await page.route('**/api/calendar?*', route => route.fulfill({ json: { items: [] } }));
  let release!: () => void;
  const response = new Promise<void>(resolve => { release = resolve; });
  await page.route('**/api/steps?unscheduled=true&done=false', async route => {
    await response;
    await route.fulfill({ json: { items: [] } });
  });
  await page.route('**/api/plans', route => route.fulfill({ json: { items: [] } }));
  await page.goto('/calendar?date=2026-11-21');
  await page.getByRole('button', { name: 'Выбрать шаг из планов' }).click();
  const picker = page.getByRole('dialog');
  try {
    await expect(picker.getByRole('status', { name: 'Загрузка шагов' })).toBeVisible();
    if (process.env.ORBIT_CAPTURE === '1') await picker.screenshot({ path: 'evidence/states/loading.png', animations: 'disabled' });
  } finally {
    release();
  }
  await expect(picker.getByText('Нет незавершённых шагов без даты.')).toBeVisible();
  if (process.env.ORBIT_CAPTURE === '1') await picker.screenshot({ path: 'evidence/states/empty.png', animations: 'disabled' });
  await picker.getByRole('link', { name: 'К планам' }).click();
  await expect(page.getByText('Планов пока нет.')).toBeVisible();
  await page.getByRole('link', { name: 'Календарь', exact: true }).click();
  await expect(page).toHaveURL(/date=2026-11-21/);
});

test('ошибка при назначении сохраняет выбор и разрешает повторить запрос', async ({ page }) => {
  const step = {
    id: 'mock-step', planId: 'mock-plan', planTitle: 'Снять первый короткий ролик', position: 1,
    title: 'Собрать черновик', done: false, scheduledDate: null, area: 'study',
  };
  let assigned = false;
  let requests = 0;
  await page.route('**/api/calendar?*', route => route.fulfill({ json: {
    items: assigned ? [{ ...step, kind: 'step', startDate: '2026-11-21', endDate: '2026-11-21' }] : [],
  } }));
  await page.route('**/api/steps?unscheduled=true&done=false', route => route.fulfill({ json: { items: [step] } }));
  await page.route('**/api/steps/mock-step', route => {
    requests += 1;
    expect(route.request().postDataJSON()).toEqual({ scheduledDate: '2026-11-21' });
    if (requests === 1) return route.fulfill({ status: 500, json: {} });
    assigned = true;
    return route.fulfill({ json: { ...step, scheduledDate: '2026-11-21' } });
  });

  await page.goto('/calendar?date=2026-11-21');
  await page.getByRole('combobox', { name: 'Сфера' }).selectOption('personal');
  await page.getByRole('button', { name: 'Выбрать шаг из планов' }).click();
  const dialog = page.getByRole('dialog');
  const choose = dialog.getByRole('button', { name: step.title });
  await choose.click();
  await expect(dialog.getByRole('alert')).toContainText('Сервер не смог выполнить запрос.');
  if (process.env.ORBIT_CAPTURE === '1') await dialog.screenshot({ path: 'evidence/states/error.png', animations: 'disabled' });
  await choose.click();
  await expect(dialog).toBeHidden();
  await expect(page.getByRole('heading', { name: step.title })).toBeVisible();
  await expect(page.getByRole('combobox', { name: 'Сфера' })).toHaveValue('');
  expect(requests).toBe(2);
});

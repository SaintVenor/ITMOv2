import { expect, test, type APIRequestContext } from '@playwright/test';

async function add(request: APIRequestContext, path: string, data: object) {
  const response = await request.post('/api' + path, { data });
  expect(response.status(), await response.text()).toBe(201);
  return response.json();
}

test('ежедневная серия начинается с указанной даты и поддерживает четыре области удаления', async ({ page, request }) => {
  const base = { id: 'edits-daily', title: 'Чтение по вечерам', kind: 'event', frequency: 'daily',
    startDate: '2026-11-21', endDate: '2026-11-21', startTime: '17:30', endTime: '18:30' };
  await add(request, '/entries', base);
  const dates = async () => {
    const response = await request.get('/api/calendar?from=2026-11-20&to=2026-11-27');
    const { items } = await response.json();
    return items.filter((item: { id: string }) => item.id === base.id).map((item: { occurrenceDate: string }) => item.occurrenceDate);
  };
  expect(await dates()).toEqual(['21', '22', '23', '24', '25', '26', '27'].map(day => '2026-11-' + day));
  await page.goto('/calendar?date=2026-11-23');
  const agenda = page.getByRole('complementary', { name: 'Повестка' });
  await agenda.getByRole('button', { name: 'Открыть запись' }).click();
  await expect(page.getByRole('dialog').getByLabel('Повторение', { exact: true })).toHaveValue('daily');
  await page.getByRole('dialog').getByRole('button', { name: 'Удалить', exact: true }).click();
  await expect(page.getByRole('dialog').getByLabel('Что удалить')).toHaveValue('one');
  await page.getByRole('dialog').getByRole('button', { name: 'Удалить запись' }).click();
  await expect(agenda.getByRole('heading', { name: base.title })).toHaveCount(0);
  expect(await dates()).not.toContain('2026-11-23');

  for (const [scope, day] of [['before', '22'], ['after', '26']]) {
    expect((await request.delete('/api/entries/' + base.id + '?scope=' + scope + '&occurrence=2026-11-' + day)).status()).toBe(204);
  }
  expect(await dates()).toEqual(['2026-11-24', '2026-11-25']);
  expect((await request.delete('/api/entries/' + base.id)).status()).toBe(204);
  expect(await dates()).toEqual([]);
});

test('ежемесячные серии пропускают отсутствующий день, ежегодные — невисокосный год', async ({ request }) => {
  for (const [id, frequency, startDate] of [
    ['edits-monthly', 'monthly', '2026-01-31'], ['edits-yearly', 'yearly', '2024-02-29'],
    ['edits-weekly', 'weekly', '2026-02-20'],
  ]) await add(request, '/entries', {
    id, frequency, kind: 'event', title: id, startDate, endDate: startDate,
  });
  async function dates(id: string, from: string, to: string) {
    const response = await request.get('/api/calendar', { params: { from, to } });
    const { items } = await response.json();
    return items.filter((item: { id: string }) => item.id === id).map((item: { startDate: string }) => item.startDate);
  }
  expect(await dates('edits-monthly', '2026-02-01', '2026-04-30')).toEqual(['2026-03-31']);
  expect(await dates('edits-yearly', '2025-01-01', '2028-03-01')).toEqual(['2028-02-29']);
  expect(await dates('edits-weekly', '2026-02-18', '2026-03-03')).toEqual(['2026-02-20', '2026-02-27']);
  for (const id of ['edits-monthly', 'edits-yearly', 'edits-weekly']) {
    expect((await request.delete('/api/entries/' + id)).status()).toBe(204);
  }
});

test('пара через неделю сохраняет выбранную первую дату', async ({ page, request }) => {
  await add(request, '/lessons', {
    id: 'edits-fortnight', subject: 'Двухнедельный семинар', room: '305',
    weekday: 3, startTime: '09:00', endTime: '10:30', termStart: '2027-02-01',
    termEnd: '2027-05-31', weekInterval: 2, firstDate: '2027-02-10',
  });
  await page.goto('/calendar?date=2027-02-10&view=week');
  await page.getByRole('switch', { name: 'Учебные пары' }).check();
  const week = page.getByRole('region', { name: 'Неделя' });
  await expect(week.getByRole('button', { name: /Двухнедельный семинар/ })).toBeVisible();
  await page.getByRole('button', { name: 'Следующая неделя' }).click();
  await expect(week.getByRole('button', { name: /Двухнедельный семинар/ })).toHaveCount(0);
  await page.getByRole('button', { name: 'Следующая неделя' }).click();
  await expect(week.getByRole('button', { name: /Двухнедельный семинар/ })).toBeVisible();
});

test('недельный вид показывает пересечения и сохраняет тёмную тему', async ({ page, request }) => {
  const day = '2027-02-10';
  for (const [id, title, startTime, endTime] of [['a', 'Консультация', '09:00', '10:30'], ['b', 'Онлайн-встреча', '09:15', '10:00']]) {
    await add(request, '/entries', { id: 'edits-week-' + id, title, kind: 'event', startDate: day, endDate: day, startTime, endTime });
  }
  await page.goto('/calendar?date=' + day);
  await page.getByText('Неделя', { exact: true }).click();
  const week = page.getByRole('region', { name: 'Неделя' });
  await expect(week.getByRole('button', { name: /Консультация.*Пересечение/ })).toBeVisible();
  await expect(week.getByRole('button', { name: /Онлайн-встреча.*Пересечение/ })).toBeVisible();
  await page.getByRole('button', { name: 'Тёмная тема' }).click();
  await expect(page.locator('html')).toHaveAttribute('data-mantine-color-scheme', 'dark');
  await page.reload();
  await expect(page.locator('html')).toHaveAttribute('data-mantine-color-scheme', 'dark');
  await page.setViewportSize({ width: 360, height: 844 });
  await expect(week.getByRole('button', { name: /Онлайн-встреча/ })).toBeVisible();
  const agenda = page.getByRole('complementary', { name: 'Повестка' });
  await expect(agenda.getByRole('heading', { name: 'Онлайн-встреча' })).toHaveCount(0);
  await week.getByRole('button', { name: /Онлайн-встреча/ }).click();
  await expect(page.getByRole('dialog').getByLabel('Название')).toHaveValue('Онлайн-встреча');
  await page.keyboard.press('Escape');

  const plan = await add(request, '/plans', { id: 'mobile-week-plan', title: 'План на среду' });
  try {
    await add(request, '/plans/' + plan.id + '/steps', {
      id: 'mobile-week-step', title: 'Подготовить вопросы', scheduledDate: day,
    });
    await page.reload();
    await expect(week.getByRole('button', { name: /Подготовить вопросы/ })).toHaveCount(0);
    await expect(agenda.getByRole('heading', { name: 'Подготовить вопросы' })).toBeVisible();
    await agenda.getByRole('button', { name: 'Отметить выполненным' }).click();
    await expect(agenda.getByText('Шаг плана · Выполнен')).toBeVisible();
    await expect(agenda.getByRole('link', { name: 'План на среду' })).toHaveAttribute('href', '/plans/' + plan.id);
  } finally {
    await request.delete('/api/plans/' + plan.id);
  }
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBe(360);
  await page.getByRole('button', { name: 'Следующая неделя' }).click();
  await expect(page).toHaveURL(/date=2027-02-17.*view=week/);
});

test('полный клик карточки, новая обложка, перенос и удаление шагов и плана', async ({ page, request }) => {
  const plan = await add(request, '/plans', { id: 'edits-plan', title: 'Маршрут проверки' });
  for (const [id, title] of [['edits-first', 'Первая точка'], ['edits-second', 'Вторая точка']]) {
    await add(request, '/plans/' + plan.id + '/steps', { id, title, done: true });
  }
  await page.goto('/plans');
  const archive = page.getByRole('region', { name: 'Выполненные' });
  const card = archive.getByRole('heading', { name: plan.title }).locator('..');
  const cover = await card.locator('[data-motif]').boundingBox();
  expect(cover).not.toBeNull();
  if (cover) await page.mouse.click(cover.x + cover.width / 2, cover.y + cover.height / 2);
  await expect(page.getByRole('heading', { name: plan.title })).toBeVisible();
  await page.getByRole('button', { name: 'Редактировать план' }).click();
  await page.getByLabel('Обложка', { exact: true }).selectOption('comet');
  await page.getByRole('dialog').getByRole('button', { name: 'Сохранить' }).click();
  await expect(page.locator('[data-motif="comet"]')).toBeVisible();
  const steps = page.getByRole('region', { name: 'Шаги' });
  const first = steps.getByRole('listitem').filter({ hasText: 'Первая точка' });
  const second = steps.getByRole('listitem').filter({ hasText: 'Вторая точка' });
  await second.locator('[draggable="true"]').dragTo(first);
  await expect(steps.getByRole('checkbox').first()).toHaveAccessibleName('Вторая точка');
  await page.reload();
  await expect(page.getByRole('region', { name: 'Шаги' }).getByRole('checkbox').first()).toHaveAccessibleName('Вторая точка');
  await page.getByRole('button', { name: 'Удалить шаг «Первая точка»' }).click();
  await page.getByRole('dialog').getByRole('button', { name: 'Подтвердить удаление' }).click();
  await expect(page.getByRole('checkbox', { name: 'Первая точка' })).toHaveCount(0);
  await page.getByRole('button', { name: 'Удалить план', exact: true }).click();
  await page.getByRole('dialog').getByRole('button', { name: 'Подтвердить удаление' }).click();
  await expect(page).toHaveURL(/\/plans$/);
  await expect(archive.getByRole('link', { name: plan.title })).toHaveCount(0);
});

test('длинный шаг переносится в окне выбора на ширине 360 px', async ({ page }) => {
  const title = 'Написать многопоточный интерпретатор для C++ на Rust и проверить длинное название';
  await page.route('**/api/calendar?*', route => route.fulfill({ json: { items: [] } }));
  await page.route('**/api/steps?*', route => route.fulfill({ json: { items: [{
    id: 'long-step', title, planId: 'p', planTitle: 'Изучить Rust', area: 'study', done: false,
  }] } }));
  await page.setViewportSize({ width: 360, height: 844 });
  await page.goto('/calendar?date=2026-11-21');
  await page.getByRole('button', { name: 'Выбрать шаг из планов' }).click();
  const button = page.getByRole('button', { name: title, exact: true });
  await expect(button).toBeVisible();
  expect(await button.evaluate(element => element.clientHeight)).toBeGreaterThan(40);
  expect(await button.evaluate(element => element.scrollWidth)).toBe(await button.evaluate(element => element.clientWidth));
});

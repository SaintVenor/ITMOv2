import { expect, test } from '@playwright/test';

const friday = '2026-11-27';
const term = { weekday: 5, termStart: '2026-11-20', termEnd: friday };
const lesson = {
  ...term, id: 'schedule-discrete', subject: 'Дискретная математика',
  room: '2403', startTime: '09:00', endTime: '10:30',
};

test('недельные пары сохраняются, не попадают в сводку и исчезают за границей семестра', async ({ page, request }) => {
  const event = await request.post('/api/entries', { data: {
    id: 'schedule-ordinary-event', kind: 'event', title: 'Поездка в Карелию',
    startDate: friday, endDate: '2026-12-02',
  } });
  expect(event.status()).toBe(201);
  for (const data of [
    { ...lesson, id: 'schedule-design', subject: 'Проектирование интерфейсов', room: '2312', startTime: '10:50', endTime: '12:20' },
    { ...lesson, id: 'schedule-language', subject: 'Английский язык', room: '3104', startTime: '13:00', endTime: '14:30' },
  ]) {
    expect((await request.post('/api/lessons', { data })).status()).toBe(201);
  }

  let lessonLoads = 0;
  let creates = 0;
  page.on('request', req => {
    if (new URL(req.url()).pathname !== '/api/lessons') return;
    if (req.method() === 'GET') lessonLoads += 1;
    if (req.method() === 'POST') creates += 1;
  });

  await page.setViewportSize({ width: 360, height: 844 });
  await page.goto('/calendar?date=' + friday);
  const show = page.getByRole('switch', { name: 'Учебные пары', exact: true });
  const agenda = page.getByRole('complementary', { name: 'Повестка' });
  const month = page.getByRole('region', { name: 'Месяц' });
  const summary = page.getByText('1 событие', { exact: true });
  const add = page.getByRole('button', { name: 'Добавить пару', exact: true });
  const count = month.getByRole('button', { name: '3 пары · пятница, 27 ноября 2026' });
  await expect(summary).toBeVisible();
  await expect(show).not.toBeChecked();
  expect(lessonLoads).toBe(0);
  await expect(add).toHaveCount(0);

  await show.focus();
  await page.keyboard.press('Space');
  await expect(add).toBeVisible();
  await add.click();
  const form = page.getByRole('dialog', { name: 'Добавить пару' });
  const save = form.getByRole('button', { name: 'Сохранить' });
  await expect(form.getByRole('textbox', { name: 'Предмет' })).toBeFocused();
  await expect(form.getByLabel('День недели')).toHaveValue('5');
  await form.getByRole('textbox', { name: 'Предмет' }).fill(lesson.subject);
  await form.getByRole('textbox', { name: 'Аудитория' }).fill(lesson.room);
  await form.getByLabel('Начало пары', { exact: true }).fill(lesson.startTime);
  await form.getByLabel('Конец пары', { exact: true }).fill('08:00');
  await form.getByLabel('Начало семестра', { exact: true }).fill(term.termStart);
  await save.click();
  await expect(form.getByText('Окончание пары должно быть позже начала.')).toBeVisible();
  await expect(form.getByLabel('Конец пары', { exact: true })).toBeFocused();
  await expect(form.getByRole('textbox', { name: 'Предмет' })).toHaveValue(lesson.subject);
  expect(creates).toBe(0);

  await form.getByLabel('Конец пары', { exact: true }).fill(lesson.endTime);
  await save.click();
  await expect(form).toBeHidden();
  await expect(add).toBeFocused();
  await expect(count).toBeVisible();
  await expect(agenda.getByText('09:00–10:30 · Аудитория 2403')).toBeVisible();
  await expect(summary).toBeVisible();
  await expect(agenda.getByRole('heading', { name: 'Поездка в Карелию' })).toBeVisible();
  expect(creates).toBe(1);
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBe(360);

  await page.getByRole('button', { name: 'Фильтры' }).click();
  await page.getByRole('combobox', { name: 'Тип' }).selectOption('deadline');
  await expect(count).toBeVisible();
  await expect(agenda.getByRole('heading', { name: 'Поездка в Карелию' })).toHaveCount(0);
  await page.getByRole('button', { name: 'Сбросить фильтры' }).click();
  await expect(summary).toBeVisible();

  await show.uncheck();
  await expect(count).toHaveCount(0);
  await expect(agenda.getByRole('heading', { name: lesson.subject })).toHaveCount(0);
  await expect(agenda.getByRole('heading', { name: 'Поездка в Карелию' })).toBeVisible();
  await expect(summary).toBeVisible();
  await page.reload();
  await expect(show).not.toBeChecked();
  await show.check();
  await expect(count).toBeVisible();
  await expect(agenda.getByText('09:00–10:30 · Аудитория 2403')).toBeVisible();

  await month.getByRole('button', { name: '3 пары · пятница, 20 ноября 2026' }).click();
  await expect(agenda.getByRole('heading', { name: 'пятница, 20 ноября 2026' })).toBeFocused();
  await expect(agenda.getByRole('heading', { name: lesson.subject })).toBeVisible();
  await page.getByRole('button', { name: 'Следующий месяц' }).click();
  await month.getByRole('button', { name: 'пятница, 4 декабря 2026', exact: true }).getByText('4', { exact: true }).click();
  await expect(agenda.getByRole('heading', { name: lesson.subject })).toHaveCount(0);
  await expect(month.getByRole('button', { name: /пары · пятница, 4 декабря/ })).toHaveCount(0);

  await page.getByRole('button', { name: 'Предыдущий месяц' }).click();
  await count.click();
  await agenda.getByRole('button', { name: 'Редактировать пару «' + lesson.subject + '»' }).click();
  const edit = page.getByRole('dialog', { name: 'Редактировать пару' });
  await edit.getByRole('textbox', { name: 'Аудитория' }).fill('2500');
  await edit.getByRole('button', { name: 'Сохранить' }).click();
  await expect(agenda.getByText('09:00–10:30 · Аудитория 2500')).toBeVisible();
  await agenda.getByRole('button', { name: 'Редактировать пару «' + lesson.subject + '»' }).click();
  await edit.getByRole('button', { name: 'Удалить', exact: true }).click();
  await page.getByRole('dialog', { name: 'Удалить пару?' }).getByRole('button', { name: 'Удалить пару', exact: true }).click();
  await expect(month.getByRole('button', { name: '2 пары · пятница, 27 ноября 2026' })).toBeVisible();
  await expect(agenda.getByRole('heading', { name: lesson.subject })).toHaveCount(0);
  await expect(summary).toBeVisible();

  for (const number of [1, 2, 3]) {
    const extra = await request.post('/api/entries', { data: {
      id: 'schedule-overflow-' + number, title: 'Встреча ' + number, kind: 'event', startDate: friday, endDate: friday,
    } });
    expect(extra.status()).toBe(201);
  }
  await page.reload();
  await show.check();
  await month.getByRole('button', { name: 'Ещё 1 · пятница, 27 ноября 2026' }).click();
  await expect(agenda.getByRole('heading', { name: 'Встреча 3' })).toBeVisible();
  await month.getByRole('button', { name: '2 пары · пятница, 27 ноября 2026' }).click();
  await expect(agenda.getByRole('heading', { name: 'Английский язык' })).toBeVisible();
});

test('API проверяет период семестра и повторное создание пары', async ({ request }) => {
  const payload = { ...lesson, id: 'schedule-api' };
  const invalid = await request.post('/api/lessons', { data: { ...payload, termStart: '2026-11-23', termEnd: '2026-11-24' } });
  expect(invalid.status()).toBe(422);
  expect((await invalid.json()).detail[0].loc).toEqual(['body', 'termEnd']);
  const create = () => request.post('/api/lessons', { data: payload });
  expect((await create()).status()).toBe(201);
  expect((await create()).status()).toBe(201);
  const inTerm = await request.get('/api/lessons?from=2026-11-27&to=2026-11-27');
  expect((await inTerm.json()).items.filter((item: { id: string }) => item.id === payload.id)).toHaveLength(1);
  const afterTerm = await request.get('/api/lessons?from=2026-11-28&to=2026-12-05');
  expect((await afterTerm.json()).items).toEqual([]);
});

test('сбой расписания оставляет доступным обычный календарь', async ({ page }) => {
  await page.route('**/api/calendar?*', route => route.fulfill({ json: { items: [{
    id: 'schedule-mock', kind: 'event', title: 'Консультация', area: 'study', startDate: friday, endDate: friday,
  }] } }));
  let fails = true;
  await page.route('**/api/lessons?*', route => fails
    ? route.fulfill({ status: 500, json: {} })
    : route.fulfill({ json: { items: [lesson] } }));
  await page.goto('/calendar?date=' + friday);
  await page.getByRole('switch', { name: 'Учебные пары', exact: true }).check();
  await expect(page.getByRole('alert')).toContainText('Не удалось загрузить учебное расписание.');
  await expect(page.getByRole('heading', { name: 'Консультация' })).toBeVisible();
  await expect(page.getByText('1 событие', { exact: true })).toBeVisible();
  fails = false;
  await page.getByRole('button', { name: 'Повторить', exact: true }).click();
  await expect(page.getByRole('heading', { name: lesson.subject })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Консультация' })).toBeVisible();
});

test('разовая пара сохраняет дату и тип, переключатель остаётся на месте', async ({ page, request }) => {
  await page.setViewportSize({ width: 360, height: 844 });
  await page.clock.install();
  await page.goto('/calendar?date=2027-01-14&view=day');
  await expect(page.getByRole('heading', { name: '14 января', exact: true })).toBeVisible();
  const toggle = page.getByRole('switch', { name: 'Учебные пары' });
  const before = await toggle.boundingBox();
  await toggle.check();
  expect(await toggle.boundingBox()).toEqual(before);
  await page.getByRole('button', { name: 'Добавить пару' }).click();
  const dialog = page.getByRole('dialog');
  await dialog.getByLabel('Предмет').fill('Разовая физика');
  await dialog.getByLabel('Аудитория').fill('101');
  await dialog.getByLabel('Тип пары').selectOption('lab');
  await dialog.getByLabel('Повторение пары').selectOption('once');
  await dialog.getByLabel('Дата пары').fill('2027-01-15');
  await dialog.getByLabel('Начало пары').fill('09:00');
  await dialog.getByLabel('Конец пары').fill('10:30');
  if (process.env.ORBIT_CAPTURE_DAY) await page.screenshot({ path: '.cache/day-preview/one-off-lesson.png' });
  await dialog.getByRole('button', { name: 'Сохранить' }).click();
  const lessonCard = page.getByRole('button', { name: /Лабораторная.*Разовая физика/ });
  await expect(lessonCard).toBeVisible();
  const savedNotice = page.getByRole('status').filter({ hasText: 'Пара сохранена.' });
  await expect(savedNotice).toBeVisible();
  await page.clock.fastForward(4000);
  await expect(savedNotice).toHaveCount(0);
  await expect(page.getByText('10:30', { exact: true })).toBeVisible();
  const results = await request.get('/api/lessons?from=2027-01-15&to=2027-01-15');
  const pair = (await results.json()).items.find((item: { subject: string }) => item.subject === 'Разовая физика');
  try {
    expect(pair).toMatchObject({ termStart: '2027-01-15', termEnd: '2027-01-15', lessonType: 'lab' });
    await lessonCard.click();
    await expect(dialog.getByLabel('Повторение пары')).toHaveValue('once');
    await page.keyboard.press('Escape');
    await page.goto('/calendar?date=2027-01-22&view=day');
    await page.getByRole('switch', { name: 'Учебные пары' }).check();
    await expect(page.getByRole('heading', { name: 'Свободный день' })).toBeVisible();
    await expect(lessonCard).toHaveCount(0);
  } finally {
    await request.delete('/api/lessons/' + pair.id);
  }
});

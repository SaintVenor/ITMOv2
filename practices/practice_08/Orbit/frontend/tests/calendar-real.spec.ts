import { expect, test, type Page } from '@playwright/test';

const calendar = '/calendar?date=2026-11-27';
const trip = 'Поездка в Карелию';

const real = test.extend<{ cleanupEntries: string[] }>({
  cleanupEntries: async ({ request }, use) => {
    const ids: string[] = [];
    await use(ids);
    for (const id of ids) {
      const response = await request.delete('/api/entries/' + id);
      expect([204, 404]).toContain(response.status());
    }
  },
});

async function addTrip(page: Page, cleanupEntries: string[]) {
  await page.goto(calendar);
  await page.getByRole('banner').getByRole('button', { name: 'Добавить запись' }).click();
  const dialog = page.getByRole('dialog');
  await dialog.getByRole('textbox', { name: 'Название' }).fill(trip);
  await expect(dialog.getByLabel('Начало', { exact: true })).toHaveValue('2026-11-27');
  await expect(dialog.getByLabel('Окончание', { exact: true })).toHaveValue('2026-11-27');
  await dialog.getByLabel('Окончание', { exact: true }).fill('2026-12-02');
  const response = page.waitForResponse(res => res.url().endsWith('/api/entries') && res.request().method() === 'POST');
  await dialog.getByRole('button', { name: 'Сохранить' }).click();
  const created = await response;
  expect(created.status()).toBe(201);
  cleanupEntries.push((await created.json()).id);
  await expect(dialog).toBeHidden();
  await expect(page.getByText('Запись сохранена.')).toBeVisible();
}

for (const width of [1440, 360]) {
  real('поездка переживает reload, перенос конца и удаление при ширине ' + width, async ({ page, request, cleanupEntries }) => {
    await page.setViewportSize({ width, height: width === 1440 ? 900 : 844 });
    await addTrip(page, cleanupEntries);
    const agenda = page.getByRole('complementary', { name: 'Повестка' });
    const month = page.getByRole('region', { name: 'Месяц' });
    const segments = month.getByRole('button', { name: trip + ' · Событие' });
    await expect(segments).toHaveCount(2);
    await expect(page.getByText('1 событие', { exact: true })).toBeVisible();
    await expect(agenda.getByRole('heading', { name: trip })).toBeVisible();

    await page.getByRole('button', { name: 'суббота, 28 ноября 2026', exact: true }).getByText('28', { exact: true }).click();
    await expect(agenda.getByText('27 ноя — 2 дек · день 2 из 6')).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBe(width);

    await page.reload();
    await expect(agenda.getByRole('heading', { name: trip })).toBeVisible();
    await expect(segments).toHaveCount(2);
    if (width === 1440) {
      for (const segment of await segments.all()) {
        await segment.click();
        await expect(page.getByRole('dialog').getByLabel('Начало', { exact: true })).toHaveValue('2026-11-27');
        await page.keyboard.press('Escape');
      }
    }

    await page.getByRole('button', { name: 'Следующий месяц' }).click();
    await expect(page).toHaveURL(/date=2026-12-01/);
    await expect(agenda.getByText('27 ноя — 2 дек · день 5 из 6')).toBeVisible();
    await agenda.getByRole('button', { name: 'Открыть запись' }).click();
    const dialog = page.getByRole('dialog');
    await expect(dialog.getByRole('textbox', { name: 'Название' })).toHaveValue(trip);
    await dialog.getByLabel('Окончание', { exact: true }).fill('2026-12-04');
    await dialog.getByRole('button', { name: 'Сохранить' }).click();
    await expect(agenda.getByText('27 ноя — 4 дек · день 5 из 8')).toBeVisible();
    await page.reload();
    await expect(agenda.getByText('27 ноя — 4 дек · день 5 из 8')).toBeVisible();
    const december = await request.get('/api/calendar?from=2026-12-01&to=2026-12-31');
    expect((await december.json()).items).toMatchObject([{ title: trip, startDate: '2026-11-27', endDate: '2026-12-04' }]);

    await agenda.getByRole('button', { name: 'Открыть запись' }).click();
    await dialog.getByRole('button', { name: 'Удалить', exact: true }).click();
    await expect(dialog.getByText('Будет удалено всё событие')).toBeVisible();
    await dialog.getByRole('button', { name: 'Удалить запись' }).click();
    await expect(agenda.getByRole('heading', { name: trip })).toHaveCount(0);
    await expect(page.getByText('Запись удалена.')).toBeVisible();
  });
}

test('пересекающий весь диапазон интервал, ночь и ежегодная дата читаются из SQLite', async ({ request }) => {
  const outside = {
    id: 'integration-long', title: 'Долгая поездка', kind: 'event',
    startDate: '2026-10-01', endDate: '2027-01-12',
  };
  const midnight = {
    id: 'integration-midnight', title: 'Ночной поезд', kind: 'event',
    startDate: '2026-11-27', endDate: '2026-11-28', startTime: '22:00', endTime: '00:00',
  };
  const leap = { id: 'integration-leap', title: 'Лия', kind: 'birthday', birthDay: 29, birthMonth: 2 };
  for (const data of [outside, midnight, leap]) {
    expect((await request.post('/api/entries', { data })).status()).toBe(201);
  }
  expect((await request.post('/api/entries', { data: outside })).status()).toBe(201);
  expect((await request.post('/api/entries', { data: { ...outside, title: 'Другая поездка' } })).status()).toBe(409);
  const extract = async (from: string, to = from) =>
    (await (await request.get('/api/calendar', { params: { from, to } })).json()).items;
  expect(await extract('2026-11-28')).toMatchObject([
    { id: outside.id }, { id: midnight.id, endTime: '00:00' },
  ]);
  expect(await extract('2027-02-01', '2027-02-28')).toEqual([]);
  expect(await extract('2028-02-01', '2028-02-29')).toMatchObject([
    { id: leap.id, startDate: '2028-02-29', area: 'personal' },
  ]);
  for (const { id } of [outside, midnight, leap]) {
    expect((await request.delete('/api/entries/' + id)).status()).toBe(204);
  }
});

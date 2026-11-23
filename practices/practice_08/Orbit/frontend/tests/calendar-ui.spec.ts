import { expect, test, type Locator, type Page } from '@playwright/test';

const date = '/calendar?date=2026-11-28';
const sample = {
  id: 'event-1', title: 'Встреча с одногруппниками', kind: 'event', area: 'personal',
  startDate: '2026-11-28', endDate: '2026-11-28',
};

async function add(page: Page) {
  await page.getByRole('banner').getByRole('button', { name: 'Добавить запись' }).click();
  return page.getByRole('dialog');
}

async function mockCalendar(page: Page) {
  const items: object[] = [];
  await page.route('**/api/calendar?*', route => route.fulfill({ json: { items } }));
  return items;
}

function gate() {
  let release!: () => void;
  const wait = new Promise<void>(resolve => { release = resolve; });
  return { release, wait };
}

test('клавиатура, Escape, фокус и ошибки конкретных полей', async ({ page }) => {
  await mockCalendar(page);
  let requests = 0;
  await page.route('**/api/entries', route => { requests += 1; return route.fulfill({ status: 500 }); });
  await page.goto(date);
  const month = page.getByRole('region', { name: 'Месяц' });
  const selected = month.getByRole('button', { name: 'суббота, 28 ноября 2026' });
  await expect(month.locator('button[tabindex="0"]')).toHaveCount(1);
  await selected.focus();
  await page.keyboard.press('ArrowRight');
  await expect(month.getByRole('button', { name: 'воскресенье, 29 ноября 2026' })).toBeFocused();
  await page.keyboard.press('Enter');
  await expect(page).toHaveURL(/date=2026-11-29/);

  const trigger = page.getByRole('banner').getByRole('button', { name: 'Добавить запись' });
  await trigger.focus();
  await page.keyboard.press('Enter');
  const dialog = page.getByRole('dialog');
  await expect(dialog.getByRole('textbox', { name: 'Название' })).toBeFocused();
  await page.keyboard.press('Escape');
  await expect(dialog).toBeHidden();
  await expect(trigger).toBeFocused();

  await add(page);
  const save = dialog.getByRole('button', { name: 'Сохранить' });
  await save.click();
  await expect(dialog.getByText('Введите название.')).toBeVisible();
  await dialog.getByRole('textbox', { name: 'Название' }).fill(sample.title);
  await dialog.getByLabel('Начало', { exact: true }).fill('2026-11-30');
  await expect(dialog.getByLabel('Окончание', { exact: true })).toHaveValue('2026-11-30');
  await dialog.getByLabel('Окончание', { exact: true }).fill('2026-11-29');
  await dialog.getByLabel('Начало', { exact: true }).fill('2026-12-01');
  await expect(dialog.getByLabel('Окончание', { exact: true })).toHaveValue('2026-11-29');
  await save.click();
  await expect(dialog.getByText('Окончание раньше начала.')).toBeVisible();
  await expect(dialog.getByRole('textbox', { name: 'Название' })).toHaveValue(sample.title);
  expect(requests).toBe(0);
  await dialog.getByLabel('Тип записи').selectOption('deadline');
  await expect(dialog.getByLabel('Дата сдачи', { exact: true })).toHaveValue('2026-12-01');
});

test('задержка, пустые данные, ошибки загрузки и сохранения, затем успех', async ({ page }) => {
  const first = gate();
  const items: object[] = [];
  let failGet = false;
  let failPost = true;
  const operationIds: string[] = [];
  await page.route('**/api/calendar?*', async route => {
    await first.wait;
    await route.fulfill(failGet ? { status: 500, json: {} } : { json: { items } });
  });
  await page.route('**/api/entries', async route => {
    const fields = route.request().postDataJSON();
    operationIds.push(fields.id);
    if (failPost) {
      await route.fulfill({ status: 500, json: {} });
    } else {
      items.push({ ...sample, ...fields });
      failGet = true;
      await route.fulfill({ status: 201, json: fields });
    }
  });

  await page.goto(date);
  const shot = async (name: string) => {
    if (process.env.ORBIT_CAPTURE === '1') await page.screenshot({ path: '.cache/calendar-states/' + name + '.png', fullPage: true });
  };
  await expect(page.getByRole('status', { name: 'Загрузка записей' })).toBeVisible();
  await shot('calendar-test-delay');
  first.release();
  await expect(page.getByText('В этом месяце пока нет записей.')).toBeVisible();
  await shot('calendar-test-empty');

  failGet = true;
  await page.getByRole('button', { name: 'Следующий месяц' }).click();
  await expect(page.getByRole('alert')).toContainText('Не удалось загрузить календарь.');
  failGet = false;
  await page.getByRole('button', { name: 'Повторить', exact: true }).click();
  await expect(page.getByText('В этом месяце пока нет записей.')).toBeVisible();
  await page.getByRole('button', { name: 'Предыдущий месяц' }).click();
  const dialog = await add(page);
  await dialog.getByRole('textbox', { name: 'Название' }).fill(sample.title);
  await dialog.getByRole('button', { name: 'Сохранить' }).click();
  await expect(dialog.getByRole('alert')).toContainText('Сервер не смог выполнить запрос.');
  await expect(dialog.getByRole('textbox', { name: 'Название' })).toHaveValue(sample.title);
  await shot('calendar-test-error-500');

  failPost = false;
  await dialog.getByRole('button', { name: 'Сохранить' }).click();
  await expect(dialog).toBeHidden();
  await expect(page.getByText('Запись сохранена.')).toBeVisible();
  await expect(page.getByRole('alert')).toContainText('Не удалось загрузить календарь.');
  failGet = false;
  await page.getByRole('button', { name: 'Повторить', exact: true }).click();
  await expect(page.getByRole('heading', { name: sample.title })).toBeVisible();
  expect(operationIds).toHaveLength(2);
  expect(operationIds[0]).toBe(operationIds[1]);
  await shot('calendar-test-success');
});

const submissions: Record<string, (page: Page, save: Locator) => Promise<void>> = {
  'двойной клик': async (_page, save) => { await save.dblclick(); },
  'повторный Enter': async (page) => { await page.keyboard.press('Enter'); await page.keyboard.press('Enter'); },
};

for (const [name, submit] of Object.entries(submissions)) {
  test(name + ' во время отправки не создаёт второй POST', async ({ page }) => {
    const items = await mockCalendar(page);
    const pending = gate();
    let requests = 0;
    await page.route('**/api/entries', async route => {
      requests += 1;
      await pending.wait;
      const fields = route.request().postDataJSON();
      items.push({ ...sample, ...fields });
      await route.fulfill({ status: 201, json: fields });
    });
    try {
      await page.goto(date);
      const dialog = await add(page);
      await dialog.getByRole('textbox', { name: 'Название' }).fill(sample.title);
      await submit(page, dialog.getByRole('button', { name: 'Сохранить' }));
      await expect.poll(() => requests).toBe(1);
      await expect(dialog.getByRole('button', { name: 'Сохраняем…' })).toBeDisabled();
      pending.release();
      await expect(dialog).toBeHidden();
      await expect(page.getByRole('heading', { name: sample.title })).toHaveCount(1);
      expect(requests).toBe(1);
    } finally {
      pending.release();
    }
  });
}

test('задержанный ответ старого месяца не меняет текущий', async ({ page }) => {
  const decemberStarted = gate();
  const slowDecember = gate();
  const decemberSettled = gate();
  await page.route('**/api/calendar?*', async route => {
    const from = new URL(route.request().url()).searchParams.get('from');
    if (from === '2026-11-30') {
      decemberStarted.release();
      await slowDecember.wait;
      try {
        await route.fulfill({ json: { items: [{
          ...sample, title: 'Старый ответ', startDate: '2026-12-01', endDate: '2026-12-01',
        }] } });
      } catch {
        // Chromium may already have aborted the obsolete request.
      } finally {
        decemberSettled.release();
      }
    } else {
      await route.fulfill({ json: { items: from === '2026-12-28' ? [{
        ...sample, title: 'Январская встреча', startDate: '2027-01-01', endDate: '2027-01-01',
      }] : [] } });
    }
  });

  try {
    await page.goto(date);
    const next = page.getByRole('button', { name: 'Следующий месяц' });
    await next.click();
    await decemberStarted.wait;
    await next.click();
    await expect(page.getByRole('heading', { name: 'Январь 2027' })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Январская встреча' })).toBeVisible();
    slowDecember.release();
    await decemberSettled.wait;
    await expect(page.getByRole('heading', { name: 'Январская встреча' })).toBeVisible();
    await expect(page.getByText('Старый ответ')).toHaveCount(0);
  } finally {
    slowDecember.release();
  }
});

test('фильтры и переполнение сохраняют полный список дня', async ({ page }) => {
  const items = await mockCalendar(page);
  items.push(
    { ...sample, title: 'Поездка 1', startDate: '2026-11-26', endDate: '2026-12-02' },
    { ...sample, id: '2', title: 'Поездка 2', startDate: '2026-11-27', endDate: '2026-12-03' },
    { ...sample, id: '3', title: 'Экскурсия', startDate: '2026-11-27', endDate: '2026-11-29' },
    { ...sample, id: '4', title: 'Лабораторная', kind: 'deadline', area: 'study', startTime: '18:00' },
  );
  await page.goto('/calendar?date=2026-11-27');
  await expect(page.getByText('1 дедлайн · 3 события')).toBeVisible();
  await page.getByRole('button', { name: 'Ещё 1 · суббота, 28 ноября 2026' }).click();
  const agenda = page.getByRole('complementary', { name: 'Повестка' });
  await expect(agenda.getByRole('button', { name: 'Открыть запись' })).toHaveCount(4);
  await expect(agenda.getByText('Сдать до 18:00')).toBeVisible();
  await page.getByRole('combobox', { name: 'Сфера' }).selectOption('study');
  await expect(agenda.getByRole('button', { name: 'Открыть запись' })).toHaveCount(1);
  await page.getByRole('combobox', { name: 'Тип' }).selectOption('event');
  await expect(agenda.getByText('Нет записей по выбранным фильтрам.')).toBeVisible();
  await page.getByRole('button', { name: 'Сбросить фильтры' }).click();
  await expect(agenda.getByRole('button', { name: 'Открыть запись' })).toHaveCount(4);
});

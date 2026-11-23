import { expect, test, type APIRequestContext, type Page } from '@playwright/test';

const title = 'Снять первый короткий ролик';
const draft = 'Собрать черновик';
const tutorial = 'https://www.blender.org/support/tutorials/';
const saturday = '2026-11-21';

async function post(request: APIRequestContext, path: string, data: object) {
  const response = await request.post('/api' + path, { data });
  expect(response.status(), await response.text()).toBe(201);
  return response.json();
}

async function screenshot(page: Page, name: string) {
  if (process.env.ORBIT_CAPTURE === '1') await page.screenshot({ path: 'evidence/' + name + '.png', fullPage: true });
}

test('из плана в повестку и обратно: назначение, выполнение, перенос и снятие даты', async ({ page, request }) => {
  await post(request, '/plans', {
    id: 'film-integration', title, motif: 'film', note: 'Собрать ролик из коротких кадров и попробовать монтаж.',
  });
  await post(request, '/plans/film-integration/steps', { id: 'watch-integration', title: 'Посмотреть урок', done: true });
  await post(request, '/plans/film-integration/steps', { id: 'draft-integration', title: draft });
  await post(request, '/plans/film-integration/steps', { id: 'review-integration', title: 'Посмотреть ролик целиком' });
  await post(request, '/plans/film-integration/resources', { id: 'tutorial-integration', title: 'Урок по монтажу', url: tutorial });

  await page.goto('/calendar?date=' + saturday);
  const nav = page.getByRole('navigation', { name: 'Разделы' });
  await nav.getByRole('link', { name: 'Планы', exact: true }).click();
  await expect(page.getByText('1 из 3', { exact: true })).toBeVisible();
  await expect(page.getByText(draft, { exact: true })).toBeVisible();
  await page.getByRole('link', { name: title }).click();
  await expect(page.getByRole('link', { name: 'Урок по монтажу' })).toHaveAttribute('href', tutorial);
  await expect(page.getByRole('checkbox', { name: draft })).not.toBeChecked();
  await nav.getByRole('link', { name: 'Календарь', exact: true }).click();
  await expect(page).toHaveURL(/date=2026-11-21/);

  const agenda = page.getByRole('complementary', { name: 'Повестка' });
  const pick = agenda.getByRole('button', { name: 'Выбрать шаг из планов' });
  await expect(agenda.getByText('На этот день ничего не запланировано.')).toBeVisible();
  await screenshot(page, 'scenario/free-day');
  await pick.focus();
  await page.keyboard.press('Enter');
  const dialog = page.getByRole('dialog', { name: 'Выбрать шаг из планов' });
  await expect(dialog.getByRole('button', { name: draft, exact: true })).toBeVisible();
  await expect(dialog.getByRole('button', { name: 'Посмотреть урок', exact: true })).toHaveCount(0);
  await expect(dialog.getByText('суббота, 21 ноября 2026')).toBeVisible();
  await screenshot(page, 'scenario/choose-step');
  await dialog.getByRole('button', { name: draft, exact: true }).focus();
  await page.keyboard.press('Enter');
  await expect(dialog).toBeHidden();
  await expect(pick).toBeFocused();
  await expect(agenda.getByRole('heading', { name: draft })).toBeVisible();

  await page.reload();
  await expect(agenda.getByRole('heading', { name: draft })).toBeVisible();
  await screenshot(page, 'scenario/assigned-after-reload');
  await agenda.getByRole('button', { name: 'Отметить выполненным' }).click();
  await expect(agenda.getByText('Шаг плана · Выполнен')).toBeVisible();
  await expect(page.getByRole('region', { name: 'Месяц' }).getByRole('button', { name: draft + ' · Шаг плана' })).toBeVisible();
  await screenshot(page, 'scenario/completed-step');
  await agenda.getByRole('link', { name: title }).click();
  await expect(page.getByText('2 из 3', { exact: true })).toBeVisible();
  await expect(page.getByRole('checkbox', { name: draft })).toBeChecked();
  await expect(page.getByRole('link', { name: 'суббота, 21 ноября 2026' })).toBeVisible();
  await screenshot(page, 'comparison/plan-app-desktop');

  await page.setViewportSize({ width: 360, height: 844 });
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBe(360);
  await page.setViewportSize({ width: 390, height: 844 });
  await screenshot(page, 'comparison/plan-app-mobile');
  await page.setViewportSize({ width: 360, height: 844 });
  const editStep = page.getByRole('button', { name: 'Редактировать шаг «' + draft + '»' });
  await editStep.click();
  const edit = page.getByRole('dialog', { name: 'Редактировать шаг' });
  await edit.getByLabel('Дата шага').fill('2026-11-22');
  await edit.getByRole('button', { name: 'Сохранить' }).click();
  await expect(page.getByRole('link', { name: 'воскресенье, 22 ноября 2026' })).toBeVisible();
  await nav.getByRole('link', { name: 'Календарь', exact: true }).click();
  await expect(page).toHaveURL(/date=2026-11-21/);
  await expect(agenda.getByText('На этот день ничего не запланировано.')).toBeVisible();
  await page.getByRole('button', { name: 'воскресенье, 22 ноября 2026', exact: true }).getByText('22', { exact: true }).click();
  await expect(agenda.getByText('Шаг плана · Выполнен')).toBeVisible();
  await agenda.getByRole('link', { name: title }).click();
  await editStep.click();
  await edit.getByRole('button', { name: 'Снять дату' }).click();
  await edit.getByRole('button', { name: 'Сохранить' }).click();
  await expect(page.getByRole('link', { name: 'воскресенье, 22 ноября 2026' })).toHaveCount(0);
  await page.reload();
  await expect(page.getByRole('checkbox', { name: draft })).toBeChecked();
  await expect(page.getByRole('link', { name: 'воскресенье, 22 ноября 2026' })).toHaveCount(0);
  await nav.getByRole('link', { name: 'Календарь', exact: true }).click();
  await expect(agenda.getByText('На этот день ничего не запланировано.')).toBeVisible();
  await pick.click();
  await expect(dialog.getByRole('button', { name: draft, exact: true })).toHaveCount(0);
  await expect(dialog.getByRole('button', { name: 'Посмотреть ролик целиком', exact: true })).toBeVisible();
});

test('создание плана, первый шаг, правка названия, валидация и удаление материала', async ({ page }) => {
  await page.goto('/plans');
  await page.getByRole('button', { name: 'Новый план' }).click();
  const create = page.getByRole('dialog', { name: 'Новый план' });
  await create.getByRole('textbox', { name: 'Название' }).fill('Пройти маршрут вдоль залива');
  await create.getByRole('textbox', { name: 'Заметка' }).fill('Начать с короткого маршрута.');
  await create.getByRole('button', { name: 'Сохранить' }).click();
  await expect(page.getByRole('heading', { name: 'Пройти маршрут вдоль залива' })).toBeVisible();
  await page.getByRole('link', { name: 'Все планы' }).click();
  const card = page.getByRole('heading', { name: 'Пройти маршрут вдоль залива' }).locator('..');
  await card.getByRole('link', { name: 'Добавить первый шаг' }).click();
  const addStep = page.getByRole('dialog', { name: 'Новый шаг' });
  await addStep.getByRole('textbox', { name: 'Название' }).fill('Проложить маршрт');
  await addStep.getByRole('button', { name: 'Сохранить' }).click();
  await expect(page.getByRole('checkbox', { name: 'Проложить маршрт' })).toBeVisible();
  await page.getByRole('button', { name: 'Редактировать шаг «Проложить маршрт»' }).click();
  const editStep = page.getByRole('dialog', { name: 'Редактировать шаг' });
  await editStep.getByRole('textbox', { name: 'Название' }).fill('Проложить маршрут');
  await editStep.getByRole('button', { name: 'Сохранить' }).click();
  await expect(page.getByRole('checkbox', { name: 'Проложить маршрут' })).toBeVisible();

  await page.getByRole('button', { name: 'Редактировать план' }).click();
  const editPlan = page.getByRole('dialog', { name: 'Редактировать план' });
  await editPlan.getByLabel('Сфера').selectOption('study');
  await editPlan.getByRole('textbox', { name: 'Заметка' }).fill('Проверить доступность маршрута.');
  await editPlan.getByRole('button', { name: 'Сохранить' }).click();
  await expect(page.getByText('Проверить доступность маршрута.')).toBeVisible();

  let requests = 0;
  page.on('request', request => {
    if (request.method() === 'POST' && request.url().endsWith('/resources')) requests += 1;
  });
  await page.getByRole('button', { name: 'Добавить материал' }).click();
  const material = page.getByRole('dialog', { name: 'Добавить материал' });
  await material.getByRole('textbox', { name: 'Название' }).fill('Карта прогулки');
  await material.getByRole('textbox', { name: 'Ссылка' }).fill('javascript:alert(1)');
  await material.getByRole('button', { name: 'Сохранить' }).click();
  await expect(material.getByText('Введите ссылку http:// или https://.')).toBeVisible();
  await expect(material.getByRole('textbox', { name: 'Ссылка' })).toBeFocused();
  await expect(material.getByRole('textbox', { name: 'Название' })).toHaveValue('Карта прогулки');
  expect(requests).toBe(0);
  await material.getByRole('textbox', { name: 'Ссылка' }).fill('https://example.org/map');
  await material.getByRole('button', { name: 'Сохранить' }).click();
  await expect(page.getByRole('link', { name: 'Карта прогулки' })).toHaveAttribute('href', 'https://example.org/map');
  expect(requests).toBe(1);
  await page.reload();
  await expect(page.getByRole('checkbox', { name: 'Проложить маршрут' })).toBeVisible();
  await page.getByRole('button', { name: 'Удалить материал «Карта прогулки»' }).click();
  await expect(page.getByText('Материалов пока нет.')).toBeVisible();
  await page.reload();
  await expect(page.getByText('Материалов пока нет.')).toBeVisible();
});

test('повтор создания и параллельное добавление шагов сохраняют уникальный порядок', async ({ request }) => {
  const plan = { id: 'ordering-integration', title: 'Порядок шагов' };
  const firstPlan = await post(request, '/plans', plan);
  expect(await post(request, '/plans', plan)).toMatchObject({ id: firstPlan.id, motif: firstPlan.motif });
  const destination = '/plans/ordering-integration/steps';
  const [first, second] = await Promise.all([
    post(request, destination, { id: 'ordering-a', title: 'Первое действие' }),
    post(request, destination, { id: 'ordering-b', title: 'Второе действие' }),
  ]);
  expect([first.position, second.position].sort()).toEqual([1, 2]);
  expect(await post(request, destination, { id: 'ordering-b', title: 'Второе действие' })).toMatchObject({ position: second.position });
  const detail = await request.get('/api/plans/ordering-integration');
  expect((await detail.json()).steps).toHaveLength(2);
  const invalid = await request.post('/api/plans/ordering-integration/resources', {
    data: { id: 'ordering-bad-url', title: 'Внешний материал', url: 'file:///document' },
  });
  expect(invalid.status()).toBe(422);
  expect((await invalid.json()).detail[0].loc).toEqual(['body', 'url']);
});

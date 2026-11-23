import { mkdir } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { chromium } from '@playwright/test';
import { expect } from '@playwright/test';

const output = new URL('../evidence/comparison/', import.meta.url);
await mkdir(output, { recursive: true });
const browser = await chromium.launch();
try {
  for (const [name, viewport] of Object.entries({
    desktop: { width: 1440, height: 900 },
    mobile: { width: 390, height: 844 },
  })) {
    const page = await browser.newPage({ viewport });
    await page.goto(new URL('../design/prototype.html', import.meta.url).href);
    const review = page.getByRole('complementary', { name: 'Проверка макета' });
    const agenda = page.getByRole('complementary', { name: 'Повестка' });
    await expect(page.getByRole('heading', { name: 'Ноябрь 2026' })).toBeVisible();
    await expect(agenda.getByText('Поездка в Карелию')).toBeVisible();
    await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth)).toBe(viewport.width);
    const capture = (screen, fullPage = false) => page.screenshot({
      path: fileURLToPath(new URL(screen + '-prototype-' + name + '.png', output)),
      fullPage,
    });
    const view = page.locator('.views');
    await view.getByRole('button', { name: 'Неделя', exact: true }).click();
    await expect(page.getByRole('region', { name: 'Неделя' })).toBeVisible();
    await page.getByRole('button', { name: 'Тёмная тема' }).click();
    await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark');
    await page.getByRole('button', { name: 'Светлая тема' }).click();
    await view.getByRole('button', { name: 'Месяц', exact: true }).click();
    const toggle = page.getByRole('checkbox', { name: 'Учебные пары' });
    await expect(toggle).not.toBeChecked();
    await toggle.check();
    await page.getByRole('button', { name: '3 пары · 27 ноября', exact: true }).click();
    await expect(agenda.getByText('09:00–10:30 · Аудитория 2403')).toBeVisible();
    await expect(agenda.getByText('Поездка в Карелию')).toBeVisible();
    await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth)).toBe(viewport.width);
    await page.getByRole('button', { name: 'Добавить пару' }).click();
    await expect(page.getByRole('dialog').getByRole('textbox', { name: 'Предмет' })).toBeVisible();
    await page.keyboard.press('Escape');
    await toggle.uncheck();
    await page.getByRole('button', { name: '28 ноября', exact: true }).click();
    const navigation = page.getByRole('navigation', { name: 'Разделы' });
    await navigation.getByRole('button', { name: 'Планы' }).click();
    await expect(page.getByRole('heading', { name: 'Собрать список книг' })).toBeVisible();
    await expect(page.getByText('1 из 3')).toBeVisible();
    await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth)).toBe(viewport.width);
    await navigation.getByRole('button', { name: 'Календарь' }).click();
    await page.getByRole('button', { name: 'Следующий месяц' }).click();
    await expect(agenda.getByText('27 ноя — 2 дек · день 5 из 6')).toBeVisible();
    await review.getByRole('button', { name: 'Ошибка', exact: true }).click();
    await expect(page.getByRole('alert')).toBeVisible();
    await expect(page.getByRole('textbox', { name: 'Название' })).toHaveValue('Поездка в Карелию');
    await page.keyboard.press('Escape');
    await review.getByRole('button', { name: 'Пустой день' }).click();
    await agenda.getByRole('button', { name: 'Выбрать шаг из планов' }).click();
    await page.getByRole('button', { name: 'Собрать черновик', exact: true }).click();
    await agenda.getByRole('button', { name: 'Отметить выполненным' }).click();
    await agenda.getByRole('button', { name: 'Снять первый короткий ролик' }).click();
    await expect(page.getByText('2 из 3')).toBeVisible();
    await capture('plan', true);
    await page.goto(new URL('../design/today.html?date=2026-11-20', import.meta.url).href);
    await page.getByRole('checkbox', { name: 'Учебные пары' }).check();
    await expect(page.locator('#hero')).toContainText('2334');
    await expect(page.locator('#notice')).toContainText('10:50–11:20');
    await capture('day');
    await page.close();
    console.log(name, viewport.width + '×' + viewport.height, 'OK');
  }
} finally {
  await browser.close();
}

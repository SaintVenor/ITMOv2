import { expect, test } from '@playwright/test';
import { formatDuration } from '../src/features/calendar/dates';

test('окна дольше часа показывают часы и остаток минут', () => {
  expect([45,60,61,90,120,130].map(formatDuration)).toEqual(['45 мин','60 мин','1 ч 1 мин','1 ч 30 мин','2 ч','2 ч 10 мин']);
});

test('утреннее расписание, пересечение и назначение шага в свободную субботу', async ({page, request}) => {
  const day = '2026-11-20';
  async function add(path: string, data: object) {
    const response = await request.post('/api/' + path, {data});
    expect(response.status(), await response.text()).toBe(201);
  }
  await add('lessons', {id:'flight-ai', subject:'Технологии ИИ в разработке ПО', room:'2334', weekday:5,
    startTime:'09:50', endTime:'11:20', termStart:day, termEnd:day});
  for (const [id,title,startTime,endTime] of [
    ['flight-consult','Консультация','10:50','11:35'], ['flight-edit','Монтаж ролика','13:05','14:00'],
  ]) await add('entries',{id,title,startTime,endTime,kind:'event',startDate:day,endDate:day});
  await add('plans',{id:'flight-video',title:'Короткий ролик'});
  await add('plans/flight-video/steps',{id:'flight-draft',title:'Собрать черновой монтаж'});
  await page.clock.setFixedTime(new Date('2026-11-20T09:12:00'));
  await page.goto('/calendar');
  await expect(page.getByRole('heading',{name:'Сегодня',exact:true})).toBeVisible();
  const toggle=page.getByRole('switch',{name:'Учебные пары'});
  await expect(toggle).not.toBeChecked();
  await expect(page.getByRole('heading',{name:'Консультация'})).toBeVisible();
  const ribbon = page.getByRole('navigation',{name:'Дни недели'});
  await expect(ribbon.getByRole('button')).toHaveCount(7);
  await expect(ribbon.getByRole('button',{pressed:true})).toHaveAccessibleName(/2 дела$/);
  await ribbon.getByRole('button',{name:/суббота.*Свободно/i}).click();
  await expect(page).toHaveURL(/date=2026-11-21/);
  await expect(page.getByRole('region',{name:'Что дальше'})).toContainText('Свободный день');
  await ribbon.getByRole('button',{name:/пятница.*2 дела/i}).click();
  await toggle.check();
  await expect(ribbon.getByRole('button',{pressed:true})).toHaveAccessibleName(/3 дела$/);
  const room=page.getByText('2334',{exact:true});
  await expect(room).toBeVisible();
  await expect(page.getByText(/△ Пересечение 10:50–11:20/)).toBeVisible();
  await expect(page.getByText('Окно · 1 ч 30 мин')).toBeVisible();
  const lesson=page.getByRole('button',{name:/Технологии ИИ/});
  await expect(lesson).toHaveCSS('border-left-width', '1px');
  await expect(lesson).toHaveCSS('box-shadow', 'none');
  const consultation=page.getByRole('button',{name:/Консультация/});
  for (const [width,height] of [[390,844],[1440,900],[360,844]]) {
    await page.setViewportSize({width,height});
    await expect(room).toBeInViewport();
    const a=(await lesson.boundingBox())!, b=(await consultation.boundingBox())!;
    expect(b.x).toBeGreaterThanOrEqual(a.x+a.width-1);
    expect(b.y).toBeGreaterThan(a.y);
    expect(b.y).toBeLessThan(a.y+a.height);
    expect(b.y+b.height).toBeGreaterThan(a.y+a.height);
    expect(await page.evaluate(()=>document.documentElement.scrollWidth)).toBe(width);
    if (process.env.ORBIT_CAPTURE_DAY && width!==360) await page.screenshot({path:'evidence/comparison/day-app-' + (width === 390 ? 'mobile' : 'desktop') + '.png'});
  }
  await page.getByRole('button',{name:'Тёмная тема'}).click();
  await expect(page.locator('html')).toHaveAttribute('data-mantine-color-scheme','dark');
  await page.setViewportSize({width:1440,height:900});
  const card = page.getByRole('region',{name:'Что дальше'});
  const timeline = page.getByRole('heading',{name:/Шкала дня/});
  const tasks = page.getByRole('region',{name:'Без времени'});
  const desktopCard = (await card.boundingBox())!;
  expect(desktopCard.x + desktopCard.width).toBeLessThan((await timeline.boundingBox())!.x);
  expect(desktopCard.y + desktopCard.height).toBeLessThanOrEqual((await tasks.boundingBox())!.y);
  if (process.env.ORBIT_CAPTURE_DAY) await page.screenshot({path:'evidence/comparison/day-dark.png'});
  await page.setViewportSize({width:390,height:844});
  const mobileCard = (await card.boundingBox())!;
  expect(mobileCard.y + mobileCard.height).toBeLessThan((await timeline.boundingBox())!.y);
  if (process.env.ORBIT_CAPTURE_DAY) await page.screenshot({path:'.cache/day-preview/app-next-dark-mobile.png'});
  await page.setViewportSize({width:1440,height:900});
  await page.getByText('Неделя',{exact:true}).click();
  const week=page.getByRole('region',{name:'Неделя'});
  await expect(week.getByRole('button',{name:/Консультация.*Пересечение/})).toBeVisible();
  if (process.env.ORBIT_CAPTURE_DAY) {
    await page.screenshot({path:'.cache/day-preview/flight-week-desktop.png'});
    await page.setViewportSize({width:390,height:844});
    await expect(week.getByRole('button',{name:/Консультация.*Пересечение/})).toBeVisible();
    await page.screenshot({path:'.cache/day-preview/flight-week-mobile.png'});
    await page.setViewportSize({width:1440,height:900});
  }
  expect(await page.evaluate(()=>document.documentElement.scrollWidth)).toBe(1440);
  await page.getByText('День',{exact:true}).click();
  await page.setViewportSize({width:390,height:844});
  await page.clock.setFixedTime(new Date('2026-11-20T10:35:00'));
  await page.reload();
  await toggle.check();
  await expect(card).toContainText('до конца 45 мин');
  await expect(card.getByRole('img',{name:'Прошло 50% события'})).toBeVisible();
  if (process.env.ORBIT_CAPTURE_DAY) await page.screenshot({path:'.cache/day-preview/flight-in-progress.png'});
  await page.clock.setFixedTime(new Date('2026-11-20T21:30:00'));
  await page.reload();
  await expect(page.getByRole('heading',{name:'Всё на сегодня закончилось'})).toBeVisible();
  await page.getByRole('button',{name:'Следующий день'}).click();
  await expect(page.getByRole('heading',{name:'Свободный день'})).toBeVisible();
  if (process.env.ORBIT_CAPTURE_DAY) await page.screenshot({path:'.cache/day-preview/flight-free-day.png'});
  await add('entries',{id:'flight-long',title:'long',kind:'event',startDate:'2026-11-21',endDate:'2026-11-25'});
  await page.reload();
  await expect(card.getByRole('heading',{name:'long'})).toBeVisible();
  await expect(card).toContainText('день 1 из 5');
  await expect(card.getByRole('img',{name:'День 1 из 5'})).toBeVisible();
  await expect(toggle).not.toBeChecked();
  await page.getByRole('region',{name:'Весь день'}).getByRole('button',{name:/long/}).click();
  await expect(page.getByRole('dialog')).toBeVisible();
  await page.keyboard.press('Escape');
  await page.getByRole('button',{name:'Выбрать шаг из планов'}).click();
  const draft = page.getByRole('button',{name:'Собрать черновой монтаж'});
  await expect(draft).toBeVisible();
  if (process.env.ORBIT_CAPTURE_DAY) await page.screenshot({path:'.cache/day-preview/flight-step-picker.png'});
  await draft.click();
  await expect(page.getByRole('dialog')).toHaveCount(0);
  await expect(page.getByRole('status')).toHaveText('Шаг «Собрать черновой монтаж» назначен на 21 ноября.');
  await expect(page.getByRole('article').filter({hasText:'Собрать черновой монтаж'})).toBeFocused();
  await page.reload();
  await expect(page.getByText('Собрать черновой монтаж',{exact:true})).toHaveCount(1);
  const completion = page.getByRole('checkbox',{name:'Выполнить шаг «Собрать черновой монтаж»'});
  await completion.click();
  await expect(completion).toBeChecked();
  await expect(page.getByText('Шаг выполнен.')).toBeVisible();
  await page.getByRole('link',{name:'Короткий ролик'}).click();
  await expect(page.getByRole('checkbox',{name:'Собрать черновой монтаж'})).toBeChecked();
  if (process.env.ORBIT_CAPTURE_DAY) await page.screenshot({path:'.cache/day-preview/flight-plan-completed.png', fullPage:true});

  // Past day with a deadline and several untimed steps, as in the review screenshot.
  const past = '2026-11-19';
  await add('entries',{id:'flight-report',title:'Лабораторная по алгоритмам',kind:'deadline',
    startDate:past,endDate:past,startTime:'18:00'});
  for (const [index,title] of ['Подготовить сценарий','Снять вступление','Выбрать музыку','Записать голос','Проверить субтитры'].entries()) {
    await add('plans/flight-video/steps',{id:'flight-row-'+index,title,scheduledDate:past});
  }
  await page.goto('/calendar?date='+past+'&view=day');
  const list=page.getByRole('region',{name:'Без времени'});
  await expect(list.getByRole('article')).toHaveCount(5);
  await expect(page.getByText('Подготовить сценарий',{exact:true})).toHaveCount(1);
  await expect(page.getByRole('heading',{name:'Расписание на день завершено'})).toBeVisible();
  await expect(page.getByRole('button',{name:/Лабораторная по алгоритмам/})).toBeVisible();
  for (const [width,height] of [[1440,900],[390,844]]) {
    await page.setViewportSize({width,height});
    expect(await page.evaluate(()=>document.documentElement.scrollWidth)).toBe(width);
    if(process.env.ORBIT_CAPTURE_DAY) await page.screenshot({path:'.cache/day-preview/day-tasks-dark-'+width+'.png'});
  }
});

test.afterEach(async ({request}, testInfo) => {
  if (!testInfo.title.startsWith('утреннее расписание')) return;
  for (const path of ['plans/flight-video','entries/flight-consult','entries/flight-edit','entries/flight-report','entries/flight-long','lessons/flight-ai']) {
    const response = await request.delete('/api/' + path);
    expect([204,404]).toContain(response.status());
  }
});

test('четыре пересекающихся события дают одну сводку и помещаются на телефоне', async ({ page }) => {
  const day = '2026-11-20';
  await page.route('**/api/calendar?*', route => route.fulfill({ json: {
    items: Array.from({ length: 4 }, (_, index) => ({
      id: String(index), title: 'Событие ' + (index + 1), kind: 'event', area: 'study',
      startDate: day, endDate: day, startTime: '09:00', endTime: index === 0 ? '12:00' : '11:00',
    })),
  } }));
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/calendar?date=' + day + '&view=day');
  await expect(page.getByText(/△ Пересечение/)).toHaveCount(1);
  await expect(page.getByText('△ Пересечение 09:00–11:00')).toBeVisible();
  const cards = page.getByRole('button', { name: /Событие [1-4]/ });
  await expect(cards).toHaveCount(4);
  const first = (await cards.first().boundingBox())!;
  const second = (await cards.nth(1).boundingBox())!;
  expect(second.y).toBeGreaterThanOrEqual(first.y + first.height);
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBe(390);
  await page.setViewportSize({ width: 1440, height: 900 });
  await expect(page.getByText('11:00', { exact: true })).toBeVisible();
  await expect(page.getByText('12:00', { exact: true })).toBeVisible();
  if (process.env.ORBIT_CAPTURE_DAY) {
    await page.screenshot({ path: '.cache/day-preview/day-overlaps-light.png' });
    await page.getByRole('button', { name: 'Тёмная тема' }).click();
    await page.screenshot({ path: '.cache/day-preview/day-overlaps-dark.png' });
  }
});

import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

test('welcome is local, accessible and responsive', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByRole('heading', { name: /Understand a mix/ })).toBeVisible();
  await expect(page.locator('.hero-image img')).toBeVisible();
  const audit = await new AxeBuilder({ page }).analyze();
  expect(audit.violations.filter(v => ['critical', 'serious'].includes(v.impact || ''))).toEqual([]);
  for (const width of [1440, 1280, 768, 390]) {
    await page.setViewportSize({ width, height: 900 });
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    await page.screenshot({ path: `test-results/welcome-${test.info().project.name}-${width}.png`, fullPage: true });
  }
});

test('wheel scrolls the page over controls without changing values', async ({ page }) => {
  await page.goto('/#evaluate');
  const field = page.getByRole('textbox', { name: /Cement/ }).first();
  await field.scrollIntoViewIfNeeded(); await field.fill('365');
  const value = await field.inputValue(); await field.hover();
  const before = await page.evaluate(() => scrollY);
  await page.mouse.wheel(0, 160); await page.waitForTimeout(180);
  expect(await field.inputValue()).toBe(value);
  expect(await page.evaluate(() => scrollY)).toBeGreaterThan(before);
  await page.getByRole('checkbox', { name: 'Air entrained', exact: true }).scrollIntoViewIfNeeded();
  await page.getByRole('checkbox', { name: 'Air entrained', exact: true }).hover();
  const checkBefore = await page.evaluate(() => scrollY);
  await page.mouse.wheel(0, 120); await page.waitForTimeout(180);
  expect(await page.evaluate(() => scrollY)).toBeGreaterThan(checkBefore);
  const select = page.getByRole('button', { name: /Aggregate.*basis/ });
  await select.scrollIntoViewIfNeeded(); await select.click();
  await expect(page.getByRole('listbox')).toBeVisible();
  expect(await page.evaluate(() => getComputedStyle(document.documentElement).overflow)).not.toBe('hidden');
  await page.keyboard.press('Escape'); await expect(page.getByRole('listbox')).toHaveCount(0);
});

test('evaluation is explicit and exports the calculated snapshot after edits', async ({ page }) => {
  let calculations=0;
  page.on('request',request=>{if(request.url().endsWith('/api/v1/predict')) calculations++;});
  await page.goto('/#evaluate');
  await page.getByRole('textbox',{name:/Cement content/}).fill('365');
  expect(calculations).toBe(0);
  await page.getByRole('button',{name:'Run analysis',exact:true}).click();
  await expect(page.getByRole('heading',{name:'A clearer picture of your mix.'})).toBeVisible();
  expect(calculations).toBe(1);
  await expect(page.getByRole('heading',{name:'Four perspectives on strength'})).toBeVisible();
  await page.getByRole('button',{name:'Edit inputs'}).click();
  await page.getByRole('textbox',{name:/Cement content/}).fill('390');
  await page.getByRole('button',{name:/View last report/}).click();
  await expect(page.getByRole('status')).toContainText('Inputs changed');
  const downloadEvent=page.waitForEvent('download');
  await page.getByRole('button',{name:'JSON · SI',exact:true}).click();
  const file=await (await downloadEvent).path();
  const {readFile}=await import('node:fs/promises');
  const snapshot=JSON.parse(await readFile(file!,'utf8'));
  expect(snapshot.inputs.cement.weight_kg).toBe(365);
  expect(snapshot.data.report.inputs.cement.weight_kg).toBe(365);
  expect(calculations).toBe(1);
  await page.screenshot({path:`test-results/evaluation-${test.info().project.name}.png`,fullPage:true});
});

test('SI US switch preserves submitted physical quantities',async({page})=>{
  await page.goto('/#evaluate');
  await page.getByRole('textbox',{name:/Cement content/}).fill('400');
  await page.getByRole('button',{name:/Input units/}).click();
  await page.getByRole('option',{name:'US · customary'}).click();
  const responseEvent=page.waitForResponse(response=>response.url().endsWith('/api/v1/predict'));
  await page.getByRole('button',{name:'Run analysis',exact:true}).click();
  const response=await responseEvent;
  expect((await response.json()).report.cement_kg_m3).toBeCloseTo(400,10);
  await expect(page.getByRole('heading',{name:'A clearer picture of your mix.'})).toBeVisible();
});

test('design steps and named comparison snapshots retain calculated values',async({page})=>{
  await page.goto('/#design');
  await page.getByRole('button',{name:'Run analysis',exact:true}).click();
  await expect(page.getByRole('heading',{name:'A clearer picture of your mix.'})).toBeVisible();
  await page.getByRole('tab',{name:'Design steps',exact:true}).click();
  await expect(page.getByText('What governed this design?',{exact:true})).toBeVisible();
  await expect(page.getByText(/Other convention:/)).toBeVisible();
  page.once('dialog',dialog=>dialog.accept('First design'));
  await page.getByRole('button',{name:'Save for comparison',exact:true}).click();
  await page.getByRole('button',{name:'Edit inputs'}).click();
  await page.getByRole('textbox',{name:/Specified strength/}).fill('30');
  await page.getByRole('button',{name:'Run analysis',exact:true}).click();
  await expect(page.getByRole('heading',{name:'A clearer picture of your mix.'})).toBeVisible();
  page.once('dialog',dialog=>dialog.accept('Second design'));
  await page.getByRole('button',{name:'Save for comparison',exact:true}).click();
  await page.getByRole('link',{name:'Compare snapshots',exact:true}).click();
  await expect(page.getByRole('heading',{name:'Compare, with the context intact.'})).toBeVisible();
  await expect(page.getByRole('heading',{name:'First design',exact:true})).toBeVisible();
  await expect(page.getByRole('heading',{name:'Second design',exact:true})).toBeVisible();
  await expect(page.getByRole('heading',{name:'What changed between these mixes?'})).toBeVisible();
  const shots=await page.evaluate(()=>JSON.parse(sessionStorage.getItem('crs.compare.v1')||'[]'));
  expect(shots).toHaveLength(2);
  expect(shots[0].inputs.specified_fc_mpa).toBe(25);
  expect(shots[1].inputs.specified_fc_mpa).toBe(30);
});

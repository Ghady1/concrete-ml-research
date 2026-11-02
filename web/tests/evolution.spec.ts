import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

test('material influence and engineering explanations remain accessible', async ({ page }) => {
  await page.goto('/#evaluate');
  await expect(page.getByRole('textbox', { name: 'Cement name', exact: true })).toHaveAccessibleDescription(/Record only/);
  await expect(page.getByRole('textbox', { name: /Strength class/ })).toHaveAttribute('placeholder', /certificate/);
  await page.getByRole('checkbox', { name: 'Enter actual batch weights' }).check();
  await expect(page.getByRole('textbox', { name: /Intended batch yield/ })).toHaveAccessibleDescription(/does not remove sand/);
  await page.getByRole('button', { name: 'Run analysis', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Calculated, with assumptions.' })).toBeVisible();
  await expect(page.getByText('Workability method', { exact: true })).toBeVisible();
  await page.getByText('Show the engineering', { exact: true }).click();
  await expect(page.getByRole('heading', { name: '02 · Follow effective water' })).toBeVisible();
  const audit = await new AxeBuilder({ page }).analyze();
  expect(audit.violations.filter(v => ['critical', 'serious'].includes(v.impact || ''))).toEqual([]);
  for (const width of [1440, 768, 390]) {
    await page.setViewportSize({ width, height: 1000 });
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  }
  await page.getByRole('button', { name: 'Edit inputs' }).click();
  await page.getByRole('textbox', { name: /Cement content/ }).fill('-');
  await page.getByRole('button', { name: /View last report/ }).click();
  await expect(page.getByRole('status')).toContainText('Inputs changed');
});

test('research pages provide working examples methods and visible attribution', async ({ page }) => {
  for (const route of ['methods', 'examples', 'credits']) {
    await page.goto('/#' + route);
    await expect(page.locator('main h1')).toBeVisible();
    await expect(page.getByText(/next workspace is being connected/)).toHaveCount(0);
    const audit = await new AxeBuilder({ page }).analyze();
    expect(audit.violations.filter(v => ['critical', 'serious'].includes(v.impact || ''))).toEqual([]);
    for (const width of [1440, 1280, 768, 390]) {
      await page.setViewportSize({ width, height: 1000 });
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    }
  }
  await expect(page.getByRole('link', { name: /CC BY 3.0/ })).toHaveAttribute('href', 'https://creativecommons.org/licenses/by/3.0/');
  await page.goto('/#examples');
  await page.getByRole('button', { name: 'Load evaluation example →', exact: true }).nth(1).click();
  await expect(page.getByRole('textbox', { name: /Fine total moisture/ })).toHaveValue('5');
  await page.getByRole('button', { name: 'Run analysis', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Research limitations', exact: false })).toBeVisible();
  await page.getByText('Calculated input snapshot · canonical SI', { exact: true }).click();
  await expect(page.getByText('These are the submitted quantities', { exact: false })).toBeVisible();
});

test('figures export real SVG PNG and full precision data', async ({ page }) => {
  await page.goto('/#evaluate');
  await page.getByRole('button', { name: 'Run analysis', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Four perspectives on strength' })).toBeVisible();
  const { readFile } = await import('node:fs/promises');
  for (const [name, extension] of [['SVG image', '.svg'], ['PNG', '.png'], ['CSV data', '.csv']]) {
    const pending = page.waitForEvent('download');
    await page.getByRole('button', { name: 'Download Four perspectives on strength ' + name, exact: true }).click();
    const file = await pending;
    expect(file.suggestedFilename().endsWith(extension)).toBe(true);
    const bytes = await readFile((await file.path())!);
    expect(bytes.length).toBeGreaterThan(100);
    if (extension === '.svg') expect(bytes.toString()).toContain('Model disagreement is not a confidence interval.');
    if (extension === '.png') expect(bytes.subarray(1, 4).toString()).toBe('PNG');
    if (extension === '.csv') expect(bytes.toString()).toContain('mean (MPa)');
  }
  await page.getByRole('tab', { name: 'Strength', exact: true }).click();
  await expect(page.getByText(/Shading is outside table coverage/)).toBeVisible();
});


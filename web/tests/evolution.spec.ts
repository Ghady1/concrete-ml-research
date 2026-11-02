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

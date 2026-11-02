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
  const select = page.getByRole('button', { name: /Aggregate basis/ });
  await select.scrollIntoViewIfNeeded(); await select.click();
  await expect(page.getByRole('listbox')).toBeVisible();
  expect(await page.evaluate(() => getComputedStyle(document.documentElement).overflow)).not.toBe('hidden');
  await page.keyboard.press('Escape'); await expect(page.getByRole('listbox')).toHaveCount(0);
});

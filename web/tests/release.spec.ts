import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

test('complete demonstration needs only loopback and exports its calculated report', async ({ page }) => {
  const remote: string[] = [];
  await page.route('**/*', route => {
    if (['127.0.0.1', 'localhost'].includes(new URL(route.request().url()).hostname)) return route.continue();
    remote.push(route.request().url()); return route.abort();
  });
  const start = Date.now();
  await page.goto('/');
  await expect(page.getByRole('heading', { name: /Understand a mix/ })).toBeVisible();
  // A generous test ceiling avoids conflating cold CI browser startup with the demo target.
  expect(Date.now() - start).toBeLessThan(10000);
  await page.getByRole('link', { name: 'Examples', exact: true }).click();
  await page.getByRole('button', { name: 'Load course design →', exact: true }).first().click();
  await page.getByRole('button', { name: 'Run analysis', exact: true }).click();
  await page.getByRole('tab', { name: 'Design steps', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Design constraints, made visible' })).toBeVisible();
  await page.evaluate(() => { window.print = () => {}; });
  await page.getByRole('button', { name: 'Print / PDF', exact: true }).click();
  await expect(page.getByText(/Print layout prepared/)).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Follow the water' })).toBeVisible();
  await page.getByRole('button', { name: 'Return to tab view' }).click();
  await page.getByRole('link', { name: 'Calibrate', exact: true }).click();
  await page.getByRole('button', { name: /Explore the 12-row synthetic demo/ }).click();
  await page.getByRole('button', { name: 'Fit three strength models', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Inspect the residuals', exact: true })).toBeVisible();
  expect(remote).toEqual([]);
});

test('workspaces and result tabs remain accessible and fit all demonstration widths', async ({ page }) => {
  test.setTimeout(90000);
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await page.goto('/#evaluate');
  await expect(page.locator('.material-companion')).toHaveCount(4);
  expect(await page.locator('.companion-body').first().evaluate(element => getComputedStyle(element).animationName)).toBe('none');
  await page.getByRole('button', { name: 'Run analysis', exact: true }).click();
  await page.getByRole('tab', { name: 'Overview', exact: true }).focus();
  await page.keyboard.press('ArrowRight');
  await expect(page.getByRole('tab', { name: 'Strength', exact: true })).toBeFocused();
  await expect(page.getByRole('tab', { name: 'Strength', exact: true })).toHaveAttribute('aria-selected', 'true');
  for (const width of [1440, 1280, 768, 390]) {
    await page.setViewportSize({ width, height: 1000 });
    await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  }
  const audit = await new AxeBuilder({ page }).analyze();
  expect(audit.violations.filter(item => ['critical', 'serious'].includes(item.impact || ''))).toEqual([]);
});

test('late exploratory responses cannot replace a newer hypothetical mix', async ({ page }) => {
  let release = () => {};
  const gate = new Promise<void>(resolve => { release = resolve; });
  await page.route('**/api/v1/predict', async route => {
    const data = route.request().postDataJSON();
    const response = await route.fetch();
    if (data.inputs.water_kg === 210) await gate;
    try { await route.fulfill({ response }); } catch { /* The old request is deliberately cancelled. */ }
  });
  await page.goto('/#evaluate');
  await page.getByRole('button', { name: 'Run analysis', exact: true }).click();
  await page.getByRole('button', { name: 'Open Mix Explorer' }).click();
  const field = page.locator('.mix-explorer').getByRole('textbox', { name: /Added water/ });
  const old = page.waitForRequest(request => request.url().endsWith('/predict') && request.postDataJSON().inputs.water_kg === 210);
  await field.fill('210'); await old;
  const next = page.waitForResponse(response => response.url().endsWith('/predict') && response.request().postDataJSON().inputs.water_kg === 220);
  await field.fill('220'); await next;
  await expect(page.getByRole('button', { name: /Use hypothetical as new evaluation draft/ })).toBeVisible();
  release();
  await page.getByRole('button', { name: /Use hypothetical as new evaluation draft/ }).click();
  await expect(page.getByRole('textbox', { name: /Added water/ })).toHaveValue('220');
});

test('a failed view chunk keeps a recoverable interface', async ({ page }) => {
  await page.route('**/assets/research-pages-*.js', route => route.abort());
  await page.goto('/#examples');
  await expect(page.getByRole('alert')).toContainText('This view could not be opened.');
  await expect(page.getByRole('button', { name: 'Reload the studio' })).toBeVisible();
  await expect(page.getByRole('navigation', { name: 'Main navigation' })).toBeVisible();
});

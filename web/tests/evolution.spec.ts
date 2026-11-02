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

test('Mix Explorer isolates hypothetical inputs and adopts only on request', async ({ page }) => {
  await page.goto('/#evaluate');
  await page.getByRole('button', { name: 'Run analysis', exact: true }).click();
  await page.getByRole('button', { name: 'Open Mix Explorer' }).click();
  const explorer = page.locator('.mix-explorer');
  await expect(explorer.getByRole('heading', { name: 'Change one thing. See what follows.' })).toBeVisible();
  const response = page.waitForResponse(async response => response.url().endsWith('/api/v1/predict') && response.request().postDataJSON()?.inputs.water_kg === 215);
  await explorer.getByRole('textbox', { name: /Added water/ }).fill('215');
  await response;
  await expect(explorer.getByRole('button', { name: /Use hypothetical as new evaluation draft/ })).toBeVisible();
  const pending = page.waitForEvent('download');
  await page.getByRole('button', { name: 'JSON · SI', exact: true }).click();
  const { readFile } = await import('node:fs/promises');
  const baseline = JSON.parse(await readFile((await (await pending).path())!, 'utf8'));
  expect(baseline.inputs.water_kg).toBe(200);
  await explorer.getByRole('button', { name: /Use hypothetical as new evaluation draft/ }).click();
  await expect(page.getByRole('textbox', { name: /Added water/ })).toHaveValue('215');
  await expect(page.getByRole('textbox', { name: /Cement content/ })).toHaveValue('315');
  await page.getByRole('button', { name: /View last report/ }).click();
  await expect(page.getByRole('status')).toContainText('Inputs changed');
});

test('notebook renames duplicates undoes removals and imports recorded versions', async ({ page }) => {
  await page.goto('/#evaluate');
  await page.getByRole('button', { name: 'Run analysis', exact: true }).click();
  page.once('dialog', dialog => dialog.accept('Baseline'));
  await page.getByRole('button', { name: 'Save for comparison', exact: true }).click();
  await page.getByRole('link', { name: 'Compare snapshots', exact: true }).click();
  page.once('dialog', dialog => dialog.accept('Reference mix'));
  await page.getByRole('button', { name: 'Rename 1', exact: true }).click();
  await page.getByRole('button', { name: 'Duplicate 1', exact: true }).click();
  await expect(page.locator('.notebook-card')).toHaveCount(2);
  await page.getByRole('button', { name: 'Remove Reference mix (copy)', exact: true }).click();
  await expect(page.locator('.notebook-card')).toHaveCount(1);
  await page.getByRole('button', { name: 'Undo removal' }).click();
  await expect(page.locator('.notebook-card')).toHaveCount(2);
  await page.getByRole('checkbox', { name: 'Remember this notebook on this device' }).check();
  const pending = page.waitForEvent('download');
  await page.getByRole('button', { name: 'Export notebook JSON' }).click();
  const { readFile } = await import('node:fs/promises');
  const buffer = await readFile((await (await pending).path())!);
  const notebook = JSON.parse(buffer.toString());
  expect(notebook.version).toBe(2);
  expect(notebook.items[0].data.provenance.engine_sha256).toHaveLength(64);
  const fresh = await page.context().newPage();
  await fresh.goto('/#compare');
  await expect(fresh.getByRole('heading', { name: 'Reference mix', exact: true })).toBeVisible();
  await fresh.close();
  page.once('dialog', dialog => dialog.accept());
  await page.getByLabel('Import notebook JSON').setInputFiles({ name: 'notebook.json', mimeType: 'application/json', buffer });
  await expect(page.locator('.notebook-card')).toHaveCount(2);
  await page.getByLabel('Import notebook JSON').setInputFiles({ name: 'bad.json', mimeType: 'application/json', buffer: Buffer.from('{"version":2,"items":[{}]}') });
  await expect(page.getByRole('alert')).toContainText('invalid');
  await expect(page.locator('.notebook-card')).toHaveCount(2);
});

test('calibration distinguishes grouped holdout and selected-model fits', async ({ page }) => {
  await page.goto('/#calibration');
  await page.getByRole('button', { name: /Explore the 12-row synthetic demo/ }).click();
  await expect(page.getByText(/12 valid rows/)).toBeVisible();
  await page.getByRole('button', { name: /Validation approach/ }).click();
  await page.getByRole('option', { name: /Internal grouped holdout/ }).click();
  await page.getByRole('checkbox', { name: 'Fit bolomey', exact: true }).uncheck();
  await page.getByRole('checkbox', { name: 'Fit feret', exact: true }).uncheck();
  await page.getByRole('button', { name: 'Fit selected models', exact: true }).click();
  await expect(page.getByText(/Internal grouped holdout: fit only/)).toBeVisible();
  await expect(page.getByRole('columnheader', { name: 'MAE (MPa)', exact: true })).toBeVisible();
  await expect(page.getByText(/Held-out mixes · 28-day/)).toBeVisible();
  await page.getByRole('button', { name: /Diagnostic observations/ }).click();
  await page.getByRole('option', { name: 'Calibration rows · in sample', exact: true }).click();
  await expect(page.getByText(/In-sample calibration · 28-day/)).toBeVisible();
  await page.getByRole('checkbox', { name: 'Fit feret', exact: true }).check();
  await expect(page.getByRole('button', { name: 'Save material-set fits' })).toHaveCount(0);
});

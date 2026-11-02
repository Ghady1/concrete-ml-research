import type { Snapshot } from './workbench';

const key = 'crs.notebook.v2';
const preference = 'crs.notebook.remember';
export const remembering = () => { try { return localStorage.getItem(preference) === 'yes'; } catch { return false; } };
export function getSnapshots(): Snapshot[] {
    const raw = (remembering() ? localStorage.getItem(key) : null) || sessionStorage.getItem(key);
    if (raw) return parseArchive(raw);
    const legacy = JSON.parse(sessionStorage.getItem('crs.compare.v1') || '[]');
    return parseArchive(JSON.stringify({ version: 2, items: legacy }));
}
export function putSnapshots(items: Snapshot[]) {
  const raw = JSON.stringify({ version: 2, items });
  sessionStorage.setItem(key, raw);
  // Keep the original session reader compatible during migration.
  sessionStorage.setItem('crs.compare.v1', JSON.stringify(items));
  if (remembering()) localStorage.setItem(key, raw);
}
export function setRemember(yes: boolean, items: Snapshot[]) {
  if (yes) { localStorage.setItem(key, JSON.stringify({ version: 2, items })); localStorage.setItem(preference, 'yes'); }
  else { localStorage.removeItem(key); localStorage.removeItem(preference); }
  putSnapshots(items);
}
export function archive(items: Snapshot[]) { return JSON.stringify({ version: 2, items }, null, 2); }

export function parseArchive(raw: string): Snapshot[] {
  const data = JSON.parse(raw);
  if (data?.version !== 2 || !Array.isArray(data.items) || data.items.length > 3) throw new Error('Import a version 2 notebook with at most three snapshots.');
  const ids = new Set<string>();
  const finite = (value: unknown) => typeof value === 'number' && Number.isFinite(value);
  for (const item of data.items) {
    const report = item?.mode === 'design' ? item?.data?.prediction : item?.data?.report;
    if (!item || !['evaluate', 'design'].includes(item.mode) || typeof item.id !== 'string' || ids.has(item.id) || typeof item.name !== 'string' || item.name.length > 120 || !Number.isFinite(Date.parse(item.at)) || !item.inputs || !item.options || !report || !report.inputs?.cement || !finite(report.wc) || !finite(report.wcm) || !finite(report.volumes?.closure_error_m3) || !finite(report.volumes?.total_m3) || !finite(report.unit_weight?.computed_kg_m3) || !report.water || !finite(report.water.effective_water_kg) || !report.slump || !Array.isArray(report.flags)) throw new Error('The notebook contains an incomplete or invalid calculated snapshot.');
    for (const model of ['aci_table', 'abrams', 'bolomey', 'feret']) {
      const prediction = report.predictions?.[model];
      if (!prediction || (prediction.mean_28d_mpa !== null && !finite(prediction.mean_28d_mpa)) || !prediction.constants_used || typeof prediction.constants_source !== 'string') throw new Error('A snapshot has invalid model results.');
    }
    ids.add(item.id);
  }
  return data.items as Snapshot[];
}

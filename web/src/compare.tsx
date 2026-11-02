import { useState } from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { Chart, reportOf } from './results';
import { PageHeading, Select, TextField, Toggle } from './components';
import { flatten, type Unit } from './form';
import { fmt, pretty, download, type Metadata, type Report } from './api';
import { tableCSV } from './chart-export';
import { getSnapshots, putSnapshots, remembering, setRemember, archive, parseArchive } from './snapshot-store';
import type { Snapshot } from './workbench';

export default function Compare({ metadata }: { metadata: Metadata }) {
  const [loaded] = useState(() => { try { return { items: getSnapshots(), error: '' }; } catch { return { items: [] as Snapshot[], error: 'The stored notebook could not be read. It has not been overwritten. Import a valid notebook or export individual reports.' }; } });
  const [items, setItems] = useState<Snapshot[]>(loaded.items), [message, setMessage] = useState(loaded.error);
  const [unit, setUnit] = useState<Unit>('SI'), [reference, setReference] = useState(loaded.items[0]?.id || '');
  const [remember, updateRemember] = useState(() => { try { return remembering(); } catch { return false; } });
  const [removed, setRemoved] = useState<Snapshot | null>(null);
  function commit(next: Snapshot[]) {
    try { putSnapshots(next); setItems(next); if (!next.some(item => item.id === reference)) setReference(next[0]?.id || ''); setMessage(''); }
    catch { setMessage('Storage is unavailable or full. Export your notebook before closing this page.'); }
  }
  function rename(item: Snapshot) {
    const name = prompt('Rename this snapshot', item.name)?.trim(); if (!name) return;
    if (name.length > 120) { setMessage('Use a name of at most 120 characters.'); return; }
    commit(items.map(value => value.id === item.id ? { ...value, name } : value));
  }
  async function importNotebook(file: File) {
    try {
      if (file.size > 5 * 1024 * 1024) throw new Error('Notebook exceeds the 5 MiB limit.');
      const next = parseArchive(await file.text());
      if (items.length && !confirm('Replace the current notebook? Export it first if you need a backup.')) return;
      commit(next); setRemoved(null);
    } catch (error) { setMessage(error instanceof Error ? error.message : 'Notebook import failed. Existing snapshots are unchanged.'); }
  }
  const stress = (value: number) => value / (unit === 'US' ? metadata.conversion_factors.MPA_PER_PSI : 1);
  const length = (value: number) => value / (unit === 'US' ? metadata.conversion_factors.MM_PER_IN : 1);
  const ref = items.find(item => item.id === reference) || items[0];
  const refReport = ref ? reportOf(ref)! : null;
  const labels = items.map((item, i) => `${i + 1}. ${item.name}`);
  const rows = ['aci_table', 'abrams', 'bolomey', 'feret'].map(model => ({ model: pretty(model), ...Object.fromEntries(items.map((item, i) => [labels[i], reportOf(item)?.predictions[model].mean_28d_mpa == null ? null : stress(reportOf(item)!.predictions[model].mean_28d_mpa!)])) }));
  const quantities: { label: string; value: (report: Report) => number | null }[] = [
    { label: 'Effective w/c', value: report => report.wc },
    { label: `Effective water (${unit === 'SI' ? 'kg/m³' : 'lb/yd³'})`, value: report => report.water.effective_water_kg / (unit === 'US' ? metadata.conversion_factors.KG_M3_PER_LB_YD3 : 1) },
    { label: 'Volume total (m³/m³)', value: report => report.volumes.total_m3 },
    { label: 'Signed volume discrepancy (m³/m³)', value: report => report.volumes.closure_error_m3 },
    { label: `Heuristic water-table equivalent (${unit === 'SI' ? 'mm' : 'in'})`, value: report => report.flags.some(flag => flag.code === 'SLUMP_IGNORES_ADMIXTURES') || report.slump.slump_mm == null ? null : length(report.slump.slump_mm) },
    ...['aci_table', 'abrams', 'bolomey', 'feret'].map(model => ({ label: `${pretty(model)} mean (${unit === 'SI' ? 'MPa' : 'psi'})`, value: (report: Report) => report.predictions[model].mean_28d_mpa == null ? null : stress(report.predictions[model].mean_28d_mpa!) })),
  ];
  const summary = quantities.map(quantity => ({ quantity: quantity.label, ...Object.fromEntries(items.map((item, i) => [labels[i], quantity.value(reportOf(item)!)])) }));
  const normalized = items.map(item => {
    const report = reportOf(item)!;
    return flatten({ quantities_per_m3: { ...report.inputs, cement: { ...report.inputs.cement, weight_kg: report.cement_kg_m3 }, water_kg: report.water_added_kg_m3, coarse_kg: report.coarse_entered_kg_m3, fine_kg: report.fine_entered_kg_m3, batch_volume_m3: null, scm: report.inputs.scm?.map(binder => ({ ...binder, weight_kg: binder.weight_kg * report.per_m3_scale })) }, declared_batch_volume_m3: report.inputs.batch_volume_m3, design_settings: item.mode === 'design' ? item.inputs : null, analysis_options: item.options });
  });
  const keys = Array.from(new Set(normalized.flatMap(item => Object.keys(item)))).filter(key => normalized.some(item => JSON.stringify(item[key]) !== JSON.stringify(normalized[0]?.[key])));
  return <><PageHeading eyebrow="Research notebook" title="Compare, with the context intact.">Three frozen analyses, their assumptions and the differences that matter. Higher predicted strength does not automatically mean a better mixture.</PageHeading>
    <div className="notebook-toolbar"><Toggle label="Remember this notebook on this device" checked={remember} onChange={yes => { try { setRemember(yes, items); updateRemember(yes); } catch { setMessage('Persistent storage is unavailable. Session snapshots remain available.'); } }} help="Opt in for local browser storage. Uploaded lab files are never included. Otherwise snapshots last for this browser session."/><div className="actions compact"><button className="button small" onClick={() => download('research-notebook-v2.json', archive(items))}>Export notebook JSON</button><label className="button small">Import notebook<input className="file-control" aria-label="Import notebook JSON" type="file" accept=".json" onChange={event => { const file = event.target.files?.[0]; if (file) importNotebook(file); event.target.value = ''; }}/></label></div></div>
    {message && <p className="notice error" role="alert">{message}</p>}{removed && <p role="status">Removed {removed.name}. <button className="text-link bare" disabled={items.length >= 3} onClick={() => { commit([...items, removed]); setRemoved(null); }}>Undo removal</button></p>}
    {!items.length ? <div className="empty-state"><h2>Begin with a calculated mix.</h2><p>Run an evaluation or design, then choose “Save for comparison” on its report.</p><a className="button primary" href="#evaluate">Evaluate a mix →</a></div> : <>
      <div className="snapshot-list">{items.map((item, i) => <article className="notebook-card" key={item.id}><span className="eyebrow">{item.mode} · calculated snapshot</span><h3>{item.name}</h3><small>{new Date(item.at).toLocaleString()}</small><p>w/c {fmt(reportOf(item)!.wc, 4)} · {reportOf(item)!.flags.length} notices</p><TextField label={'Description for snapshot ' + (i + 1)} value={item.description || ''} onChange={description => commit(items.map(value => value.id === item.id ? { ...value, description: description.slice(0, 1000) } : value))} optional/><div className="actions compact"><button className="button small" onClick={() => rename(item)}>Rename {i + 1}</button><button className="button small" disabled={items.length >= 3} onClick={() => commit([...items, { ...structuredClone(item), id: crypto.randomUUID(), name: item.name.slice(0, 110) + ' (copy)' }])}>Duplicate {i + 1}</button><button className="button small" onClick={() => { setRemoved(item); commit(items.filter(value => value.id !== item.id)); }}>Remove {item.name}</button></div><details className="source-row"><summary>Version and parameter record</summary><p>{item.data.provenance ? `Studio ${item.data.provenance.application_version}; engine ${item.data.provenance.engine_package_version}; Python ${item.data.provenance.python_version}` : 'Legacy snapshot: code/table version fingerprints were not recorded.'}</p><pre>{JSON.stringify(item.data.provenance || {}, null, 2)}</pre><p>{item.options.calibration_id || 'Uncalibrated defaults'}. Exact constants, source strings and flags remain in the exported snapshot. Keep the matching software checkout for an exact rerun.</p></details></article>)}</div>
      <div className="work-toolbar"><Select label="Reference mixture" value={ref?.id || ''} options={items.map(item => ({ value: item.id, label: item.name }))} onChange={setReference}/><Select label="Comparison units" value={unit} options={['SI', 'US'].map(value => ({ value, label: value }))} onChange={value => setUnit(value as Unit)}/><button className="button small" onClick={() => download('mix-comparison.csv', tableCSV(summary), 'text/csv')}>Export comparison CSV</button></div>
      <Chart title="Strength across snapshots" note={`Estimated 28-day means (${unit === 'SI' ? 'MPa' : 'psi'}). These are different scenarios, not an accuracy ranking.`} rows={rows}><ResponsiveContainer width="100%" height="100%"><BarChart data={rows}><CartesianGrid stroke="#e6e8df" vertical={false}/><XAxis dataKey="model"/><YAxis/><Tooltip/><Legend/>{items.map((item, i) => <Bar isAnimationActive={false} key={item.id} dataKey={labels[i]} fill={['#2a6257', '#a45436', '#596f89'][i]}/>)}</BarChart></ResponsiveContainer></Chart>
      <h2 className="spaced-heading">Differences from {ref?.name}</h2><p className="caption">Each cell shows value, signed difference and percentage of the absolute reference value. Percentage is unavailable for a zero reference. Workability remains heuristic.</p><div className="table-scroll" tabIndex={0} role="region" aria-label="Scrollable numerical table"><table><thead><tr><th>Calculated quantity</th>{items.map(item => <th key={item.id}>{item.name}</th>)}</tr></thead><tbody>{quantities.map(quantity => {
        const referenceValue = refReport ? quantity.value(refReport) : null;
        return <tr key={quantity.label}><th>{quantity.label}</th>{items.map(item => { const value = quantity.value(reportOf(item)!); return <td key={item.id}>{fmt(value, 5)}{value != null && referenceValue != null && item.id !== ref?.id && <small className="difference">Δ {fmt(value - referenceValue, 5)} · {referenceValue === 0 ? 'percentage unavailable' : fmt(100 * (value - referenceValue) / Math.abs(referenceValue)) + '%'}</small>}</td>; })}</tr>;
      })}</tbody></table></div>
      <h2 className="spaced-heading">What changed in the inputs?</h2><p className="caption">Only differences are listed. Quantity contents are normalized kg/m³ with the declared aggregate basis. Original batch volume, design settings and analysis options are retained separately.</p><div className="table-scroll" tabIndex={0} role="region" aria-label="Scrollable numerical table"><table><thead><tr><th>Input · canonical SI</th>{items.map(item => <th key={item.id}>{item.name}</th>)}</tr></thead><tbody>{keys.map(key => <tr key={key}><th>{pretty(key.replaceAll('.', ' / '))}</th>{normalized.map((input, i) => <td key={i}>{typeof input[key] === 'number' ? fmt(input[key] as number, 5) : typeof input[key] === 'object' ? JSON.stringify(input[key]) : String(input[key] ?? 'Not specified')}</td>)}</tr>)}</tbody></table></div>
    </>}</>;
}

import { useState } from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { ArrowRight, Trash2 } from 'lucide-react';
import { Chart, reportOf } from './results';
import { PageHeading, Select } from './components';
import { flatten, type Unit } from './form';
import { fmt, pretty, type Metadata } from './api';
import type { Snapshot } from './workbench';

export default function Compare({ metadata }: { metadata: Metadata }) {
  const [unit, setUnit] = useState<Unit>('SI');
  const [items, setItems] = useState<Snapshot[]>(() => { try { return JSON.parse(sessionStorage.getItem('crs.compare.v1') || '[]'); } catch { return []; } });
  const remove = (id: string) => { const next = items.filter(x => x.id !== id); setItems(next); sessionStorage.setItem('crs.compare.v1', JSON.stringify(next)); };
  const stress = (n: number) => n / (unit === 'US' ? metadata.conversion_factors.MPA_PER_PSI : 1);
  const labels=items.map((item,i)=>`${i+1}. ${item.name}`);
  const rows = ['aci_table', 'abrams', 'bolomey', 'feret'].map(model => ({ model: pretty(model), ...Object.fromEntries(items.map((item,i) => [labels[i], reportOf(item)?.predictions[model].mean_28d_mpa == null ? null : stress(reportOf(item)!.predictions[model].mean_28d_mpa!)])) }));
  const normalized = items.map(item => { const report = reportOf(item)!; return flatten({ ...report.inputs,
    cement: { ...report.inputs.cement, weight_kg: report.cement_kg_m3 }, water_kg: report.water_added_kg_m3,
    coarse_kg: report.coarse_entered_kg_m3, fine_kg: report.fine_entered_kg_m3, batch_volume_m3: null }); });
  const keys = Array.from(new Set(normalized.flatMap(item => Object.keys(item)))).filter(key => normalized.some(item => JSON.stringify(item[key]) !== JSON.stringify(normalized[0]?.[key])));
  return <><PageHeading eyebrow="Calculated snapshots" title="Compare, with the context intact.">Up to three frozen analyses. Changing a draft never changes a saved comparison.</PageHeading>
    {!items.length ? <div className="empty-state"><h2>Begin with a calculated mix.</h2><p>Run an evaluation or design, then choose “Save for comparison” on its report.</p><a className="button primary" href="#evaluate">Evaluate a mix <ArrowRight size={17}/></a></div> : <>
      <div className="snapshot-list">{items.map(item => <div key={item.id}><span className="eyebrow">{item.mode}</span><h3>{item.name}</h3><small>{new Date(item.at).toLocaleString()}</small><button className="icon-button" onClick={() => remove(item.id)} aria-label={'Remove ' + item.name}><Trash2 size={17}/></button></div>)}</div>
      <div className="work-toolbar"><p className="caption">Each line retains its own materials, basis, flags and provenance.</p><Select label="Comparison units" value={unit} options={['SI', 'US'].map(value => ({ value, label: value }))} onChange={v => setUnit(v as Unit)}/></div>
      <Chart title="Strength across snapshots" note={`Estimated 28-day means (${unit === 'SI' ? 'MPa' : 'psi'}). Comparing models does not establish a measured performance ranking.`} rows={rows}>
        <ResponsiveContainer width="100%" height="100%"><BarChart data={rows}><CartesianGrid stroke="#e6e8df" vertical={false}/><XAxis dataKey="model"/><YAxis/><Tooltip/><Legend/>{items.map((item, i) => <Bar key={item.id} dataKey={labels[i]} fill={['#2a6257', '#a45436', '#596f89'][i]}/>)}</BarChart></ResponsiveContainer>
      </Chart><div className="table-scroll"><table><thead><tr><th>Calculated quantity</th>{items.map(item => <th key={item.id}>{item.name}</th>)}</tr></thead><tbody>{[
        ['Effective w/c', (item: Snapshot) => fmt(reportOf(item)!.wc, 4)], ['Slump (mm)', (item: Snapshot) => fmt(reportOf(item)!.slump.slump_mm)],
        ['Volume closure (m³/m³)', (item: Snapshot) => fmt(reportOf(item)!.volumes.closure_error_m3, 5)],
        ['Prediction constants', (item: Snapshot) => item.options.calibration_id || 'Uncalibrated defaults']
      ].map(([label, fn]) => <tr key={String(label)}><td>{String(label)}</td>{items.map(item => <td key={item.id}>{(fn as (s: Snapshot) => string)(item)}</td>)}</tr>)}</tbody></table></div>
      <h2 className="spaced-heading">What changed between these mixes?</h2><p className="caption">Only different inputs are listed. Masses here are normalized kg/m³; properties retain canonical SI units and declared aggregate basis.</p>
      <div className="table-scroll"><table><thead><tr><th>Input · canonical SI</th>{items.map(item => <th key={item.id}>{item.name}</th>)}</tr></thead><tbody>{keys.map(key => <tr key={key}><td>{pretty(key.replaceAll('.', ' / '))}</td>{normalized.map((input, i) => <td key={i}>{typeof input[key] === 'number' ? fmt(input[key] as number, 5) : String(input[key] ?? 'Not specified')}</td>)}</tr>)}</tbody></table></div>
    </>}</>;
}

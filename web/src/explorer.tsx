import { useEffect, useState } from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { Numeric, Select } from './components';
import { request, fmt, type Metadata, type Prediction, type MixInputs } from './api';
import { factor, fieldUnit, draftFrom, materialize, type Unit, type FieldDef } from './form';
import { Chart, reportOf, Flags } from './results';
import type { Snapshot } from './workbench';

const fields: FieldDef[] = [
  { path: 'water_kg', label: 'Added water', kind: 'weight' },
  { path: 'cement.weight_kg', label: 'Cement content', kind: 'weight' },
  { path: 'age_days', label: 'Test age (days)' },
];

export default function Explorer({ baseline, metadata, onAdopt }: { baseline: Snapshot; metadata: Metadata; onAdopt: (inputs: MixInputs) => void }) {
  const base = reportOf(baseline)!;
  const [parameter, setParameter] = useState('water_kg'), [unit, setUnit] = useState<Unit>('SI');
  const [raw, setRaw] = useState(String(base.inputs.water_kg));
  const [result, setResult] = useState<Prediction | null>(null), [message, setMessage] = useState(''), [busy, setBusy] = useState(false);
  const field = fields.find(item => item.path === parameter)!;
  const initialDraft = draftFrom(base.inputs);
  const conversion = factor(field, initialDraft, metadata);
  const label = field.label + (fieldUnit(field, initialDraft, unit) ? ' (' + fieldUnit(field, initialDraft, unit) + ')' : '');
  useEffect(() => {
    const controller = new AbortController();
    setResult(null); setMessage(''); setBusy(true);
    const draft = draftFrom(base.inputs);
    // Convert this single display value at the boundary; all other inputs stay canonical SI.
    const numeric = /^[+-]?(?:\d+\.?\d*|\.\d+)(?:e[+-]?\d+)?$/i.test(raw.trim()) ? Number(raw) : NaN;
    if (!Number.isFinite(numeric)) { setMessage('Enter a finite decimal value. The baseline is unchanged.'); setBusy(false); return () => controller.abort(); }
    draft[parameter] = String(numeric * (unit === 'US' ? conversion : 1));
    const prepared = materialize(draft, base.inputs, 'evaluate', 'SI', metadata);
    const timer = setTimeout(async () => {
      try {
        const prediction = await request<Prediction>('/predict', { inputs: prepared.inputs, options: baseline.options }, controller.signal);
        if (controller.signal.aborted) return;
        for (const [name, original] of Object.entries(base.predictions)) {
          const next = prediction.report.predictions[name];
          if (JSON.stringify(original.constants_used) !== JSON.stringify(next.constants_used) || original.constants_source !== next.constants_source) throw new Error('The parameter set changed since this baseline. Re-run the baseline before exploring.');
        }
        setResult(prediction);
      } catch (error) {
        if (!controller.signal.aborted) setMessage(error instanceof Error ? error.message : 'Hypothetical calculation failed.');
      } finally { if (!controller.signal.aborted) setBusy(false); }
    }, 350);
    return () => { clearTimeout(timer); controller.abort(); };
  }, [raw, parameter, unit, baseline.id, metadata]);
  const choose = (path: string) => {
    const next = fields.find(item => item.path === path)!;
    setParameter(path);
    setRaw(String(Number(initialDraft[path]) / (unit === 'US' ? factor(next, initialDraft, metadata) : 1)));
  };
  const changeUnit = (next: string) => {
    if (Number.isFinite(Number(raw)) && raw.trim()) setRaw(String(Number(raw) * (next === 'US' ? 1 / conversion : conversion)));
    setUnit(next as Unit);
  };
  const report = result?.report;
  const stressFactor = unit === 'US' ? metadata.conversion_factors.MPA_PER_PSI : 1;
  const stressUnit = unit === 'US' ? 'psi' : 'MPa';
  const exploringAge = parameter === 'age_days';
  const baselineSeries = exploringAge ? `Baseline · ${base.inputs.age_days} days (${stressUnit})` : `Baseline (${stressUnit})`;
  const hypotheticalSeries = exploringAge ? `Hypothetical · ${report?.inputs.age_days ?? '…'} days (${stressUnit})` : `Hypothetical (${stressUnit})`;
  const rows = Object.entries(base.predictions).map(([name, model]) => {
    const before = exploringAge ? base.age_adjusted[name]?.strength_mpa : model.mean_28d_mpa;
    const after = exploringAge ? report?.age_adjusted[name]?.strength_mpa : report?.predictions[name].mean_28d_mpa;
    return { model: name, [baselineSeries]: before == null ? null : before / stressFactor, [hypotheticalSeries]: after == null ? null : after / stressFactor };
  });
  const strengthNote = exploringAge
    ? `Age-adjusted estimates in ${stressUnit}: baseline at ${base.inputs.age_days} days versus hypothetical at ${report?.inputs.age_days ?? '…'} days. ${baseline.options.normalise_age_to_28d ? 'Normalized' : 'Literal'} age equation. The underlying 28-day means remain unchanged. All model warnings still apply.`
    : `28-day means in ${stressUnit}. All model warnings still apply.`;
  return <section className="mix-explorer no-print"><span className="eyebrow">Mix Explorer · hypothetical</span><h2>Change one thing. See what follows.</h2><p>The calculated baseline stays frozen. This is one-variable-at-a-time exploration, not an optimizer or evidence of physical causation.</p>
    <div className="fields"><Select label="Explore a parameter" value={parameter} options={fields.map(item => ({ value: item.path, label: item.label }))} onChange={choose}/><Numeric label={label} value={raw} onChange={setRaw} help="Other inputs and the declared yield stay fixed. Values are sent to the existing Python engine."/><Select label="Explorer units" value={unit} options={['SI', 'US'].map(value => ({ value, label: value }))} onChange={changeUnit}/></div>
    <p className="caption">For water/cement changes, aggregate quantities stay fixed: volume may no longer close. Age changes adjust age predictions, not the base 28-day means. No automatic yield balancing is applied.</p>
    {busy && <p role="status">Updating the hypothetical mix…</p>}{message && <p className="notice error" role="alert">{message}</p>}
    {report && <><div className="table-scroll" tabIndex={0} role="region" aria-label="Scrollable numerical table"><table><thead><tr><th>Calculated quantity</th><th>Baseline</th><th>Hypothetical</th><th>Signed difference</th></tr></thead><tbody>{[
      ['Effective w/c', base.wc, report.wc], ['Volume total (m³/m³)', base.volumes.total_m3, report.volumes.total_m3], ['Mass per declared volume (kg/m³)', base.unit_weight.computed_kg_m3, report.unit_weight.computed_kg_m3],
    ].map(([name, before, after]) => <tr key={String(name)}><th>{name}</th><td>{fmt(Number(before), 5)}</td><td>{fmt(Number(after), 5)}</td><td>{fmt(Number(after) - Number(before), 5)}</td></tr>)}</tbody></table></div>
      <Chart title="Baseline and hypothetical strength" note={strengthNote} rows={rows}><ResponsiveContainer width="100%" height="100%"><BarChart data={rows}><CartesianGrid stroke="#e6e8df" vertical={false}/><XAxis dataKey="model"/><YAxis/><Tooltip/><Legend/><Bar isAnimationActive={false} dataKey={baselineSeries} fill="#8c9382"/><Bar isAnimationActive={false} dataKey={hypotheticalSeries} fill="#2a6257"/></BarChart></ResponsiveContainer></Chart>
      <div className="table-scroll" tabIndex={0} role="region" aria-label="Scrollable numerical table"><table><thead><tr><th>Model</th><th>Baseline selected-age strength ({stressUnit})</th><th>Hypothetical selected-age strength ({stressUnit})</th></tr></thead><tbody>{Object.keys(base.predictions).map(name => <tr key={name}><th>{name}</th><td>{fmt(base.age_adjusted[name]?.strength_mpa == null ? null : base.age_adjusted[name]!.strength_mpa / stressFactor)}</td><td>{fmt(report.age_adjusted[name]?.strength_mpa == null ? null : report.age_adjusted[name]!.strength_mpa / stressFactor)}</td></tr>)}</tbody></table></div>
      <details className="explorer-checks"><summary>Hypothetical checks · {report.flags.length} notices</summary><Flags flags={report.flags}/></details><button className="button primary" onClick={() => onAdopt(report.inputs)}>Use hypothetical as new evaluation draft →</button><p className="caption">This explicit action replaces the evaluation draft. The calculated baseline and saved comparisons remain unchanged.</p>
    </>}
  </section>;
}

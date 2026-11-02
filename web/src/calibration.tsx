import { useState } from 'react';
import { ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine, Legend } from 'recharts';
import { Upload, Download, Save, Play, CheckCircle2 } from 'lucide-react';
import { PageHeading, Section, Select, Toggle } from './components';
import { Chart } from './results';
import { request, ApiError, fmt, type Uploaded, type Fit } from './api';

export default function Calibration() {
  const [upload, setUpload] = useState<Uploaded | null>(null), [fit, setFit] = useState<Fit | null>(null);
  const [material, setMaterial] = useState(''), [age, setAge] = useState('only_28d'), [subset, setSubset] = useState(false);
  const [selectedModels, setSelectedModels] = useState(['abrams', 'bolomey', 'feret']);
  const [validation, setValidation] = useState('in_sample'), [diagnosticSplit, setDiagnosticSplit] = useState('calibration'), [replaceAllowed, setReplaceAllowed] = useState(false);
  const [model, setModel] = useState('abrams'), [busy, setBusy] = useState(false), [message, setMessage] = useState(''), [saved, setSaved] = useState(false), [synthetic, setSynthetic] = useState(false);
  const invalidate = () => { setFit(null); setSaved(false); setMessage(''); };
  async function validate(file: File, isSynthetic = false) {
    setBusy(true); setMessage(''); setUpload(null); invalidate(); setSynthetic(isSynthetic);
    try {
      if (file.size > 10 * 1024 * 1024) throw new Error('File exceeds the 10 MiB limit.');
      const form = new FormData(); form.append('file', file);
      const response = await fetch('/api/v1/calibration/validate', { method: 'POST', body: form });
      const data = await response.json(); if (!response.ok) throw new Error(data.error?.message || 'The source file could not be read.');
      setUpload(data); setMaterial(data.material_sets[0] || ''); setSubset(false);
      setSynthetic(isSynthetic || data.rows.some((row: Uploaded['rows'][number]) => (row.mix_id+' '+row.notes).toUpperCase().includes('SYNTHETIC')));
    } catch (error) { setMessage(error instanceof Error ? error.message : 'Upload failed.'); } finally { setBusy(false); }
  }
  const eligible = upload?.rows.filter(row => row.material_set_id === material && (age === 'convert' || row.age_days === 28)).length || 0;
  async function loadDemo() {
    setMessage('');
    try {
      const response = await fetch('/api/v1/demo/calibration.csv');
      if (!response.ok) throw new Error('The local demo dataset is unavailable.');
      await validate(new File([await response.blob()], 'synthetic-demo.csv', { type: 'text/csv' }), true);
    } catch (error) { setMessage(error instanceof Error ? error.message : 'The local server is unavailable.'); }
  }
  async function runFit() {
    if (!upload) return; setBusy(true); setMessage('');
    try { const result = await request<Fit>('/calibration/fit', { dataset_id: upload.dataset_id, material_set_id: material, age_policy: age, accept_valid_subset: subset, models: selectedModels, validation_mode: validation }); setFit(result); setModel(Object.keys(result.results)[0]); setDiagnosticSplit(validation === 'group_holdout' ? 'held_out' : 'calibration'); setSaved(false); setReplaceAllowed(false); }
    catch (error) { setMessage(error instanceof Error ? error.message : 'Fitting failed.'); } finally { setBusy(false); }
  }
  async function save() {
    if (!fit) return; setBusy(true); setMessage('');
    try { await request('/calibration/save', { fit_id: fit.fit_id, replace_existing: replaceAllowed }); setSaved(true); }
    catch (error) { setMessage(error instanceof Error ? error.message : 'Saving failed.'); } finally { setBusy(false); }
  }
  const points = (fit?.diagnostics[model] || []).filter(point => point.split === diagnosticSplit);
  const extent = points.length ? Math.max(...points.flatMap(p => [p.measured_mpa, p.predicted_mpa])) * 1.1 : 1;
  return <><PageHeading eyebrow="03 / Calibrate with lab data" title="Let your observations speak.">Fit the model coefficients to a defined material set. See the agreement, inspect the residuals and keep the source with the result.</PageHeading>
    <Section title="Bring a lab mix log" description="CSV or .xlsx · canonical SI · up to 10 MiB / 5,000 rows. Your upload is processed locally and is not stored in browser storage.">
      <div className="upload-zone"><Upload size={25}/><h3>A record for every mix and test age.</h3><p>Use the stable lab schema. The template’s synthetic rows must be deleted before recording experiments.</p><label className="button primary">Choose CSV or Excel<input aria-label="Lab mix log" type="file" accept=".csv,.xlsx" disabled={busy} onChange={e => { const file = e.target.files?.[0]; if (file) validate(file); e.target.value = ''; }}/></label>
        <a className="text-link" href="/api/v1/demo/calibration.csv" download><Download size={16}/> Download synthetic demonstration</a>
        <button className="text-link bare" disabled={busy} onClick={loadDemo}>Explore the 12-row synthetic demo <span aria-hidden="true">→</span></button>
      </div>
    </Section>{busy && <p role="status">Working with the local engine…</p>}{message && <div className="notice error" role="alert">{message}</div>}
    {upload && <><div className={'notice ' + (synthetic ? 'warning' : '')}>{synthetic && <strong>Synthetic demonstration — not laboratory evidence. </strong>}{upload.valid_count} valid rows · {upload.errors.length} cell errors · source {upload.source_name}</div>
      {upload.errors.length > 0 && <><div className="table-scroll" tabIndex={0} role="region" aria-label="Scrollable numerical table"><table><thead><tr><th>Row</th><th>Column</th><th>Issue</th></tr></thead><tbody>{upload.errors.map((e, i) => <tr key={i}><td>{e.row}</td><td>{e.column}</td><td>{e.message}</td></tr>)}</tbody></table></div><Toggle label="Fit valid rows while excluding the errors shown above" checked={subset} onChange={v => { setSubset(v); invalidate(); }}/></>}
      {upload.valid_count > 0 && <Section title="Choose the evidence" description="Fit one material set at a time. Keep materials, air condition and test conditions consistent."><div className="fields"><Select label="Material set" value={material} options={upload.material_sets.map(value => ({ value, label: value }))} onChange={v => { setMaterial(v); invalidate(); }}/><Select label="Age policy" value={age} options={[{ value: 'only_28d', label: 'Actual 28-day measurements only' }, { value: 'convert', label: 'Convert other ages with the age equation' }]} onChange={v => { setAge(v); invalidate(); }}/></div><p className="caption">{eligible} eligible observations. At least three are required, with varying w/c for an Abrams fit.</p>{age === 'convert' && <p className="notice warning">Age conversion is model-based; verify cement type, curing and applicability. Actual 28-day values remain unchanged.</p>}<Select label="Validation approach" value={validation} options={[{ value: 'in_sample', label: 'Calibration only · in-sample diagnostics' }, { value: 'group_holdout', label: 'Internal grouped holdout · at least 10 mixes' }]} onChange={value => { setValidation(value); invalidate(); }}/><p className="caption">Grouped holdout keeps each mix_id together. About 20% of distinct mixes (at least two) are held out using a fixed split. Ten mixes is a project guard, not a guarantee of statistical adequacy. Reusing the holdout for tuning weakens its evidence.</p><div className="toggle-row">{['abrams', 'bolomey', 'feret'].map(name => <Toggle key={name} label={'Fit ' + name} checked={selectedModels.includes(name)} onChange={yes => { setSelectedModels(yes ? [...selectedModels, name] : selectedModels.filter(value => value !== name)); invalidate(); }}/>)}</div><button className="button primary" disabled={busy || eligible < 3 || !selectedModels.length || (!!upload.errors.length && !subset)} onClick={runFit}><Play size={16}/> {selectedModels.length === 3 ? 'Fit three strength models' : 'Fit selected models'}</button><details className="source-row"><summary>Review valid source rows (canonical SI)</summary><div className="table-scroll" tabIndex={0} role="region" aria-label="Scrollable numerical table"><table><thead><tr>{Object.keys(upload.rows[0]).map(key => <th key={key}>{key}</th>)}</tr></thead><tbody>{upload.rows.map((row, i) => <tr key={i}>{Object.values(row).map((value, j) => <td key={j}>{String(value ?? '')}</td>)}</tr>)}</tbody></table></div></details></Section>}
    </>}
    {fit && <><Section title="Fit, then look at the disagreement" description={fit.context.validation_mode === 'group_holdout' ? 'Internal grouped holdout: fit only calibration rows, then evaluate held-out mix IDs. This is not external validation.' : 'In-sample diagnostics describe fitting observations. They do not demonstrate accuracy on unseen mixes.'}>
      <div className="fields"><Select label="Diagnostic observations" value={diagnosticSplit} options={[{ value: 'calibration', label: 'Calibration rows · in sample' }, ...(fit.context.n_held_out ? [{ value: 'held_out', label: 'Held-out mixes · internal validation' }] : [])]} onChange={setDiagnosticSplit}/><Select label="Diagnostic model" value={model} options={Object.keys(fit.results).map(value => ({ value, label: value }))} onChange={setModel}/></div>
      <div className="table-scroll" tabIndex={0} role="region" aria-label="Scrollable numerical table"><table><thead><tr><th>Model</th><th>Rows</th><th>MAE (MPa)</th><th>RMSE (MPa)</th><th>R² (MPa)</th><th>Default RMSE (MPa)</th><th>Fitted constants</th></tr></thead><tbody>{Object.entries(fit.results).map(([name, result]) => { const metric = fit.metrics[name]?.[diagnosticSplit]; return <tr key={name}><th>{name}</th><td>{metric?.n}</td><td>{fmt(metric?.mae_mpa, 3)}</td><td>{fmt(metric?.rmse_mpa, 3)}</td><td>{metric?.r2_mpa == null ? 'Undefined (constant target)' : fmt(metric.r2_mpa, 4)}</td><td>{fmt(metric?.default_rmse_mpa, 3)}</td><td>{Object.entries(result.values).map(([key, value]) => `${key}=${fmt(value, 5)}`).join(', ')}</td></tr>; })}</tbody></table></div>
      <p className="caption">Eligible {fit.eligible_rows} · excluded {fit.excluded_rows} · age-converted {fit.converted_rows} · fit rows {fit.context.n_train} · held-out rows {fit.context.n_held_out}. Metrics use 28-day cylinder-equivalent MPa; age conversion is an assumption, not a measurement.</p>
      <details className="source-row"><summary>Inspect fitting context and raw fit statistics</summary><pre>{JSON.stringify({ context: fit.context, fit_statistics: fit.results }, null, 2)}</pre><p>Abrams fitting uses log strength; its raw R² space is recorded above. The primary comparison uses MPa-space diagnostics. Constant-target R² is undefined here, rather than using the legacy fitter's 0/1 convention.</p></details>
    </Section>
      <div className="chart-grid"><Chart title="Predicted versus measured" note={`${diagnosticSplit === 'held_out' ? 'Held-out mixes' : 'In-sample calibration'} · 28-day cylinder-equivalent MPa. The diagonal is equality, not a fitted regression line.`} rows={points}><ResponsiveContainer width="100%" height="100%"><ScatterChart><CartesianGrid stroke="#e6e8df"/><XAxis dataKey="measured_mpa" name="Measured" type="number" domain={[0, extent]}/><YAxis dataKey="predicted_mpa" name="Predicted" type="number" domain={[0, extent]}/><Tooltip cursor={{ strokeDasharray: '4 4' }}/><ReferenceLine segment={[{ x: 0, y: 0 }, { x: extent, y: extent }]} stroke="#777" strokeDasharray="4 4"/><Legend/><Scatter isAnimationActive={false} name="Fitted model" data={points} fill="#2a6257"/><Scatter isAnimationActive={false} name="Uncalibrated default" data={points.map(point => ({ ...point, predicted_mpa: point.default_mpa }))} fill="#94721b"/></ScatterChart></ResponsiveContainer></Chart>
      <Chart title="Inspect the residuals" note="Residual = measured minus predicted (MPa). A pattern can reveal a model mismatch; no uncertainty claim is inferred." rows={points}><ResponsiveContainer width="100%" height="100%"><ScatterChart><CartesianGrid stroke="#e6e8df"/><XAxis dataKey="predicted_mpa" name="Predicted" type="number"/><YAxis dataKey="residual_mpa" name="Residual" type="number"/><Tooltip/><ReferenceLine y={0} stroke="#777"/><Scatter isAnimationActive={false} data={points} fill="#a45436"/></ScatterChart></ResponsiveContainer></Chart></div>
      <Toggle label="Allow a new saved revision for an existing material set" checked={replaceAllowed} onChange={setReplaceAllowed} help="Required before replacing stored parameters; earlier records are retained locally."/><div className="run-panel"><div><h2>Keep this material set.</h2><p>Saving preserves selected fits, source hash, fitting conditions and split context. Existing models not selected here are retained. Replacements keep earlier model records in revision history. Select the saved set in a calculation workspace.</p><small className="hash">SHA-256 {fit.data_hash}</small></div><button className="button primary" disabled={busy || saved} onClick={save}>{saved ? <CheckCircle2 size={17}/> : <Save size={17}/>} {saved ? 'Saved locally' : 'Save material-set fits'}</button></div>{saved && <p className="notice" role="status">Saved {fit.material_set_id}. These fits are now available under Prediction constants. {synthetic && 'This is a synthetic demonstration calibration.'}</p>}
    </>}</>;
}

import { useState } from 'react';
import { ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine } from 'recharts';
import { Upload, Download, Save, Play, CheckCircle2 } from 'lucide-react';
import { PageHeading, Section, Select, Toggle } from './components';
import { Chart } from './results';
import { request, ApiError, fmt, type Uploaded, type Fit } from './api';

export default function Calibration() {
  const [upload, setUpload] = useState<Uploaded | null>(null), [fit, setFit] = useState<Fit | null>(null);
  const [material, setMaterial] = useState(''), [age, setAge] = useState('only_28d'), [subset, setSubset] = useState(false);
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
    try { const result = await request<Fit>('/calibration/fit', { dataset_id: upload.dataset_id, material_set_id: material, age_policy: age, accept_valid_subset: subset }); setFit(result); setSaved(false); }
    catch (error) { setMessage(error instanceof Error ? error.message : 'Fitting failed.'); } finally { setBusy(false); }
  }
  async function save() {
    if (!fit) return; setBusy(true); setMessage('');
    try { await request('/calibration/save', { fit_id: fit.fit_id }); setSaved(true); }
    catch (error) { setMessage(error instanceof Error ? error.message : 'Saving failed.'); } finally { setBusy(false); }
  }
  const points = fit?.diagnostics[model] || [];
  const extent = points.length ? Math.max(...points.flatMap(p => [p.measured_mpa, p.predicted_mpa])) * 1.1 : 1;
  return <><PageHeading eyebrow="03 / Calibrate with lab data" title="Let your observations speak.">Fit the model coefficients to a defined material set. See the agreement, inspect the residuals and keep the source with the result.</PageHeading>
    <Section title="Bring a lab mix log" description="CSV or .xlsx · canonical SI · up to 10 MiB / 5,000 rows. Your upload is processed locally and is not stored in browser storage.">
      <div className="upload-zone"><Upload size={25}/><h3>A record for every mix and test age.</h3><p>Use the stable lab schema. The template’s synthetic rows must be deleted before recording experiments.</p><label className="button primary">Choose CSV or Excel<input aria-label="Lab mix log" type="file" accept=".csv,.xlsx" disabled={busy} onChange={e => { const file = e.target.files?.[0]; if (file) validate(file); e.target.value = ''; }}/></label>
        <a className="text-link" href="/api/v1/demo/calibration.csv" download><Download size={16}/> Download synthetic demonstration</a>
        <button className="text-link bare" disabled={busy} onClick={loadDemo}>Explore the 12-row synthetic demo <span aria-hidden="true">→</span></button>
      </div>
    </Section>{busy && <p role="status">Working with the local engine…</p>}{message && <div className="notice error" role="alert">{message}</div>}
    {upload && <><div className={'notice ' + (synthetic ? 'warning' : '')}>{synthetic && <strong>Synthetic demonstration — not laboratory evidence. </strong>}{upload.valid_count} valid rows · {upload.errors.length} cell errors · source {upload.source_name}</div>
      {upload.errors.length > 0 && <><div className="table-scroll"><table><thead><tr><th>Row</th><th>Column</th><th>Issue</th></tr></thead><tbody>{upload.errors.map((e, i) => <tr key={i}><td>{e.row}</td><td>{e.column}</td><td>{e.message}</td></tr>)}</tbody></table></div><Toggle label="Fit valid rows while excluding the errors shown above" checked={subset} onChange={v => { setSubset(v); invalidate(); }}/></>}
      {upload.valid_count > 0 && <Section title="Choose the evidence" description="Fit one material set at a time. Keep materials, air condition and test conditions consistent."><div className="fields"><Select label="Material set" value={material} options={upload.material_sets.map(value => ({ value, label: value }))} onChange={v => { setMaterial(v); invalidate(); }}/><Select label="Age policy" value={age} options={[{ value: 'only_28d', label: 'Actual 28-day measurements only' }, { value: 'convert', label: 'Convert other ages with the age equation' }]} onChange={v => { setAge(v); invalidate(); }}/></div><p className="caption">{eligible} eligible observations. At least three are required, with varying w/c for an Abrams fit.</p>{age === 'convert' && <p className="notice warning">Age conversion is model-based; verify cement type, curing and applicability. Actual 28-day values remain unchanged.</p>}<button className="button primary" disabled={busy || eligible < 3 || (!!upload.errors.length && !subset)} onClick={runFit}><Play size={16}/> Fit three strength models</button><details className="source-row"><summary>Review valid source rows (canonical SI)</summary><div className="table-scroll"><table><thead><tr>{Object.keys(upload.rows[0]).map(key => <th key={key}>{key}</th>)}</tr></thead><tbody>{upload.rows.map((row, i) => <tr key={i}>{Object.values(row).map((value, j) => <td key={j}>{String(value ?? '')}</td>)}</tr>)}</tbody></table></div></details></Section>}
    </>}
    {fit && <><Section title="Fit, then look at the disagreement" description="In-sample diagnostics describe these observations; they are not cross-validation or evidence of certified predictive accuracy."><div className="table-scroll"><table><thead><tr><th>Model</th><th>Rows</th><th>R²</th><th>R² space</th><th>R² (MPa)</th><th>RMSE (MPa)</th><th>Constants</th></tr></thead><tbody>{Object.entries(fit.results).map(([name, r]) => <tr key={name}><td>{name}</td><td>{r.n_rows}</td><td>{fmt(r.r2, 4)}</td><td>{r.r2_space}</td><td>{fmt(r.r2_mpa, 4)}</td><td>{fmt(r.rmse_mpa, 3)}</td><td>{Object.entries(r.values).map(([key, value]) => `${key}=${fmt(value, 5)}`).join(', ')}</td></tr>)}</tbody></table></div><p className="caption">Eligible {fit.eligible_rows} · excluded {fit.excluded_rows} · converted {fit.converted_rows}</p><div className="fields"><Select label="Diagnostic model" value={model} options={Object.keys(fit.results).map(value => ({ value, label: value }))} onChange={setModel}/></div></Section>
      <div className="chart-grid"><Chart title="Predicted versus measured" note="28-day cylinder-equivalent strength (MPa). The diagonal is equality, not a fitted regression line." rows={points}><ResponsiveContainer width="100%" height="100%"><ScatterChart><CartesianGrid stroke="#e6e8df"/><XAxis dataKey="measured_mpa" name="Measured" type="number" domain={[0, extent]}/><YAxis dataKey="predicted_mpa" name="Predicted" type="number" domain={[0, extent]}/><Tooltip cursor={{ strokeDasharray: '4 4' }}/><ReferenceLine segment={[{ x: 0, y: 0 }, { x: extent, y: extent }]} stroke="#777" strokeDasharray="4 4"/><Scatter data={points} fill="#2a6257"/></ScatterChart></ResponsiveContainer></Chart>
      <Chart title="Inspect the residuals" note="Residual = measured minus predicted (MPa). A pattern can reveal a model mismatch; no uncertainty claim is inferred." rows={points}><ResponsiveContainer width="100%" height="100%"><ScatterChart><CartesianGrid stroke="#e6e8df"/><XAxis dataKey="predicted_mpa" name="Predicted" type="number"/><YAxis dataKey="residual_mpa" name="Residual" type="number"/><Tooltip/><ReferenceLine y={0} stroke="#777"/><Scatter data={points} fill="#a45436"/></ScatterChart></ResponsiveContainer></Chart></div>
      <div className="run-panel"><div><h2>Keep this material set.</h2><p>Saving preserves three model fits, source hash and timestamp. Select the saved set in a calculation workspace.</p><small className="hash">SHA-256 {fit.data_hash}</small></div><button className="button primary" disabled={busy || saved} onClick={save}>{saved ? <CheckCircle2 size={17}/> : <Save size={17}/>} {saved ? 'Saved locally' : 'Save material-set fits'}</button></div>{saved && <p className="notice" role="status">Saved {fit.material_set_id}. These fits are now available under Prediction constants. {synthetic && 'This is a synthetic demonstration calibration.'}</p>}
    </>}</>;
}

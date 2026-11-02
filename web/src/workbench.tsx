import { lazy, Suspense, useEffect, useState } from 'react';
import { ArrowLeft, ArrowRight, RotateCcw, Play, SlidersHorizontal } from 'lucide-react';
import { Numeric, TextField, Select, Toggle, Section, PageHeading } from './components';
import { MaterialCompanion, type MaterialKind } from './material-companion';
import { ApiError, request, pretty, type Metadata, type Options, type Prediction, type Design, type MixInputs, type ModeAInputs } from './api';
import { allFields, materialFields, conditionFields, advancedFields, draftFrom, fieldUnit, materialize, switchUnits, type Draft, type Mode, type Unit, type FieldDef } from './form';
const Results = lazy(() => import('./results'));
export type Snapshot = { id: string; name: string; description?: string; mode: Mode; at: string; data: Prediction | Design; inputs: MixInputs | ModeAInputs; options: Options };
const fingerprint = (value: unknown) => JSON.stringify(value, (_, item) => typeof item === 'number' ? Number(item.toPrecision(12)) : item);

export default function Workbench({ mode, metadata }: { mode: Mode; metadata: Metadata }) {
  const template = mode === 'evaluate' ? metadata.defaults_b : metadata.defaults_a;
  const key = 'crs.workspace.v1.' + mode;
  const initial = () => {
    try { const stored = JSON.parse(sessionStorage.getItem(key) || 'null'); if (stored?.version === 1) return stored; } catch { /* A corrupt old draft must not prevent opening the app. */ }
    return { version: 1, draft: draftFrom(template), unit: 'SI' as Unit, options: { policy: 'extrapolate', normalise_age_to_28d: false, calibration_id: null }, snapshot: null, submitted: '' };
  };
  const [state, setState] = useState(initial);
  const draft = state.draft as Draft, unit = state.unit as Unit, options = state.options as Options;
  const snapshot = state.snapshot as Snapshot | null;
  const [view, setView] = useState<'inputs' | 'results'>('inputs');
  const [busy, setBusy] = useState(false), [errors, setErrors] = useState<Record<string, string>>({}), [message, setMessage] = useState('');
  const [calibrations, setCalibrations] = useState<string[]>([]);
  useEffect(() => { try { sessionStorage.setItem(key, JSON.stringify(state)); } catch { setMessage('Browser storage is full. Export the current report before closing this tab.'); } }, [state, key]);
  useEffect(() => { request<{ items: string[] }>('/calibrations').then(r => setCalibrations(r.items)).catch(() => {}); }, []);
  useEffect(() => {
    const evaluation = sessionStorage.getItem('crs.load-evaluation');
    if (evaluation && mode === 'evaluate') {
      try { setState({ ...initial(), draft: draftFrom(JSON.parse(evaluation)), unit: 'SI', snapshot: null, submitted: '' }); } catch { setMessage('The example could not be loaded.'); }
      sessionStorage.removeItem('crs.load-evaluation');
    }
    const example = sessionStorage.getItem('crs.load-example');
    if (example && mode === 'design') {
      const found = metadata.examples.find(x => x.id === example);
      if (found) { setState({ ...initial(), draft: draftFrom(found.inputs as ModeAInputs), unit: 'SI', snapshot: null, submitted: '' }); sessionStorage.removeItem('crs.load-example'); }
    }
  }, [mode, metadata]);
  const update = (path: string, value: string | boolean) => setState((s: typeof state) => ({ ...s, draft: { ...s.draft, [path]: value } }));
  const setOptions = (value: Partial<Options>) => setState((s: typeof state) => ({ ...s, options: { ...s.options, ...value } }));
  const current = materialize(draft, template, mode, unit, metadata);
  const stale = !!snapshot && (Object.keys(current.errors).length > 0 || fingerprint({ inputs: current.inputs, options }) !== state.submitted);
  const changeUnit = (next: string) => setState((s: typeof state) => ({ ...s, unit: next, draft: switchUnits(s.draft, mode, next as Unit, metadata) }));
  async function run() {
    setErrors(current.errors); setMessage('');
    if (Object.keys(current.errors).length) { setMessage('Check the highlighted entries. Your draft has been preserved.'); return; }
    setBusy(true);
    try {
      const data = await request<Prediction | Design>(mode === 'evaluate' ? '/predict' : '/design', { inputs: current.inputs, options });
      const fresh: Snapshot = { id: crypto.randomUUID(), name: mode === 'evaluate' ? 'Evaluated mix' : 'Designed mix', mode, at: new Date().toISOString(), data, inputs: current.inputs, options: { ...options } };
      setState((s: typeof state) => ({ ...s, snapshot: fresh, submitted: fingerprint({ inputs: current.inputs, options }) }));
      setView('results'); window.scrollTo(0, 0);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'The local server is unavailable. Check that the Python server is running.');
      if (error instanceof ApiError) setErrors(Object.fromEntries(error.fields.map(f => [f.path.replace(/^inputs\./, ''), f.message])));
    } finally { setBusy(false); }
  }
  const renderField = (field: FieldDef) => {
    const suffix = fieldUnit(field, draft, unit); const label = field.label + (suffix ? ` (${suffix})` : '');
    if (field.choices) return <Select key={field.path} label={label} value={String(draft[field.path] || '')}
      options={[...(field.optional ? [{ value: '', label: 'Not specified' }] : []), ...(metadata.choices[field.choices] || []).map(value => ({ value, label: pretty(value) }))]}
      onChange={value => update(field.path, value)} help={field.help}/>;
    if (field.text) return <TextField key={field.path} label={label} value={String(draft[field.path] || '')} onChange={value => update(field.path, value)} help={field.help} optional={field.optional} placeholder={field.placeholder}/>;
    return <Numeric key={field.path} label={label} value={String(draft[field.path] ?? '')} onChange={value => update(field.path, value)} optional={field.optional} help={field.help} error={errors[field.path]}/>;
  };
  if (view === 'results' && snapshot) return <><div className="work-toolbar no-print"><button className="text-link bare" onClick={() => { setView('inputs'); window.scrollTo(0, 0); }}><ArrowLeft size={16}/> Edit inputs</button><Select label="Display units" value={unit} options={[{ value: 'SI', label: 'SI · metric' }, { value: 'US', label: 'US · customary' }]} onChange={changeUnit}/></div>
    {stale && <div className="notice warning" role="status">Inputs changed — run analysis again. This is the previous calculated snapshot.</div>}
    <Suspense fallback={<p>Preparing the calculated report…</p>}><Results snapshot={snapshot} unit={unit} metadata={metadata} onAdopt={inputs => {
      if (mode === 'design') { sessionStorage.setItem('crs.load-evaluation', JSON.stringify(inputs)); location.hash = 'evaluate'; }
      else { setState((s: typeof state) => ({ ...s, draft: draftFrom(inputs), unit: 'SI' })); setView('inputs'); window.scrollTo(0, 0); }
    }}/></Suspense></>;
  return <>
    <PageHeading eyebrow={mode === 'evaluate' ? '01 / Evaluate a mix' : '02 / Design a mix'} title={mode === 'evaluate' ? 'Start with what goes in.' : 'Begin with a clear target.'}>
      {mode === 'evaluate' ? 'Enter your batch and material properties. We’ll follow the water, compare the models and make the important checks visible.' : 'A transparent ten-step course design, from strength and exposure to proportions you can take to a trial batch.'}</PageHeading>
    <div className="work-toolbar no-print"><div className="actions compact"><button className="button small" onClick={() => { if (confirm('Reset this workspace? Saved calibrations are unaffected.')) { setState({ ...initial(), draft: draftFrom(template), unit: 'SI', snapshot: null, submitted: '' }); setErrors({}); setMessage(''); } }}><RotateCcw size={14}/> Reset</button><a href="#examples" className="text-link">Load a worked example <ArrowRight size={15}/></a>
      {snapshot && <button className="button small" onClick={() => { setView('results'); window.scrollTo(0, 0); }}>View last report {stale && <span className="badge">Out of date</span>}</button>}</div>
      <Select label="Input units" value={unit} options={[{ value: 'SI', label: 'SI · metric' }, { value: 'US', label: 'US · customary' }]} onChange={changeUnit}/></div>
    <div className="work-layout"><aside className="section-rail no-print"><span className="eyebrow">In this workspace</span>{[['basis', mode === 'evaluate' ? 'Batch & basis' : 'Design targets'], ['materials', 'Material properties'], ['conditions', 'Conditions'], ['advanced', 'Advanced'], ['run', 'Run analysis']].map(([to, text], i) => <a key={to} href={'#' + mode + ':' + to} onClick={e => { e.preventDefault(); document.getElementById(to)?.scrollIntoView({ behavior: 'auto', block: 'start' }); }}><span>0{i + 1}</span>{text}</a>)}<p>Typed values are drafts.<br/>Analysis runs only when<br/>you ask it to.</p></aside>
    <div className="form-body"><Section id="basis" title={mode === 'evaluate' ? 'Batch & aggregate basis' : 'Strength & placement'} eyebrow="01 / Start here">
      <p className="default-note">Starting values are illustrative defaults, not laboratory measurements. Check each value before analysis.</p>
      {mode === 'evaluate' ? <>
        <div className="fields">{renderField({ path: 'aggregate_weight_basis', label: 'Aggregate weight basis', choices: 'basis' })}</div>
        <div className="definition"><strong>Which weight are you entering?</strong><p><b>As received</b> includes stockpile moisture. <b>Oven dry</b> uses dry mass with the entered moisture. <b>SSD</b> treats aggregate as saturated surface-dry: free water is zero.</p></div>
        <Toggle label="Enter actual batch weights" checked={draft.batch_volume_m3 !== '' && draft.batch_volume_m3 != null} onChange={yes => update('batch_volume_m3', yes ? String(unit === 'SI' ? 1 : 1 / metadata.conversion_factors.M3_PER_YD3) : '')} help="Otherwise enter contents per unit concrete volume. The labels below follow this choice."/>
        {!!draft.batch_volume_m3 && <div className="fields">{renderField({ path: 'batch_volume_m3', label: 'Intended batch yield', kind: 'volume', optional: true, help: 'Declared target, not an automatic constraint. Adding cement does not remove sand or rebalance volume. Check calculated volume closure after analysis.' })}</div>}
      </> : <><div className="fields">{renderField({ path: 'specified_fc_mpa', label: 'Specified strength', kind: 'stress' })}{renderField({ path: 'durability_class', label: 'Durability class', choices: 'durability' })}{renderField({ path: 'batch_volume_m3', label: 'Trial batch volume', kind: 'volume' })}
        <Select label="Field moisture convention" value={String(draft.moisture_convention)} options={['course', 'strict'].map(value => ({ value, label: value === 'course' ? 'Course · slide convention' : 'Strict · SSD consistent' }))} onChange={v => update('moisture_convention', v)}/></div>
        <div className="toggle-row">{[['underwater', 'Underwater placement'], ['flatwork', 'Flatwork'], ['hand_consolidated', 'Hand-consolidated mass concrete']].map(([path, label]) => <Toggle key={path} label={label} checked={!!draft[path]} onChange={v => update(path, v)}/>)}</div></>}
    </Section>
    <div id="materials">{materialFields(mode).map((group, i) => <Section key={group.title} title={group.title} eyebrow={'0' + (i + 2) + ' / Materials'} description={group.description} companion={<MaterialCompanion material={(['cement', 'coarse', 'fine'] as MaterialKind[])[i]}/>}><div className="fields">{group.fields.map(renderField)}</div></Section>)}</div>
    {mode === 'evaluate' && <Section title="Water" description="Added water is separate from aggregate free water. Never count surface moisture twice." companion={<MaterialCompanion material="water"/>}><div className="fields">{renderField({ path: 'water_kg', label: 'Added water', kind: 'weight' })}</div></Section>}
    <Section id="conditions" title="Conditions & air" description="Use the conditions represented by your material set and test specimens."><div className="toggle-row"><Toggle label="Air entrained" checked={!!draft.air_entrained} onChange={v => update('air_entrained', v)}/><Toggle label="Normalize age equation to 28 days" checked={!!options.normalise_age_to_28d} onChange={v => setOptions({ normalise_age_to_28d: v })}/></div>
      <div className="fields">{conditionFields.map(renderField)}{mode === 'evaluate' && <>{renderField({ path: 'age_days', label: 'Test age (days)' })}{renderField({ path: 'air_pct', label: 'Air content (%)', optional: true, help: 'Leave blank for the ACI table default; an entered value is an explicit override.' })}</>}
      <Select label="Out-of-range policy" value={options.policy || 'extrapolate'} options={['extrapolate', 'clamp', 'raise'].map(value => ({ value, label: pretty(value) }))} onChange={v => setOptions({ policy: v as Options['policy'] })}/>
      <Select label="Prediction constants" value={options.calibration_id || ''} options={[{ value: '', label: 'Uncalibrated project defaults' }, ...calibrations.map(value => ({ value, label: value }))]} onChange={v => setOptions({ calibration_id: v || null })}/></div>
    </Section>
    <details className="advanced" id="advanced"><summary><SlidersHorizontal size={17}/> Optional & advanced properties</summary><div className="fields">{advancedFields(mode).map(renderField)}</div><p className="caption">Cube factors are supplied by you. Admixture information does not introduce a new physical model.</p></details>
    <div id="run" className="run-panel"><div><h2>Ready to look closer?</h2><p>Your input values stay here. Run when the mix is ready.</p>{stale && <p className="stale" role="status">Inputs changed — run analysis again.</p>}</div><button className="button primary" disabled={busy} onClick={run}><Play size={16}/>{busy ? 'Calculating…' : 'Run analysis'}</button></div>
    {message && <div className="notice error" role="alert"><strong>Analysis needs attention</strong><p>{message}</p>{Object.entries(errors).map(([path, value]) => <p key={path}>{pretty(path)}: {value}</p>)}</div>}
    </div></div></>;
}

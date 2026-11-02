import { fmt, pretty, type Report } from './api';

const equations: Record<string, string> = {
  aci_table: 'f28 = inverse lookup of the required-average-strength versus w/c table',
  abrams: 'f28 = A / B^(w/c)',
  bolomey: 'f28 = K × (1/(w/c) − 0.5)',
  feret: 'f28 = K × [Vc / (Vc + Vw + Va)]²',
};

export function EngineeringNotes({ report }: { report: Report }) {
  return <details className="engineering-notes"><summary>Show the engineering</summary>
    <p>Values below come from this calculated snapshot, in canonical SI. Display rounding never changes exported numbers.</p>
    <div className="engineering-grid">
      <section><h3>01 · Resolve aggregate moisture</h3><p>Free water = oven-dry mass × (total moisture − absorption) / 100. SSD entry uses absorption as effective moisture, giving zero free water.</p>
        <div className="table-scroll"><table><thead><tr><th>Quantity</th><th>Coarse</th><th>Fine</th></tr></thead><tbody>
          <tr><td>Declared basis</td><td colSpan={2}>{pretty(report.inputs.aggregate_weight_basis)}</td></tr>
          <tr><td>Oven-dry mass (kg/m³)</td><td>{fmt(report.coarse.oven_dry_kg, 4)}</td><td>{fmt(report.fine.oven_dry_kg, 4)}</td></tr>
          <tr><td>SSD mass (kg/m³)</td><td>{fmt(report.coarse.ssd_kg, 4)}</td><td>{fmt(report.fine.ssd_kg, 4)}</td></tr>
          <tr><td>Effective moisture (%)</td><td>{fmt(report.coarse.effective_mc_pct)}</td><td>{fmt(report.fine.effective_mc_pct)}</td></tr>
          <tr><td>Signed free water (kg/m³)</td><td>{fmt(report.water.free_water_ca_kg, 4)}</td><td>{fmt(report.water.free_water_fa_kg, 4)}</td></tr>
        </tbody></table></div><p className="caption">Negative contributions mean absorption from mixing water, not missing data.</p></section>
      <section><h3>02 · Follow effective water</h3><p className="equation">Weff = Wadded + Wfree,CA + Wfree,FA</p>
        <p>{fmt(report.water.added_water_kg, 4)} + ({fmt(report.water.free_water_ca_kg, 4)}) + ({fmt(report.water.free_water_fa_kg, 4)}) = <strong>{fmt(report.water.effective_water_kg, 4)} kg/m³</strong></p>
        <p className="equation">w/c = Weff / C</p><p>{fmt(report.water.effective_water_kg, 4)} / {fmt(report.cement_kg_m3, 4)} = <strong>{fmt(report.wc, 6)}</strong></p>
        <p>w/cm = {fmt(report.wcm, 6)}. Additional binder masses contribute to that denominator; their strength effects are not supported by these non-ML models.</p>
      </section>
      <section><h3>03 · Check occupied volume</h3><p className="equation">Vi = Wi / (SGi × 1000); Vair = air % / 100</p>
        <p>Aggregate SSD masses pair with SSD specific gravities. All volumes below are m³ per declared m³.</p>
        <div className="table-scroll"><table><tbody>{[['Cement', report.volumes.cement_m3], ['Other binder', report.volumes.scm_m3], ['Effective water', report.volumes.water_m3], ['Coarse aggregate', report.volumes.coarse_m3], ['Fine aggregate', report.volumes.fine_m3], ['Air', report.volumes.air_m3], ['Total', report.volumes.total_m3], ['Signed closure: total − 1', report.volumes.closure_error_m3]].map(([name, value]) => <tr key={String(name)}><th>{name}</th><td>{fmt(Number(value), 6)}</td></tr>)}</tbody></table></div>
        <p>Declared yield is an input. These calculations do not automatically remove an ingredient to close the volume.</p>
      </section>
      <section><h3>04 · Inspect the strength models</h3>{Object.entries(report.predictions).map(([name, model]) => <details key={name} className="source-row"><summary>{name === 'aci_table' ? 'ACI table' : pretty(name)} · {fmt(model.mean_28d_mpa)} MPa</summary><p className="equation">{equations[name] || 'See the model source.'}</p><p>State: w/c {fmt(report.wc, 6)}; Vc {fmt(report.volumes.cement_m3, 6)}, Vw {fmt(report.volumes.water_m3, 6)}, Va {fmt(report.volumes.air_m3, 6)} m³/m³.</p><p>{Object.entries(model.constants_used).map(([key, value]) => `${key} = ${fmt(value, 6)}`).join('; ') || 'Tabulated reference points; no fitted coefficient.'}</p><p>{model.constants_source}</p><p>{model.calibrated ? 'Parameters loaded from a stored fit; this is not proof of independent validation.' : 'Not calibrated to these local materials.'}</p></details>)}</section>
      <section><h3>05 · Adjust for age</h3><p className="equation">f(t) = f28 × t / (a + b × t)</p><p>Normalization, when selected, divides the factor by its value at 28 days. Conditions: {report.inputs.age_days} days, {pretty(report.inputs.curing || 'moist')} curing, cement Type {report.inputs.cement_type}.</p>
        {Object.entries(report.age_adjusted).map(([name, age]) => age && <p key={name}>{pretty(name)}: a = {age.a_days} days, b = {age.b}; factor {fmt(age.factor, 6)}; {age.normalised ? 'normalized' : 'literal'}; result <strong>{fmt(age.strength_mpa)} MPa</strong>.</p>)}
      </section>
      <section><h3>06 · Interpret the checks</h3><p>Mass per declared volume: {fmt(report.unit_weight.computed_kg_m3)} kg/m³. This is not a fresh-density test or a measurement of actual yield.</p><p>Air: {fmt(report.air_pct)}%, {report.air_source === 'user' ? 'explicit input' : 'reference-table assumption'}. Entrainer dosage does not predict achieved air.</p><p>Workability is inferred by inverting a mixing-water proportioning table. It is heuristic, ignores admixture effects and has no established statistical confidence band.</p><p><a href="#methods" className="text-link">Read methods, assumptions and source status →</a></p></section>
    </div>
  </details>;
}

export function ResearchContext({ report }: { report: Report }) {
  const volumeIssue = report.flags.find(flag => flag.code === 'VOLUME_CLOSURE');
  const rangeIssue = report.flags.some(flag => ['WC_MODEL_RANGE', 'STRENGTH_TABLE_RANGE', 'STRENGTH_LOOKUP'].includes(flag.code));
  const uncalibrated = Object.values(report.predictions).filter(model => !model.calibrated).length;
  return <section className="research-context" aria-label="Analysis context"><div><span className="eyebrow">Read this analysis in context</span><h2>Calculated, with assumptions.</h2></div><div className="context-facts">
    <p><strong>Volume closure</strong><span>{fmt(report.volumes.total_m3, 4)} m³/m³ · signed discrepancy {fmt(report.volumes.closure_error_m3, 4)}{volumeIssue ? ' · check flagged' : ' · no closure threshold exceeded'}</span></p>
    <p><strong>Model applicability</strong><span>{rangeIssue ? 'Range or lookup notices require review.' : 'No range notice at this mix; this is not proof of validity.'}</span></p>
    <p><strong>Parameter evidence</strong><span>{uncalibrated} of {Object.keys(report.predictions).length} models use uncalibrated references/parameters. Independent validation is not established here.</span></p>
    <p><strong>Moisture insight</strong><span>{report.water.free_water_ca_kg === 0 && report.water.free_water_fa_kg === 0 ? 'Both aggregate free-water contributions are zero under the selected basis.' : `Signed contributions: coarse ${fmt(report.water.free_water_ca_kg)} and fine ${fmt(report.water.free_water_fa_kg)} kg/m³. They are included in effective water.`}</span></p>
  </div></section>;
}

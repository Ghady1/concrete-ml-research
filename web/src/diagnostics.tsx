import { pretty, type Flag } from './api';

const descriptions: Record<string, [string, string]> = {
  VOLUME_CLOSURE: ['The mixture volume does not close', 'Check declared yield, ingredient quantities, air and matching mass/specific-gravity bases. The calculation does not rebalance quantities.'],
  UNCALIBRATED_MODEL: ['Parameters are not calibrated to these materials', 'Treat estimates as provisional. Use representative laboratory data and separate validation before making accuracy claims.'],
  MODEL_SPREAD: ['The strength models disagree', 'Inspect assumptions and constants. The spread is not a confidence interval; agreement would not establish accuracy either.'],
  WC_MODEL_RANGE: ['Water/cement ratio is outside the project range', 'Inspect effective water and moisture basis. A numerical answer outside the range is not evidence of applicability.'],
  STRENGTH_TABLE_RANGE: ['Strength is outside the reference table range', 'Review extrapolation and the source conditions. Do not interpret this as verified material performance.'],
  SLUMP_IGNORES_ADMIXTURES: ['Admixture effects are missing from workability', 'The inverse water table cannot represent these effects. Use a measured slump or a separately validated relationship.'],
  COURSE_MOISTURE_BASIS: ['Course moisture convention uses a teaching approximation', 'Compare the strict SSD-consistent field weights; confirm the intended convention with the professor.'],
  DURABILITY_MIN_FC: ['Specified strength is below the durability reference minimum', 'Review the durability class and target with the supervisor. The application has not silently raised the target or certified compliance.'],
  UNIT_WEIGHT_DEVIATION: ['Mass per declared volume differs from the reference', 'Inspect volume closure and material quantities. Compare with measured fresh density when available.'],
  SSD_MC_MISMATCH: ['SSD entry overrides the entered moisture', 'SSD basis has zero free water. Use as-received basis for actual stockpile weights and moisture.'],
  CUBE_FACTOR_MISSING: ['Cube conversion needs an explicit factor', 'Supply an accepted conversion factor for your specimens. Main predictions remain cylinder-based.'],
};
const limitations = new Set(['UNCALIBRATED_MODEL', 'UNVERIFIED_LITERATURE_PRESET', 'SCM_NOT_SUPPORTED', 'SUPERPLASTICIZER_NOT_MODELED', 'WATER_REDUCER_NOT_MODELED', 'SLUMP_IGNORES_ADMIXTURES', 'AIR_ENTRAINER_PRODUCT_SPECIFIC', 'CEMENT_TYPE_APPROXIMATION', 'AGE_MODEL_RANGE']);

export function Diagnostics({ flags, expanded = false }: { flags: Flag[]; expanded?: boolean }) {
  const groups = new Map<string, Flag[]>();
  for (const flag of flags) {
    const key = flag.severity + ':' + flag.code;
    groups.set(key, [...(groups.get(key) || []), flag]);
  }
  const categories = ['Calculation errors', 'Engineering checks', 'Research limitations', 'Information'];
  const category = (flag: Flag) => flag.severity === 'error' ? categories[0] : limitations.has(flag.code) ? categories[2] : flag.severity === 'info' ? categories[3] : categories[1];
  return <section className="checks"><h2>Checks & context</h2><p>Original severity and messages are retained. These checks describe research calculations, not structural approval.</p>{categories.map(name => {
    const entries = [...groups].filter(([, list]) => category(list[0]) === name);
    if (!entries.length) return null;
    return <div className="diagnostic-group" key={name}><h3>{name} <span className="badge">{entries.reduce((total, [, list]) => total + list.length, 0)}</span></h3>{entries.map(([key, list]) => {
      const flag = list[0];
      const [title, action] = descriptions[flag.code] || (flag.code.startsWith('SSD_MC_MISMATCH') ? descriptions.SSD_MC_MISMATCH : [pretty(flag.code), 'Inspect the values and source assumptions in “Show the engineering”; edit inputs and rerun if needed.']);
      return <details className={'flag ' + flag.severity} key={key} open={expanded || undefined}><summary><span>{title}</span><small>{flag.severity}{list.length > 1 ? ` · ${list.length} notices` : ''}</small></summary><p>{action}</p><div className="technical-messages"><strong>Detected values and technical detail</strong>{list.map((item, i) => <p key={i}>{item.message}</p>)}<code>{flag.code}</code></div></details>;
    })}</div>;
  })}{!flags.length && <p>No engine flags were returned. This does not establish experimental validation.</p>}</section>;
}

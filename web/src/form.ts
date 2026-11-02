import type { Metadata, MixInputs, ModeAInputs } from './api';
export type Unit = 'SI' | 'US';
export type Draft = Record<string, string | boolean>;
export type Mode = 'evaluate' | 'design';
export type FieldDef = { path: string; label: string; kind?: 'length' | 'stress' | 'density' | 'volume' | 'weight'; optional?: boolean; help?: string; choices?: string; text?: boolean };
export const materialFields = (mode: Mode): { title: string; description: string; fields: FieldDef[] }[] => [
  { title: 'Cement', description: 'The binder that brings the mixture together.', fields: [
    ...(mode === 'evaluate' ? [{ path: 'cement.weight_kg', label: 'Cement content', kind: 'weight' as const }, { path: 'cement.name', label: 'Cement name', text: true }] : []),
    { path: mode === 'evaluate' ? 'cement.sg' : 'cement_sg', label: 'Specific gravity', help: 'Density relative to water; dimensionless.' },
    { path: 'cement_type', label: 'Cement type', choices: 'cement_type' },
    ...(mode === 'evaluate' ? [{ path: 'cement_strength_class', label: 'Strength class', text: true, optional: true }] : [])] },
  { title: 'Coarse aggregate', description: 'Measured on a consistent SSD specific-gravity basis.', fields: [
    ...(mode === 'evaluate' ? [{ path: 'coarse_kg', label: 'Coarse aggregate', kind: 'weight' as const }] : []),
    { path: 'coarse.sg_ssd', label: 'SSD specific gravity' }, { path: 'coarse.drd_kg_m3', label: 'Dry-rodded density', kind: 'density' },
    { path: 'coarse.absorption_pct', label: 'Absorption (%)', help: 'Percentage of oven-dry mass.' },
    { path: 'coarse.mc_pct', label: 'Total moisture (%)', help: 'Includes absorbed and surface moisture; OD denominator.' },
    { path: 'coarse.shape', label: 'Particle shape', choices: 'shape' },
    { path: 'nmas_mm', label: 'Nominal maximum size', kind: 'length', optional: mode === 'design', help: mode === 'design' ? 'Clear this field to select size from geometry below.' : 'Nominal maximum size differs from maximum sieve size.' }] },
  { title: 'Fine aggregate', description: 'Sand properties and moisture determine both volume and free water.', fields: [
    ...(mode === 'evaluate' ? [{ path: 'fine_kg', label: 'Fine aggregate', kind: 'weight' as const }] : []),
    { path: 'fine.sg_ssd', label: 'Fine SSD specific gravity' }, { path: 'fine.absorption_pct', label: 'Fine absorption (%)' },
    { path: 'fine.mc_pct', label: 'Fine total moisture (%)' }, { path: 'fine.fm', label: 'Fineness modulus', help: 'An index of grading, not a particle size.' }] },
];
export const conditionFields: FieldDef[] = [
  { path: 'exposure', label: 'Exposure', choices: 'exposure' }, { path: 'curing', label: 'Curing', choices: 'curing' },
  { path: 'element', label: 'Element', choices: 'element', optional: true },
];
export const advancedFields = (mode: Mode): FieldDef[] => [
  { path: 'sigma_mpa', label: 'Strength standard deviation', kind: 'stress', optional: true },
  { path: 'n_samples', label: 'Number of strength results', optional: true, help: 'Leave blank if unavailable; never substitute zero for unknown.' },
  ...(mode === 'evaluate' ? [
    { path: 'admixtures.air_entrainer_ml_per_pct_per_100kg', label: 'Air-entrainer rate (ml / air % / 100 kg cement)', optional: true },
    { path: 'admixtures.water_reducer_pct', label: 'Water-reducer information (%)', optional: true, help: 'Mode B uses entered water; this percentage is not applied again.' },
    { path: 'admixtures.superplasticizer_kg', label: 'Superplasticizer', kind: 'weight' as const, optional: true },
    { path: 'specimen', label: 'Specimen', choices: 'specimen' },
    { path: 'cube_to_cylinder_factor', label: 'User cube-to-cylinder factor', optional: true, help: 'No default is assumed. Obtain an accepted factor for your specimens.' },
  ] : [
    { path: 'slump_target_mm', label: 'Slump target', kind: 'length' as const, optional: true, help: 'Blank uses the element’s reference maximum.' },
    { path: 'water_reducer_pct', label: 'Water reduction (%)', optional: true },
    { path: 'bb0_adjustment_factor', label: 'Coarse bulk-ratio adjustment' },
    ...['form_min_dimension_mm', 'rebar_clear_spacing_mm', 'cover_mm', 'slab_thickness_mm'].map(path => ({ path, label: path.replace('_mm', '').replaceAll('_', ' '), kind: 'length' as const, optional: true })),
  ]),
];
export function flatten(input: unknown, prefix = '', out: Record<string, unknown> = {}): Record<string, unknown> {
  if (input && typeof input === 'object' && !Array.isArray(input)) for (const [key, value] of Object.entries(input)) flatten(value, prefix ? prefix + '.' + key : key, out);
  else out[prefix] = input;
  return out;
}
export function draftFrom(inputs: MixInputs | ModeAInputs): Draft {
  return Object.fromEntries(Object.entries(flatten(inputs)).filter(([, v]) => !Array.isArray(v)).map(([k, v]) => [k, typeof v === 'boolean' ? v : v == null ? '' : String(v)]));
}
export function allFields(mode: Mode): FieldDef[] {
  return [...materialFields(mode).flatMap(g => g.fields), ...conditionFields, ...advancedFields(mode),
    { path: 'batch_volume_m3', label: 'Batch volume', kind: 'volume', optional: mode === 'evaluate' },
    { path: 'water_kg', label: 'Added water', kind: 'weight' }, { path: 'air_pct', label: 'Air (%)', optional: true },
    { path: 'age_days', label: 'Age (days)' }, { path: 'specified_fc_mpa', label: 'Specified strength', kind: 'stress' }];
}
export function factor(field: FieldDef, draft: Draft, metadata: Metadata): number {
  const c = metadata.conversion_factors;
  return field.kind === 'weight' ? (draft.batch_volume_m3 !== '' && draft.batch_volume_m3 != null ? c.KG_PER_LB : c.KG_M3_PER_LB_YD3)
    : field.kind === 'length' ? c.MM_PER_IN : field.kind === 'stress' ? c.MPA_PER_PSI
    : field.kind === 'density' ? c.KG_M3_PER_PCF : field.kind === 'volume' ? c.M3_PER_YD3 : 1;
}
export function fieldUnit(field: FieldDef, draft: Draft, unit: Unit) {
  if (field.kind === 'weight') return draft.batch_volume_m3 !== '' && draft.batch_volume_m3 != null ? (unit === 'SI' ? 'kg' : 'lb') : (unit === 'SI' ? 'kg/m³' : 'lb/yd³');
  return ({ length: unit === 'SI' ? 'mm' : 'in', stress: unit === 'SI' ? 'MPa' : 'psi', density: unit === 'SI' ? 'kg/m³' : 'pcf', volume: unit === 'SI' ? 'm³' : 'yd³' } as Record<string, string>)[field.kind || ''] || '';
}
export function switchUnits(draft: Draft, mode: Mode, to: Unit, metadata: Metadata): Draft {
  const result = { ...draft };
  for (const field of allFields(mode)) {
    const value = draft[field.path];
    if (field.kind && typeof value === 'string' && value.trim() && Number.isFinite(Number(value))) {
      const multiplier = factor(field, draft, metadata);
      result[field.path] = String(to === 'SI' ? Number(value) * multiplier : Number(value) / multiplier);
    }
  }
  return result;
}
function setPath(target: Record<string, unknown>, path: string, value: unknown) {
  const parts = path.split('.'); let cursor = target;
  for (const part of parts.slice(0, -1)) cursor = cursor[part] as Record<string, unknown>;
  cursor[parts.at(-1)!] = value;
}
export function materialize(draft: Draft, template: MixInputs | ModeAInputs, mode: Mode, unit: Unit, metadata: Metadata) {
  const output = structuredClone(template) as unknown as Record<string, unknown>;
  const errors: Record<string, string> = {};
  for (const [path, raw] of Object.entries(draft)) {
    const def = allFields(mode).find(f => f.path === path);
    if (typeof raw === 'boolean') { setPath(output, path, raw); continue; }
    if (Array.isArray(flatten(template)[path])) continue;
    if (def && !def.choices && !def.text) {
      if (!raw.trim()) { if (!def.optional) errors[path] = 'Enter a value.'; setPath(output, path, null); continue; }
      if (!/^[+-]?(?:\d+\.?\d*|\.\d+)(?:e[+-]?\d+)?$/i.test(raw.trim()) || !Number.isFinite(Number(raw))) { errors[path] = 'Enter a finite decimal number.'; continue; }
      setPath(output, path, Number(raw) * (unit === 'US' ? factor(def, draft, metadata) : 1));
    } else setPath(output, path, raw === '' ? null : raw);
  }
  return { inputs: output as unknown as MixInputs | ModeAInputs, errors };
}

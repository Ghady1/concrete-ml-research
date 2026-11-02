import { useId, useState, type ReactNode } from 'react';
import { Listbox, ListboxButton, ListboxOptions, ListboxOption, Label } from '@headlessui/react';
import { Check, ChevronDown, ArrowUpRight, ArrowRight, FlaskConical, Layers3, Ruler } from 'lucide-react';
import { pretty } from './api';

export function Logo({ large = false }: { large?: boolean }) {
  return <svg className={'logo ' + (large ? 'large' : '')} viewBox="0 0 64 64" role="img" aria-label="Concrete Research Studio mark">
    <path className="mark-stone" d="M8 31 22 21 35 28 31 45 14 45Z" fill="#bbc5b1"/>
    <path className="mark-specimen" d="M34 15 50 10 57 22 53 41 39 42 33 29Z" fill="#2a6257"/>
    <path className="mark-water" d="M26 4C26 4 18 14 18 17a8 8 0 0 0 16 0C34 14 26 4 26 4Z" fill="#b77553"/>
    <path d="M9 53H55" stroke="#25332f" strokeWidth="2"/>
  </svg>;
}
export function Select({ label, value, options, onChange, help }: {
  label: string; value: string; options: { value: string; label: string }[]; onChange: (v: string) => void; help?: string;
}) {
  return <div className="field"><Listbox value={value} onChange={onChange}>
      <Label className="field-label">{label}</Label>
      <ListboxButton className="select">{options.find(x => x.value === value)?.label || value}<ChevronDown size={16}/></ListboxButton>
      <ListboxOptions anchor="bottom start" modal={false} className="select-options">
        {options.map(option => <ListboxOption key={option.value} value={option.value} className="select-option">
          <span>{option.label}</span>{option.value === value && <Check size={16}/>}</ListboxOption>)}
      </ListboxOptions>
    </Listbox>{help && <small>{help}</small>}</div>;
}
export function Numeric({ label, value, onChange, help, optional = false, error }: {
  label: string; value: string; onChange: (v: string) => void; help?: string; optional?: boolean; error?: string;
}) {
  const id = useId();
  return <div className="field"><label htmlFor={id}>{label}{optional && <span className="optional"> optional</span>}</label>
    <input id={id} type="text" inputMode="decimal" autoComplete="off" value={value} onChange={e => onChange(e.target.value)}
      aria-invalid={!!error} aria-describedby={help || error ? id + '-help' : undefined} placeholder={optional ? 'Not specified' : undefined}/>
    {(help || error) && <small id={id + '-help'} className={error ? 'error-text' : ''}>{error || help}</small>}</div>;
}
export function Toggle({ label, checked, onChange, help }: { label: string; checked: boolean; onChange: (v: boolean) => void; help?: string }) {
  return <label className="toggle"><input type="checkbox" checked={checked} onChange={e => onChange(e.target.checked)}/>
    <span><strong>{label}</strong>{help && <small>{help}</small>}</span></label>;
}
export function Section({ title, eyebrow, children, id, description, companion }: { title: string; eyebrow?: string; children: ReactNode; id?: string; description?: string; companion?: ReactNode }) {
  return <section className="form-section" id={id}><div className={'section-heading' + (companion ? ' with-companion' : '')}><div>{eyebrow && <span className="eyebrow">{eyebrow}</span>}
    <h2>{title}</h2>{description && <p>{description}</p>}</div>{companion}</div>{children}</section>;
}
export function PageHeading({ eyebrow, title, children }: { eyebrow: string; title: string; children?: ReactNode }) {
  return <div className="page-heading"><span className="eyebrow">{eyebrow}</span><h1>{title}</h1>{children && <p>{children}</p>}</div>;
}
export function Home() {
  return <>
    <section className="hero"><div className="hero-copy"><div className="eyebrow"><span className="small-dot"/> A workspace for materials research</div>
      <h1>Understand a mix.<br/><em>Design with clarity.</em></h1>
      <p>From the water between the grains to the strength of a finished specimen. Bring concrete’s ingredients, methods and possibilities into view.</p>
      <div className="actions"><a className="button primary" href="#evaluate">Evaluate a mix <ArrowRight size={18}/></a>
        <a className="text-link" href="#examples">Explore a worked example <ArrowUpRight size={17}/></a></div>
      <div className="hero-note"><Logo/><span>Grounded in established methods.<br/>Made for thoughtful exploration.</span></div></div>
      <figure className="hero-image"><img src="/assets/concrete-architecture.webp" alt="Sunlight and shadow across sculptural architectural concrete"/>
        <figcaption><span>01 / MATERIAL PERSPECTIVES</span><strong>Simple ingredients.<br/>A remarkable material.</strong><span>Editorial photograph · not a project specimen</span></figcaption></figure></section>
    <section className="paths"><div className="section-intro"><span className="eyebrow">Choose your starting point</span><h2>Three ways to look closer.</h2></div>
      {[{ n: '01', title: 'Evaluate a mix', text: 'Begin with your batch weights. Follow the water corrections, explore strength models and understand the checks.', url: '#evaluate', icon: <FlaskConical/> },
        { n: '02', title: 'Design a mix', text: 'Start with a strength target. Work through ten clear steps, then see how the design predicts back.', url: '#design', icon: <Layers3/> },
        { n: '03', title: 'Calibrate with lab data', text: 'Bring your own observations. Fit coefficients to a material set and inspect what the residuals reveal.', url: '#calibration', icon: <Ruler/> }].map(x =>
          <a className="path-row" key={x.n} href={x.url}><span className="path-number">{x.n}</span><div className="path-icon">{x.icon}</div><h3>{x.title}</h3><p>{x.text}</p><ArrowUpRight/></a>)}
    </section><section className="material-story"><div className="material-images"><img src="/assets/coarse-aggregate.jpg" alt="Close view of real coarse aggregate stones" loading="lazy"/><img src="/assets/concrete-texture.webp" alt="Detailed texture of a concrete surface" loading="lazy"/></div>
      <div><span className="eyebrow">Ingredients → understanding</span><h2>The details make<br/>the difference.</h2><p>Moisture changes effective water. Aggregate changes the space available for paste. A small shift in water-to-cement ratio changes the strength estimate.</p><p>This studio makes those relationships visible, while keeping assumptions, reference sources and limits close at hand.</p><a className="text-link" href="#methods">Explore the methods <ArrowUpRight size={17}/></a></div></section>
    <section className="closing-note"><Logo large/><p>Observe carefully.<br/><em>Understand what follows.</em></p><a className="button" href="#examples">Open the guided demonstration <ArrowRight size={17}/></a></section>
  </>;
}
export function ComingWorkspace() {
  const [value, setValue] = useState('350'); const [basis, setBasis] = useState('ssd'); const [checked, setChecked] = useState(false);
  return <><PageHeading eyebrow="Studio workbench" title="A little clarity, before the calculation.">Your inputs stay in one scrollable workspace. Nothing changes just because you move the wheel.</PageHeading>
    <Section title="Material controls" description="These controls use ordinary text entry and nonmodal lists."><div className="fields"><Numeric label="Cement (kg/m³)" value={value} onChange={setValue}/><Select label="Aggregate basis" value={basis} options={['ssd', 'as_received', 'oven_dry'].map(value => ({ value, label: pretty(value) }))} onChange={setBasis}/></div><Toggle label="Air entrained" checked={checked} onChange={setChecked}/></Section><div style={{height:500}} aria-hidden="true"/></>;
}

import React, { useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { ArrowUpRight, MoveUpRight, Leaf } from 'lucide-react';
import { Home, Logo, ComingWorkspace, PageHeading } from './components';
import './style.css';

function App() {
  const [route, setRoute] = useState(location.hash.slice(1) || 'home');
  const [motion, setMotion] = useState(!matchMedia('(prefers-reduced-motion: reduce)').matches);
  useEffect(() => { const update = () => { setRoute(location.hash.slice(1) || 'home'); window.scrollTo(0, 0); }; addEventListener('hashchange', update); return () => removeEventListener('hashchange', update); }, []);
  return <div className={motion ? 'studio' : 'studio reduced-motion'}><a className="skip-link" href="#main">Skip to content</a>
    <header className="topbar"><a href="#home" className="brand"><Logo/><span>Concrete<br/><strong>Research Studio</strong></span></a>
      <nav aria-label="Main navigation">{[['evaluate', 'Evaluate'], ['design', 'Design'], ['calibration', 'Calibrate'], ['examples', 'Examples']].map(([to, label]) => <a key={to} href={'#' + to} aria-current={route.startsWith(to) ? 'page' : undefined}>{label}</a>)}</nav>
      <a className="about-link" href="#methods">Methods & sources <ArrowUpRight size={15}/></a></header>
    <main id="main">{route === 'home' ? <Home/> : ['evaluate', 'design'].includes(route) ? <ComingWorkspace/> : <PageHeading eyebrow="Research workspace" title={route === 'calibration' ? 'Calibrate with lab data.' : route === 'examples' ? 'Follow a worked example.' : 'Methods, with the context intact.'}>The studio’s next workspace is being connected to the numerical engine.</PageHeading>}</main>
    <footer className="footer"><div className="footer-brand"><Logo/><span>Concrete Research Studio<br/><small>AI-Assisted Prediction of Sustainable Concrete Properties</small></span></div><div className="footer-links"><a href="#methods">Methods & limitations</a><a href="#credits">Photography & type</a><button onClick={() => setMotion(!motion)} aria-pressed={!motion}>Motion {motion ? 'on' : 'off'}</button></div></footer>
    <div className="research-strip"><span className="small-dot"/><span>Estimated mean strength (research prediction; NOT a certified structural design value).</span><span className="local-tag">LOCAL RESEARCH WORKSPACE</span></div></div>;
}
createRoot(document.getElementById('root')!).render(<React.StrictMode><App/></React.StrictMode>);

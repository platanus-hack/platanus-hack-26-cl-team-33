import React from 'react';
import ReactDOM from 'react-dom/client';
import { useState } from 'react';
import { Simulate } from './pages/Simulate';
import { Compare } from './pages/Compare';
import { useMock } from './api/client';
import './styles.css';
export function App() {
 const [page,setPage] = useState<'simulate'|'compare'>('simulate');
 return <><a href="#main" className="skip-link">Skip to content</a><header><div className="header-inner"><a className="brand" href="#" onClick={() => setPage('simulate')}><span className="brand-mark" aria-hidden="true">✳</span><span>BedFlow <b>Chile</b><small>Hospital Flow Simulation Lab</small></span></a><nav aria-label="Main navigation"><button aria-current={page === 'simulate' ? 'page' : undefined} onClick={() => setPage('simulate')}>Simulate</button><button aria-current={page === 'compare' ? 'page' : undefined} onClick={() => setPage('compare')}>Compare</button></nav><span className="mode"><i className="status-dot"/>{useMock ? 'Fixture mode' : 'HTTP API mode'}</span></div></header><div className="context-strip">SYNTHETIC MODEL <span>Fictional hospital · Uncalibrated assumptions · Not validated for real hospital decisions</span></div><main id="main">{page === 'simulate' ? <Simulate/> : <Compare/>}<aside className="policy-note"><strong>A policy target, not a prediction.</strong><span>MINSAL’s ≥85% within 12 hours is a policy target used as reference context. It is not measured hospital performance. This lab explores hypothetical interventions, using synthetic assumptions.</span></aside></main><footer><span>BEDFLOW CHILE <span className="footer-dot">/</span> SIMULATION LAB</span><span>Understand the constraints. Explore the possibilities.</span></footer></>;
}
ReactDOM.createRoot(document.getElementById('root')!).render(<React.StrictMode><App/></React.StrictMode>);

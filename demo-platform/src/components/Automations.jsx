import { useState, useEffect, useCallback } from 'react';
import { automations } from '../data/mockData';

function SimulationModal({ automation, onClose }) {
  const [activeStep, setActiveStep] = useState(-1);
  const [done, setDone] = useState(false);

  useEffect(() => {
    if (!automation) return;
    let step = 0;
    let totalDelay = 300;

    const timers = automation.steps.map((s, i) => {
      const timer = setTimeout(() => {
        setActiveStep(i);
        step = i;
      }, totalDelay);
      totalDelay += s.delay;
      return timer;
    });

    const doneTimer = setTimeout(() => setDone(true), totalDelay + 400);
    timers.push(doneTimer);

    return () => timers.forEach(clearTimeout);
  }, [automation]);

  if (!automation) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-title">{automation.name}</div>

        <div className="sim-steps">
          {automation.steps.map((step, i) => (
            <div key={i} className={`sim-step ${i <= activeStep ? 'active' : ''}`}>
              <div className="sim-step-icon">{step.icon}</div>
              <div className="sim-step-label">{step.label}</div>
              {i < automation.steps.length - 1 && <div className="sim-step-line" />}
            </div>
          ))}
        </div>

        {done && (
          <div className="sim-done">
            Automation complete — {automation.stats}
          </div>
        )}

        <button
          className="simulate-btn"
          style={{ marginTop: 20 }}
          onClick={onClose}
        >
          Close
        </button>
      </div>
    </div>
  );
}

function AutomationCard({ automation, onSimulate }) {
  return (
    <div className="automation-card">
      <div className="auto-card-header">
        <div className="auto-card-title">{automation.name}</div>
        <div className="auto-card-status">
          <span className="auto-card-dot" />
          Active
        </div>
      </div>

      <div className="auto-card-flow">
        <div className="auto-card-trigger">
          <strong>Trigger:</strong> {automation.trigger}
        </div>
        <div className="auto-card-arrow">{'\u2193'}</div>
        <div className="auto-card-action">
          <strong>Action:</strong> {automation.action}
        </div>
      </div>

      <div className="auto-card-stats">{automation.stats}</div>

      <button className="simulate-btn" onClick={() => onSimulate(automation)}>
        {'\u25B6'} Simulate
      </button>
    </div>
  );
}

export default function Automations() {
  const [simulating, setSimulating] = useState(null);

  const handleSimulate = useCallback((automation) => {
    setSimulating({ ...automation });
  }, []);

  return (
    <>
      <div className="page-header">
        <h1>Automations</h1>
        <p>Interactive automation simulator — click Simulate to see each workflow in action</p>
      </div>

      <div className="automations-grid">
        {automations.map((a) => (
          <AutomationCard key={a.id} automation={a} onSimulate={handleSimulate} />
        ))}
      </div>

      {simulating && (
        <SimulationModal
          automation={simulating}
          onClose={() => setSimulating(null)}
        />
      )}
    </>
  );
}

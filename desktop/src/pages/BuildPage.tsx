import { useState } from 'react';

type WizardStep = 'describe' | 'review' | 'compile' | 'flash';

function BuildPage() {
  const [step, setStep] = useState<WizardStep>('describe');
  const [intent, setIntent] = useState('');

  const steps: { key: WizardStep; label: string }[] = [
    { key: 'describe', label: '1. Describe' },
    { key: 'review', label: '2. Review IR' },
    { key: 'compile', label: '3. Compile' },
    { key: 'flash', label: '4. Flash' },
  ];

  return (
    <div>
      <div className="page-header">
        <h2>Build & Flash</h2>
        <p>Describe what you want in plain English</p>
      </div>

      <div className="wizard-steps">
        {steps.map(s => (
          <div
            key={s.key}
            className={`wizard-step ${
              s.key === step ? 'active' :
              steps.findIndex(x => x.key === s.key) < steps.findIndex(x => x.key === step) ? 'completed' :
              'pending'
            }`}
            onClick={() => setStep(s.key)}
          >
            {s.label}
          </div>
        ))}
      </div>

      {step === 'describe' && (
        <div className="card">
          <h3 style={{ marginBottom: 12 }}>What should your device do?</h3>
          <textarea
            className="code-input"
            placeholder="Example: Read temperature from BME280 every 5 seconds. If above 30°C, turn on the relay. Show the reading on the OLED display."
            value={intent}
            onChange={e => setIntent(e.target.value)}
          />
          <div style={{ marginTop: 12, display: 'flex', justifyContent: 'flex-end' }}>
            <button
              className="btn btn-primary"
              disabled={!intent.trim()}
              onClick={() => setStep('review')}
            >
              Generate IR →
            </button>
          </div>
        </div>
      )}

      {step === 'review' && (
        <div className="card">
          <h3 style={{ marginBottom: 12 }}>Review Generated IR</h3>
          <p style={{ color: 'var(--text-secondary)' }}>
            Connect to the backend (localhost:8400) to generate and review the IR document.
          </p>
          <div style={{ marginTop: 12, display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
            <button className="btn" onClick={() => setStep('describe')}>← Back</button>
            <button className="btn btn-primary" onClick={() => setStep('compile')}>Compile →</button>
          </div>
        </div>
      )}

      {step === 'compile' && (
        <div className="card">
          <h3 style={{ marginBottom: 12 }}>Compile to Bytecode</h3>
          <p style={{ color: 'var(--text-secondary)' }}>
            The IR document will be compiled into signed bytecode (Ed25519).
          </p>
          <div style={{ marginTop: 12, display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
            <button className="btn" onClick={() => setStep('review')}>← Back</button>
            <button className="btn btn-primary" onClick={() => setStep('flash')}>Flash →</button>
          </div>
        </div>
      )}

      {step === 'flash' && (
        <div className="card">
          <h3 style={{ marginBottom: 12 }}>Flash to Device</h3>
          <p style={{ color: 'var(--text-secondary)' }}>
            Connect your ESP32-S3 via USB or select a device over WiFi/BLE to flash the bytecode.
          </p>
          <div style={{ marginTop: 12, display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
            <button className="btn" onClick={() => setStep('compile')}>← Back</button>
            <button className="btn btn-primary">Flash Device</button>
          </div>
        </div>
      )}
    </div>
  );
}

export default BuildPage;

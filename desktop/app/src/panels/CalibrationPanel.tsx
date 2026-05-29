/**
 * CalibrationPanel — Guided sensor calibration wizard.
 * Walks user through multi-point calibration for analog sensors.
 */
import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Gauge, Check, ChevronRight, RefreshCw, Download } from 'lucide-react';

const API = 'http://localhost:8000/api/agent';

interface CalibrationPoint {
  label: string;
  reference: number;
  raw?: number;
}

interface CalibrationRecipe {
  unit: string;
  standard_points: CalibrationPoint[];
}

interface CalibrationResult {
  sensor_id: string;
  points: number;
  degree: number;
  r_squared: number;
  coefficients: number[];
  firmware_code: string;
}

export default function CalibrationPanel() {
  const [sensors, setSensors] = useState<string[]>([]);
  const [selectedSensor, setSelectedSensor] = useState('');
  const [recipe, setRecipe] = useState<CalibrationRecipe | null>(null);
  const [currentStep, setCurrentStep] = useState(0);
  const [rawInput, setRawInput] = useState('');
  const [result, setResult] = useState<CalibrationResult | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetch(`${API}/calibrate/sensors`)
      .then(r => r.json())
      .then(d => setSensors(d.sensors || []))
      .catch(() => {});
  }, []);

  const loadRecipe = async (sensorId: string) => {
    setSelectedSensor(sensorId);
    setResult(null);
    setCurrentStep(0);
    try {
      const res = await fetch(`${API}/calibrate/recipe/${sensorId}`);
      const data = await res.json();
      setRecipe(data.recipe || null);
    } catch { setRecipe(null); }
  };

  const submitPoint = async () => {
    if (!recipe || !rawInput) return;
    setLoading(true);
    const point = recipe.standard_points[currentStep];
    try {
      const res = await fetch(`${API}/calibrate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          sensor_id: selectedSensor,
          raw_value: parseFloat(rawInput),
          reference_value: point.reference,
        }),
      });
      const data = await res.json();
      setResult(data);

      if (currentStep < recipe.standard_points.length - 1) {
        setCurrentStep(s => s + 1);
      }
    } catch {}
    setRawInput('');
    setLoading(false);
  };

  const resetCalibration = () => {
    setSelectedSensor('');
    setRecipe(null);
    setResult(null);
    setCurrentStep(0);
    setRawInput('');
  };

  return (
    <div className="flex-1 p-8 overflow-y-auto bg-[var(--bg-tertiary)]">
      <div className="max-w-3xl mx-auto space-y-8">
        {/* Header */}
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-3" style={{ color: 'var(--text-primary)' }}>
            <Gauge size={24} /> Sensor Calibration
          </h1>
          <p className="text-sm mt-1" style={{ color: 'var(--text-muted)' }}>
            Multi-point polynomial calibration with NVS persistence. Results generate firmware code automatically.
          </p>
        </div>

        {/* Sensor Selection */}
        {!selectedSensor ? (
          <div className="space-y-4">
            <h2 className="text-sm font-semibold uppercase tracking-widest" style={{ color: 'var(--text-muted)' }}>
              Select Sensor to Calibrate
            </h2>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
              {sensors.map(s => (
                <button key={s} onClick={() => loadRecipe(s)}
                  className="p-4 border rounded-xl text-left hover:border-[var(--text-muted)] transition-colors bg-[var(--bg-primary)]"
                  style={{ borderColor: 'var(--border)' }}>
                  <div className="text-sm font-bold" style={{ color: 'var(--text-primary)' }}>
                    {s.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}
                  </div>
                  <div className="text-[10px] font-mono mt-1" style={{ color: 'var(--text-muted)' }}>{s}</div>
                </button>
              ))}
            </div>
          </div>
        ) : recipe ? (
          /* Calibration Wizard */
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-bold" style={{ color: 'var(--text-primary)' }}>
                Calibrating: {selectedSensor.replace(/_/g, ' ')}
              </h2>
              <button onClick={resetCalibration}
                className="flex items-center gap-2 text-xs font-semibold px-3 py-1.5 border rounded-lg hover:bg-[var(--bg-secondary)]"
                style={{ borderColor: 'var(--border)', color: 'var(--text-secondary)' }}>
                <RefreshCw size={12} /> Reset
              </button>
            </div>

            {/* Progress dots */}
            <div className="flex items-center gap-3">
              {recipe.standard_points.map((_, i) => (
                <div key={i} className="flex items-center gap-2">
                  <div className="w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold border-2 transition-colors"
                    style={{
                      borderColor: i <= currentStep ? 'var(--accent)' : 'var(--border)',
                      background: i < currentStep ? 'var(--accent)' : 'transparent',
                      color: i < currentStep ? 'white' : i === currentStep ? 'var(--accent)' : 'var(--text-muted)',
                    }}>
                    {i < currentStep ? <Check size={14} /> : i + 1}
                  </div>
                  {i < recipe.standard_points.length - 1 && (
                    <ChevronRight size={16} style={{ color: 'var(--border)' }} />
                  )}
                </div>
              ))}
            </div>

            {/* Current step */}
            <motion.div key={currentStep} initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }}
              className="p-6 border rounded-xl bg-[var(--bg-primary)]" style={{ borderColor: 'var(--border)' }}>
              <div className="text-xs font-semibold uppercase tracking-widest mb-2" style={{ color: 'var(--text-muted)' }}>
                Step {currentStep + 1} of {recipe.standard_points.length}
              </div>
              <h3 className="text-lg font-bold mb-2" style={{ color: 'var(--text-primary)' }}>
                {recipe.standard_points[currentStep].label}
              </h3>
              <p className="text-sm mb-6" style={{ color: 'var(--text-secondary)' }}>
                Place sensor in {recipe.standard_points[currentStep].label.toLowerCase()}.
                Enter the ADC raw reading shown on your device.
                Reference value: <strong>{recipe.standard_points[currentStep].reference} {recipe.unit}</strong>
              </p>

              <div className="flex gap-3">
                <input type="number" value={rawInput} onChange={e => setRawInput(e.target.value)}
                  placeholder="Raw ADC value (e.g. 2048)"
                  className="flex-1 px-4 py-3 border rounded-xl text-sm font-mono bg-[var(--bg-secondary)] outline-none focus:border-[var(--accent)]"
                  style={{ borderColor: 'var(--border)', color: 'var(--text-primary)' }}
                  onKeyDown={e => e.key === 'Enter' && submitPoint()} />
                <button onClick={submitPoint} disabled={!rawInput || loading}
                  className="px-6 py-3 rounded-xl text-sm font-bold disabled:opacity-50 transition-colors"
                  style={{ background: 'var(--accent)', color: 'white' }}>
                  {loading ? '...' : 'Submit'}
                </button>
              </div>
            </motion.div>

            {/* Result */}
            {result && (
              <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
                className="p-6 border rounded-xl bg-[var(--bg-primary)]" style={{ borderColor: 'var(--border)' }}>
                <h3 className="text-sm font-bold uppercase tracking-widest mb-4" style={{ color: 'var(--text-muted)' }}>
                  Calibration Result
                </h3>
                <div className="grid grid-cols-3 gap-4 mb-6">
                  <div className="p-3 border rounded-lg" style={{ borderColor: 'var(--border)' }}>
                    <div className="text-[10px] font-semibold uppercase" style={{ color: 'var(--text-muted)' }}>Points</div>
                    <div className="text-xl font-bold font-mono" style={{ color: 'var(--text-primary)' }}>{result.points}</div>
                  </div>
                  <div className="p-3 border rounded-lg" style={{ borderColor: 'var(--border)' }}>
                    <div className="text-[10px] font-semibold uppercase" style={{ color: 'var(--text-muted)' }}>R² Quality</div>
                    <div className="text-xl font-bold font-mono" style={{
                      color: result.r_squared > 0.99 ? 'var(--success)' : result.r_squared > 0.95 ? 'var(--warning)' : 'var(--error)'
                    }}>{result.r_squared.toFixed(6)}</div>
                  </div>
                  <div className="p-3 border rounded-lg" style={{ borderColor: 'var(--border)' }}>
                    <div className="text-[10px] font-semibold uppercase" style={{ color: 'var(--text-muted)' }}>Degree</div>
                    <div className="text-xl font-bold font-mono" style={{ color: 'var(--text-primary)' }}>{result.degree}</div>
                  </div>
                </div>

                {/* Generated firmware code */}
                <div className="relative">
                  <div className="text-[10px] font-semibold uppercase tracking-widest mb-2" style={{ color: 'var(--text-muted)' }}>
                    Generated Firmware Code
                  </div>
                  <pre className="p-4 rounded-lg text-xs font-mono overflow-x-auto bg-[var(--bg-tertiary)] border"
                    style={{ borderColor: 'var(--border)', color: 'var(--text-primary)' }}>
                    {result.firmware_code}
                  </pre>
                  <button className="absolute top-0 right-0 flex items-center gap-1 px-3 py-1 text-[10px] font-semibold rounded-lg border hover:bg-[var(--bg-secondary)]"
                    style={{ borderColor: 'var(--border)', color: 'var(--text-secondary)' }}
                    onClick={() => navigator.clipboard.writeText(result.firmware_code)}>
                    <Download size={10} /> Copy
                  </button>
                </div>
              </motion.div>
            )}
          </div>
        ) : (
          <div className="text-sm" style={{ color: 'var(--text-muted)' }}>Loading calibration recipe...</div>
        )}
      </div>
    </div>
  );
}

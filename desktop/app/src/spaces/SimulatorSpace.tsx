/**
 * SimulatorSpace (V2) — Wokwi-embedded hardware simulator.
 * Uses Wokwi iframe for real ESP32 simulation with serial monitor.
 */
import { useState, useRef, useEffect } from 'react';
import { Play, Square, RotateCcw, Monitor, Terminal, Cpu, Zap, ExternalLink, Maximize2 } from 'lucide-react';

const WOKWI_BASE = 'https://wokwi.com/projects/new/esp32';
const API = 'http://localhost:8000/api/agent';

export default function SimulatorSpace() {
  const [isRunning, setIsRunning] = useState(false);
  const [fullscreen, setFullscreen] = useState(false);
  const [serialOutput, setSerialOutput] = useState<string[]>([
    '[SYSTEM] Wokwi Simulator initialized',
    '[SYSTEM] Ready for firmware testing',
  ]);
  const iframeRef = useRef<HTMLIFrameElement>(null);
  const serialEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    serialEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [serialOutput]);

  const startSimulation = () => {
    setIsRunning(true);
    setSerialOutput(prev => [...prev,
      `[SIM] Starting firmware at ${new Date().toLocaleTimeString()}...`,
    ]);
    // Simulate boot sequence
    setTimeout(() => {
      setSerialOutput(prev => [...prev,
        '[BOOT] ESP32 rev1, 240MHz, 4MB Flash',
        '[WIFI] Connecting to network...',
        '[WIFI] Connected! IP: 192.168.1.42',
        '[SENSOR] BME280 initialized at 0x76',
        '[cal] calibrator OK',
        '[anomaly] OK',
        '[SENSOR] Temperature: 23.5°C, Humidity: 45.2%',
        '[pub] JSON published: {"ts":12345,"temperature":23.5,"humidity":45.2}',
      ]);
    }, 2000);
  };

  const stopSimulation = () => {
    setIsRunning(false);
    setSerialOutput(prev => [...prev, '[SIM] Execution halted.']);
  };

  const resetSimulation = () => {
    setIsRunning(false);
    setSerialOutput(['[SYSTEM] Simulator reset', '[SYSTEM] Ready for firmware testing']);
    if (iframeRef.current) {
      iframeRef.current.src = iframeRef.current.src;
    }
  };

  const runQuickTest = async () => {
    setSerialOutput(prev => [...prev, '[TEST] Running data interpretation...']);
    try {
      const res = await fetch(`${API}/interpret`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          readings: { temperature: 23.5, humidity: 45.2, pressure: 1013.25, co2: 450, pm25: 12 },
          context: 'Indoor air quality monitoring',
        }),
      });
      const data = await res.json();
      setSerialOutput(prev => [...prev,
        `[AI] Status: ${data.status}`,
        `[AI] Summary: ${data.summary}`,
        ...(data.anomalies || []).map((a: string) => `[AI] ⚠ ${a}`),
        ...(data.actions || []).map((a: string) => `[AI] → ${a}`),
      ]);
    } catch {
      setSerialOutput(prev => [...prev, '[AI] Backend offline — interpretation unavailable']);
    }
  };

  return (
    <div className="flex-1 flex flex-col gap-4 p-6 overflow-hidden">
      {/* Header bar */}
      <div className="flex items-center justify-between pb-4 border-b" style={{ borderColor: 'var(--border)' }}>
        <div className="flex items-center gap-3">
          <Monitor size={20} style={{ color: 'var(--text-secondary)' }} />
          <h1 className="text-base font-semibold" style={{ color: 'var(--text-primary)' }}>
            Hardware Simulator
          </h1>
          <div className="flex items-center gap-2 ml-4 px-2.5 py-1 rounded-md border"
            style={{ borderColor: 'var(--border)', background: 'var(--bg-secondary)' }}>
            <div className="w-2 h-2 rounded-full"
              style={{ background: isRunning ? 'var(--success)' : 'var(--text-muted)' }} />
            <span className="text-xs font-medium"
              style={{ color: isRunning ? 'var(--success)' : 'var(--text-muted)' }}>
              {isRunning ? 'Running' : 'Idle'}
            </span>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button onClick={runQuickTest}
            className="flex items-center gap-2 px-4 py-2 rounded-lg font-medium text-sm border transition-colors hover:bg-[var(--bg-secondary)] shadow-sm"
            style={{ borderColor: 'var(--border)', color: 'var(--accent)' }}>
            <Zap size={14} /> AI Interpret
          </button>
          {!isRunning ? (
            <button onClick={startSimulation}
              className="flex items-center gap-2 px-4 py-2 rounded-lg font-medium text-sm transition-colors shadow-sm"
              style={{ background: 'var(--text-primary)', color: 'var(--bg-primary)' }}>
              <Play size={14} /> Execute
            </button>
          ) : (
            <button onClick={stopSimulation}
              className="flex items-center gap-2 px-4 py-2 rounded-lg font-medium text-sm transition-colors shadow-sm"
              style={{ background: 'var(--error)', color: 'white' }}>
              <Square size={14} /> Halt
            </button>
          )}
          <button onClick={resetSimulation}
            className="flex items-center gap-2 px-4 py-2 rounded-lg font-medium text-sm border transition-colors hover:bg-[var(--bg-secondary)] shadow-sm"
            style={{ borderColor: 'var(--border)', color: 'var(--text-secondary)' }}>
            <RotateCcw size={14} /> Reset
          </button>
        </div>
      </div>

      {/* Simulator + Serial side-by-side */}
      <div className={`flex-1 grid ${fullscreen ? 'grid-cols-1' : 'grid-cols-2'} gap-4 min-h-0`}>
        {/* Wokwi Simulator Embed */}
        <div className="border rounded-lg flex flex-col overflow-hidden shadow-sm" style={{ borderColor: 'var(--border)', background: 'var(--bg-primary)' }}>
          <div className="px-4 py-2.5 border-b flex items-center justify-between bg-[var(--bg-secondary)]" style={{ borderColor: 'var(--border)' }}>
            <div className="flex items-center gap-2">
              <Cpu size={14} style={{ color: 'var(--text-secondary)' }} />
              <span className="text-xs font-semibold" style={{ color: 'var(--text-secondary)' }}>
                Wokwi ESP32 Simulator
              </span>
            </div>
            <div className="flex items-center gap-2">
              <button onClick={() => setFullscreen(f => !f)}
                className="p-1 rounded hover:bg-[var(--bg-primary)] transition-colors"
                title="Toggle fullscreen">
                <Maximize2 size={12} style={{ color: 'var(--text-muted)' }} />
              </button>
              <a href={WOKWI_BASE} target="_blank" rel="noopener noreferrer"
                className="p-1 rounded hover:bg-[var(--bg-primary)] transition-colors"
                title="Open in Wokwi">
                <ExternalLink size={12} style={{ color: 'var(--text-muted)' }} />
              </a>
            </div>
          </div>
          <div className="flex-1 relative">
            <iframe
              ref={iframeRef}
              src={WOKWI_BASE}
              className="absolute inset-0 w-full h-full border-0"
              title="Wokwi ESP32 Simulator"
              allow="cross-origin-isolated"
              sandbox="allow-scripts allow-same-origin allow-popups allow-forms"
            />
          </div>
        </div>

        {/* Serial Monitor */}
        {!fullscreen && (
          <div className="border rounded-lg flex flex-col overflow-hidden shadow-sm" style={{ borderColor: 'var(--border)', background: 'var(--bg-primary)' }}>
            <div className="px-4 py-2.5 border-b flex items-center gap-2 bg-[var(--bg-secondary)]" style={{ borderColor: 'var(--border)' }}>
              <Terminal size={14} style={{ color: 'var(--text-secondary)' }} />
              <span className="text-xs font-semibold" style={{ color: 'var(--text-secondary)' }}>
                Serial Monitor
              </span>
              <span className="ml-auto text-[10px] font-mono" style={{ color: 'var(--text-muted)' }}>
                115200 baud
              </span>
            </div>
            <div className="flex-1 overflow-y-auto p-4 font-mono text-xs leading-relaxed bg-[var(--bg-tertiary)]">
              {serialOutput.map((line, i) => (
                <div key={i} className="py-0.5" style={{
                  color: line.includes('[ERROR]') || line.includes('⚠') ? 'var(--error)' :
                         line.includes('[WARN]') ? 'var(--warning)' :
                         line.includes('[SIM]') ? 'var(--accent)' :
                         line.includes('[AI]') ? '#a855f7' :
                         line.includes('[SYSTEM]') ? 'var(--text-secondary)' :
                         line.includes('[TEST]') ? 'var(--accent)' :
                         line.includes('[cal]') || line.includes('[anomaly]') ? '#14b8a6' :
                         'var(--text-primary)'
                }}>
                  {line}
                </div>
              ))}
              <div ref={serialEndRef} />
            </div>
          </div>
        )}
      </div>

      {/* Virtual peripherals bar */}
      <div className="flex items-center gap-3 px-4 py-2.5 border rounded-lg shadow-sm" style={{ borderColor: 'var(--border)', background: 'var(--bg-secondary)' }}>
        <Zap size={14} style={{ color: 'var(--text-secondary)' }} />
        <span className="text-xs font-semibold" style={{ color: 'var(--text-secondary)' }}>Peripherals:</span>
        <div className="flex gap-2 flex-wrap">
          {['LED', 'BUTTON', 'I2C', 'SPI', 'UART', 'DHT22', 'OLED', 'RELAY', 'PWM', 'ADC'].map(p => (
            <span key={p} className="px-2.5 py-1 border rounded-md text-[10px] font-bold uppercase tracking-wider transition-colors bg-[var(--bg-primary)] hover:bg-[var(--bg-tertiary)]"
              style={{ borderColor: 'var(--border)', color: 'var(--text-primary)' }}>
              {p}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}

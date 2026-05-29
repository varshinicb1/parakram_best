/**
 * VerificationSpace — Hardware verification checklist.
 * Users tick features as ✅ working or ❌ broken, with AI improvement suggestions.
 */
import { useState } from 'react';
import { CheckCircle2, XCircle, Lightbulb, ClipboardCheck, Send } from 'lucide-react';

interface FeatureCheck {
  id: string;
  name: string;
  description: string;
  status: 'pending' | 'pass' | 'fail';
  suggestion?: string;
  userNote?: string;
}

const INITIAL_FEATURES: FeatureCheck[] = [
  { id: 'wifi', name: 'WiFi Connection', description: 'Device connects to configured WiFi network', status: 'pending' },
  { id: 'mqtt', name: 'MQTT Communication', description: 'Device publishes telemetry to MQTT broker', status: 'pending' },
  { id: 'sensor_read', name: 'Sensor Reading', description: 'Primary sensor returns valid data', status: 'pending' },
  { id: 'display', name: 'Display Output', description: 'OLED/LCD shows correct information', status: 'pending' },
  { id: 'serial', name: 'Serial Debug', description: 'Debug messages appear on serial monitor', status: 'pending' },
  { id: 'power', name: 'Power Management', description: 'Deep sleep / wake cycles work correctly', status: 'pending' },
  { id: 'ota', name: 'OTA Updates', description: 'Over-the-air firmware update works', status: 'pending' },
  { id: 'error_handling', name: 'Error Recovery', description: 'Device recovers gracefully from errors', status: 'pending' },
];

export default function VerificationSpace() {
  const [features, setFeatures] = useState<FeatureCheck[]>(INITIAL_FEATURES);
  const [noteInput, setNoteInput] = useState<Record<string, string>>({});

  const toggleStatus = (id: string, status: 'pass' | 'fail') => {
    setFeatures(prev => prev.map(f => {
      if (f.id === id) {
        const newF = { ...f, status };
        if (status === 'fail') {
          // Generate AI suggestion
          newF.suggestion = generateSuggestion(f.name);
        }
        return newF;
      }
      return f;
    }));
  };

  const generateSuggestion = (featureName: string): string => {
    const suggestions: Record<string, string> = {
      'WiFi Connection': 'CHECK: 1) WiFi credentials in config 2) Signal strength 3) Add retry logic with exponential backoff 4) Log RSSI value',
      'MQTT Communication': 'CHECK: 1) Broker URL/port 2) Client ID uniqueness 3) QoS level 4) Add last-will-testament for disconnect detection',
      'Sensor Reading': 'CHECK: 1) I2C address match 2) Pull-up resistors 3) Initialization delay 4) Add CRC validation for sensor data',
      'Display Output': 'CHECK: 1) I2C bus conflict 2) Display reset pin 3) Font rendering buffer 4) Clear display before write',
      'Serial Debug': 'CHECK: 1) Baud rate mismatch 2) TX/RX pin assignment 3) Buffer overflow 4) Use Serial.flush()',
      'Power Management': 'CHECK: 1) Wake source config 2) RTC memory preservation 3) GPIO hold state 4) Add wake reason logging',
      'OTA Updates': 'CHECK: 1) Partition scheme (min 2 OTA) 2) Flash size 3) HTTPS certificate 4) Add progress callback',
      'Error Recovery': 'CHECK: 1) Watchdog timer config 2) Stack overflow detection 3) Exception handler 4) Add crash counter in NVS',
    };
    return suggestions[featureName] || 'ANALYZE SERIAL OUTPUT FOR ERROR CODES AND UPDATE FIRMWARE ACCORDINGLY';
  };

  const addNote = (id: string) => {
    const note = noteInput[id];
    if (!note) return;
    setFeatures(prev => prev.map(f =>
      f.id === id ? { ...f, userNote: note } : f
    ));
    setNoteInput(prev => ({ ...prev, [id]: '' }));
  };

  const passCount = features.filter(f => f.status === 'pass').length;
  const failCount = features.filter(f => f.status === 'fail').length;
  const totalCount = features.length;

  return (
    <div className="flex-1 overflow-y-auto">
      <div className="max-w-4xl mx-auto px-8 py-10 flex flex-col gap-6">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <ClipboardCheck size={28} style={{ color: 'var(--text-primary)' }} />
            <div>
              <h1 className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>
                Hardware Verification
              </h1>
              <p className="text-sm font-medium mt-1" style={{ color: 'var(--text-muted)' }}>
                Automated and manual checks for firmware capabilities.
              </p>
            </div>
          </div>

          {/* Score */}
          <div className="flex items-center gap-6 bg-[var(--bg-secondary)] border rounded-xl px-5 py-3 shadow-sm" style={{ borderColor: 'var(--border)' }}>
            <div className="flex items-center gap-2">
              <CheckCircle2 size={18} style={{ color: '#22c55e' }} />
              <span className="text-sm font-bold" style={{ color: '#22c55e' }}>
                {passCount} Passed
              </span>
            </div>
            <div className="flex items-center gap-2">
              <XCircle size={18} style={{ color: '#ef4444' }} />
              <span className="text-sm font-bold" style={{ color: '#ef4444' }}>
                {failCount} Failed
              </span>
            </div>
            <div className="pl-6 border-l" style={{ borderColor: 'var(--border)' }}>
              <span className="text-lg font-bold" style={{ color: 'var(--text-primary)' }}>
                {Math.round((passCount / totalCount) * 100)}%
              </span>
            </div>
          </div>
        </div>

        {/* Progress bar */}
        <div className="w-full h-2 rounded-full overflow-hidden bg-[var(--bg-secondary)] border shadow-inner" style={{ borderColor: 'var(--border)' }}>
          <div className="h-full transition-all duration-500 rounded-full" style={{
            width: `${(passCount / totalCount) * 100}%`,
            background: '#22c55e',
          }} />
        </div>

        {/* Feature checklist */}
        <div className="flex flex-col gap-4">
          {features.map((feature) => (
            <div key={feature.id}
              className="bg-[var(--bg-primary)] border rounded-xl overflow-hidden transition-shadow hover:shadow-md" style={{
                borderColor: feature.status === 'pass' ? '#22c55e' :
                             feature.status === 'fail' ? '#ef4444' : 'var(--border)',
              }}>
              <div className="p-5 flex items-center justify-between">
                <div>
                  <h3 className="text-base font-bold" style={{ color: 'var(--text-primary)' }}>
                    {feature.name}
                  </h3>
                  <p className="text-sm mt-1" style={{ color: 'var(--text-muted)' }}>
                    {feature.description}
                  </p>
                </div>

                <div className="flex items-center gap-3 shrink-0 ml-4">
                  <button onClick={() => toggleStatus(feature.id, 'pass')}
                    className="p-2.5 rounded-lg border transition-all hover:scale-105"
                    style={{
                      borderColor: feature.status === 'pass' ? '#22c55e' : 'var(--border)',
                      background: feature.status === 'pass' ? '#22c55e15' : 'var(--bg-secondary)',
                      color: feature.status === 'pass' ? '#22c55e' : 'var(--text-muted)',
                    }}>
                    <CheckCircle2 size={20} />
                  </button>
                  <button onClick={() => toggleStatus(feature.id, 'fail')}
                    className="p-2.5 rounded-lg border transition-all hover:scale-105"
                    style={{
                      borderColor: feature.status === 'fail' ? '#ef4444' : 'var(--border)',
                      background: feature.status === 'fail' ? '#ef444415' : 'var(--bg-secondary)',
                      color: feature.status === 'fail' ? '#ef4444' : 'var(--text-muted)',
                    }}>
                    <XCircle size={20} />
                  </button>
                </div>
              </div>

              {/* Extras (Suggestion & Note) */}
              <div className="px-5 pb-5">
                {/* AI Suggestion for failed features */}
                {feature.status === 'fail' && feature.suggestion && (
                  <div className="mt-2 p-4 border rounded-xl" style={{ borderColor: '#d9770640', background: '#d9770608' }}>
                    <div className="flex items-center gap-2 mb-2">
                      <Lightbulb size={16} style={{ color: '#d97706' }} />
                      <span className="text-xs font-bold uppercase tracking-wider" style={{ color: '#d97706' }}>
                        AI Suggestion
                      </span>
                    </div>
                    <p className="text-sm font-medium leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
                      {feature.suggestion}
                    </p>
                  </div>
                )}

                {/* User note input for failed features */}
                {feature.status === 'fail' && (
                  <div className="mt-3 flex items-center gap-2">
                    <input
                      value={noteInput[feature.id] || ''}
                      onChange={(e) => setNoteInput(prev => ({ ...prev, [feature.id]: e.target.value }))}
                      placeholder="Add an observation note or troubleshooting step..."
                      className="flex-1 bg-[var(--bg-secondary)] border rounded-lg px-4 py-2.5 text-sm font-medium outline-none focus:border-[var(--text-primary)] transition-colors shadow-sm"
                      style={{ borderColor: 'var(--border)', color: 'var(--text-primary)' }}
                    />
                    <button onClick={() => addNote(feature.id)}
                      className="p-3 bg-[var(--text-primary)] rounded-lg text-white transition-transform hover:scale-105" style={{ color: 'var(--bg-primary)' }}>
                      <Send size={16} />
                    </button>
                  </div>
                )}

                {feature.userNote && (
                  <div className="mt-3 text-sm font-medium px-4 py-3 border rounded-xl bg-[var(--bg-secondary)]"
                    style={{ borderColor: 'var(--border)', color: 'var(--text-secondary)' }}>
                    <strong>Note:</strong> {feature.userNote}
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

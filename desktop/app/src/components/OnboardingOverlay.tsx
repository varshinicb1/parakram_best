/**
 * OnboardingOverlay — First-time user guide with step-by-step walkthrough.
 * Shows on first launch, remembers dismissal in localStorage.
 * Interactive tour highlighting each major feature area.
 */
import { useState, useEffect } from 'react';
import { useAppStore, type Space } from '../stores/appStore';
import {
  X, ChevronRight, ChevronLeft, Rocket, Sparkles,
  PenTool, Blocks, MonitorPlay, Cpu, Activity, Bug,
  Gauge, ShieldCheck, Settings, Download, Puzzle,
} from 'lucide-react';

interface Step {
  title: string;
  description: string;
  icon: React.ElementType;
  space?: Space;
  tip: string;
}

const ONBOARDING_STEPS: Step[] = [
  {
    title: 'Welcome to Parakram',
    description: 'The world\'s most advanced AI-powered firmware generation platform. Describe what you want to build in plain English — we generate production-ready firmware.',
    icon: Rocket,
    space: 'home',
    tip: 'Start by typing a project idea on the Home screen, like "weather station with BME280 and OLED display".',
  },
  {
    title: 'Visual Designer',
    description: 'Drag and drop from 202 golden blocks onto the XY Flow canvas. Connect components visually and generate firmware with one click.',
    icon: PenTool,
    space: 'designer',
    tip: 'Click any block from the left palette to add it to the canvas. Blocks auto-connect to your MCU.',
  },
  {
    title: 'Blockly Editor',
    description: 'Google Blockly visual programming with 13 custom firmware blocks. Snap together GPIO, WiFi, MQTT, sensors, and RTOS — code generates in real-time.',
    icon: Blocks,
    space: 'blockly',
    tip: 'Drag blocks from the left toolbox. Your C++ code appears live in the right panel.',
  },
  {
    title: 'Wokwi Simulator',
    description: 'Test your firmware in a virtual ESP32 before touching real hardware. Full serial monitor and AI-powered output interpretation.',
    icon: MonitorPlay,
    space: 'simulator',
    tip: 'Use "AI Interpret" to have the LLM explain what your serial output means.',
  },
  {
    title: 'Device Management',
    description: 'Scan for connected USB devices with automatic board detection (ESP32, STM32, RP2040). Flash firmware in one click using esptool.',
    icon: Cpu,
    space: 'devices',
    tip: 'Connect your board via USB, click "Scan Ports" — we identify your board by VID:PID.',
  },
  {
    title: 'Live Telemetry',
    description: 'Real-time sensor data visualization with 3-channel Recharts. Export data as CSV for analysis.',
    icon: Activity,
    space: 'telemetry',
    tip: 'Connect a device and telemetry data streams live into the dashboard.',
  },
  {
    title: 'Debug Console',
    description: 'Professional debugging: serial monitor, protocol analyzer, crash decoder, and I2C bus scanner.',
    icon: Bug,
    space: 'debug',
    tip: 'Use the crash decoder to parse ESP32 backtrace dumps into human-readable stack traces.',
  },
  {
    title: 'Sensor Calibration',
    description: 'Guided multi-point calibration wizard. Computes polynomial fit, R² quality score, and generates C calibration code.',
    icon: Gauge,
    space: 'calibration',
    tip: 'Select a sensor recipe (pH, temperature, etc.), enter reference points, and get calibrated firmware code.',
  },
  {
    title: 'Verification Suite',
    description: 'Hardware-ready checklist with AI-generated suggestions. Track your progress toward a deployable product.',
    icon: ShieldCheck,
    space: 'verification',
    tip: 'Use this before deploying to production — it catches common hardware mistakes.',
  },
  {
    title: 'Settings & LLM Providers',
    description: 'Configure 6 LLM providers (OpenAI, Anthropic, Gemini, Ollama, Groq, Mistral), manage API keys, themes, and billing.',
    icon: Settings,
    space: 'settings',
    tip: 'Set your preferred LLM provider in Settings → AI to get the best code generation results.',
  },
  {
    title: 'Toolchain Installer',
    description: 'One-click install for PlatformIO, ESP-IDF, Arduino CLI, and 10 popular libraries. Never configure a toolchain manually again.',
    icon: Download,
    space: 'installer',
    tip: 'Install PlatformIO first — it integrates with everything else automatically.',
  },
  {
    title: 'Extensions Marketplace',
    description: 'Browse and install community extensions to add new blocks, board support, or integrations.',
    icon: Puzzle,
    space: 'extensions',
    tip: 'Check the marketplace regularly — new sensor blocks and board profiles are added weekly.',
  },
];

const STORAGE_KEY = 'parakram_onboarding_complete';

export default function OnboardingOverlay() {
  const [visible, setVisible] = useState(false);
  const [step, setStep] = useState(0);
  const setActiveSpace = useAppStore(s => s.setActiveSpace);

  useEffect(() => {
    const done = localStorage.getItem(STORAGE_KEY);
    if (!done) setVisible(true);
  }, []);

  const dismiss = () => {
    setVisible(false);
    localStorage.setItem(STORAGE_KEY, 'true');
  };

  const goNext = () => {
    if (step < ONBOARDING_STEPS.length - 1) {
      const nextStep = step + 1;
      setStep(nextStep);
      if (ONBOARDING_STEPS[nextStep].space) {
        setActiveSpace(ONBOARDING_STEPS[nextStep].space!);
      }
    } else {
      dismiss();
    }
  };

  const goPrev = () => {
    if (step > 0) {
      const prevStep = step - 1;
      setStep(prevStep);
      if (ONBOARDING_STEPS[prevStep].space) {
        setActiveSpace(ONBOARDING_STEPS[prevStep].space!);
      }
    }
  };

  if (!visible) return null;

  const current = ONBOARDING_STEPS[step];
  const Icon = current.icon;
  const progress = ((step + 1) / ONBOARDING_STEPS.length) * 100;

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center"
      style={{ background: 'rgba(0,0,0,0.7)', backdropFilter: 'blur(8px)' }}>

      <div className="w-[520px] rounded-2xl border overflow-hidden shadow-2xl"
        style={{ background: 'var(--bg-secondary)', borderColor: 'var(--border)' }}>

        {/* Progress bar */}
        <div className="h-1 bg-[var(--bg-primary)]">
          <div className="h-full transition-all duration-500 ease-out rounded-r"
            style={{ width: `${progress}%`, background: 'var(--accent)' }} />
        </div>

        {/* Header */}
        <div className="flex items-center justify-between px-6 pt-5 pb-2">
          <div className="flex items-center gap-2">
            <Sparkles size={16} style={{ color: 'var(--accent)' }} />
            <span className="text-[11px] font-bold tracking-wider uppercase"
              style={{ color: 'var(--text-muted)' }}>
              Getting Started — {step + 1}/{ONBOARDING_STEPS.length}
            </span>
          </div>
          <button onClick={dismiss}
            className="p-1 rounded-lg hover:bg-[var(--bg-tertiary)] transition-colors"
            style={{ color: 'var(--text-muted)' }}>
            <X size={16} />
          </button>
        </div>

        {/* Content */}
        <div className="px-6 py-4 space-y-4">
          <div className="flex items-start gap-4">
            <div className="w-12 h-12 rounded-xl flex items-center justify-center shrink-0"
              style={{ background: 'var(--accent)', opacity: 0.9 }}>
              <Icon size={24} color="white" />
            </div>
            <div>
              <h3 className="text-lg font-bold mb-1" style={{ color: 'var(--text-primary)' }}>
                {current.title}
              </h3>
              <p className="text-sm leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
                {current.description}
              </p>
            </div>
          </div>

          {/* Tip box */}
          <div className="rounded-xl px-4 py-3 border"
            style={{
              background: 'rgba(99, 102, 241, 0.06)',
              borderColor: 'rgba(99, 102, 241, 0.15)',
            }}>
            <span className="text-[10px] font-bold uppercase tracking-wider block mb-1"
              style={{ color: 'var(--accent)' }}>
              💡 Pro Tip
            </span>
            <p className="text-xs leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
              {current.tip}
            </p>
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-6 py-4 border-t"
          style={{ borderColor: 'var(--border)' }}>
          <button onClick={dismiss}
            className="text-xs font-medium px-3 py-1.5 rounded-lg hover:bg-[var(--bg-tertiary)] transition-colors"
            style={{ color: 'var(--text-muted)' }}>
            Skip Tour
          </button>

          <div className="flex items-center gap-2">
            {step > 0 && (
              <button onClick={goPrev}
                className="flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-semibold border hover:bg-[var(--bg-tertiary)] transition-colors"
                style={{ borderColor: 'var(--border)', color: 'var(--text-secondary)' }}>
                <ChevronLeft size={14} /> Back
              </button>
            )}
            <button onClick={goNext}
              className="flex items-center gap-1 px-4 py-1.5 rounded-lg text-xs font-bold transition-colors"
              style={{ background: 'var(--accent)', color: 'white' }}>
              {step === ONBOARDING_STEPS.length - 1 ? 'Get Started!' : 'Next'}
              {step < ONBOARDING_STEPS.length - 1 && <ChevronRight size={14} />}
            </button>
          </div>
        </div>

        {/* Step indicators */}
        <div className="flex justify-center gap-1.5 pb-4">
          {ONBOARDING_STEPS.map((_, i: number) => (
            <div key={i}
              className="rounded-full transition-all duration-300"
              style={{
                width: i === step ? 20 : 6,
                height: 6,
                background: i === step ? 'var(--accent)' : i < step ? 'var(--text-muted)' : 'var(--border)',
              }} />
          ))}
        </div>
      </div>
    </div>
  );
}

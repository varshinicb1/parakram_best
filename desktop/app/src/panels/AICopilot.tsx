/**
 * AICopilot — Side panel for natural language interaction with the hardware graph.
 * Users talk to AI: "Add OLED display", "Explain my system", "Use deep sleep".
 */
import { useState, useCallback, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Sparkles, Send, X } from 'lucide-react';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: number;
}

interface Props {
  onClose: () => void;
}

const SUGGESTIONS = [
  'Add OLED display showing temperature',
  'Use deep sleep to save power',
  'Explain my system architecture',
  'Add BLE connectivity',
  'Optimize for low power',
];

export default function AICopilot({ onClose }: Props) {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 'welcome',
      role: 'assistant',
      content: 'SYSTEM ONLINE. AWAITING COMMANDS TO MODIFY OR EXPLAIN HARDWARE TOPOLOGY.',
      timestamp: Date.now(),
    },
  ]);
  const [input, setInput] = useState('');
  const [isThinking, setIsThinking] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' });
  }, [messages]);

  const sendMessage = useCallback(async (text: string) => {
    if (!text.trim() || isThinking) return;
    const userMsg: Message = { id: `u_${Date.now()}`, role: 'user', content: text, timestamp: Date.now() };
    setMessages((m) => [...m, userMsg]);
    setInput('');
    setIsThinking(true);

    // Simulate AI response (connect to backend in production)
    await new Promise((r) => setTimeout(r, 1200));

    let response = '';
    const lower = text.toLowerCase();
    if (lower.includes('explain') && lower.includes('system')) {
      response = 'SYSTEM ARCHITECTURE:\n\n• SENSOR TASK — READS SENSOR DATA EVERY 5 SECONDS\n• NETWORK TASK — MAINTAINS WIFI + MQTT CONNECTION\n• TELEMETRY TASK — PUBLISHES JSON PAYLOAD TO BROKER\n• DISPLAY TASK — UPDATES OLED WITH LATEST READINGS\n\nALL TASKS RUN ON FREERTOS WITH PROPER SEMAPHORE SYNCHRONIZATION.';
    } else if (lower.includes('oled') || lower.includes('display')) {
      response = 'INTEGRATED SSD1306 OLED DISPLAY BLOCK.\n\n• I2C ADDRESS: 0x3C\n• RESOLUTION: 128x64\n• SHOWS: TEMPERATURE, HUMIDITY, STATUS\n\nDISPLAY TASK UPDATES EVERY 2 SECONDS.';
    } else if (lower.includes('deep sleep') || lower.includes('power')) {
      response = 'INTEGRATED DEEP SLEEP BLOCK.\n\n• WAKE SOURCE: TIMER (5 MIN INTERVAL)\n• CURRENT DRAW IN SLEEP: ~10µA\n• ESTIMATED BATTERY LIFE: 6 MONTHS ON 2000MAH\n\nWAKE STUB CONFIGURED TO SKIP WIFI RECONNECTION FOR SENSOR-ONLY READS.';
    } else if (lower.includes('ble') || lower.includes('bluetooth')) {
      response = 'INTEGRATED BLE SERVER BLOCK.\n\n• SERVICE UUID: AUTO-GENERATED\n• CHARACTERISTICS: TEMPERATURE (NOTIFY), HUMIDITY (READ)\n• MTU: 512 BYTES\n\nMOBILE APPS CAN DISCOVER THIS DEVICE AS "PARAKRAM-WEATHER".';
    } else {
      response = `INPUT RECEIVED: "${text.toUpperCase()}"\n\nMODIFYING GRAPH TOPOLOGY. IN FULL DEPLOYMENT, THIS CONNECTS TO PARAKRAM AI ENGINE AT /API/AGENT/BUILD FOR REAL-TIME GRAPH MODIFICATION.`;
    }

    const aiMsg: Message = { id: `a_${Date.now()}`, role: 'assistant', content: response, timestamp: Date.now() };
    setMessages((m) => [...m, aiMsg]);
    setIsThinking(false);
  }, [isThinking]);

  return (
    <motion.div
      initial={{ x: 360, opacity: 0 }}
      animate={{ x: 0, opacity: 1 }}
      exit={{ x: 360, opacity: 0 }}
      transition={{ type: 'spring', damping: 25, stiffness: 300 }}
      className="w-[360px] border-l flex flex-col shrink-0"
      style={{ borderColor: 'var(--border)', background: 'var(--bg-secondary)' }}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b"
        style={{ borderColor: 'var(--border)' }}>
        <div className="flex items-center gap-2">
          <Sparkles size={16} style={{ color: 'var(--accent)' }} />
          <h2 className="text-xs font-semibold" style={{ color: 'var(--text-primary)' }}>AI Copilot</h2>
        </div>
        <button onClick={onClose} className="p-1 rounded-md hover:bg-white/5 border border-transparent hover:border-[var(--border)]" style={{ color: 'var(--text-muted)' }}>
          <X size={16} />
        </button>
      </div>

      {/* Messages */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto px-4 py-3 flex flex-col gap-3">
        {messages.map((msg) => (
          <motion.div
            key={msg.id}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-[85%] px-4 py-2.5 rounded-2xl text-xs font-mono leading-relaxed whitespace-pre-line border ${msg.role === 'user' ? 'rounded-br-sm' : 'rounded-bl-sm'}`}
              style={{
                background: msg.role === 'user' ? 'var(--accent)' : 'var(--bg-tertiary)',
                color: msg.role === 'user' ? '#fff' : 'var(--text-primary)',
                borderColor: msg.role === 'user' ? 'var(--accent)' : 'var(--border)',
                boxShadow: msg.role === 'user' ? '0 2px 4px rgba(37, 99, 235, 0.2)' : 'none',
              }}
            >
              {msg.content}
            </div>
          </motion.div>
        ))}
        <AnimatePresence>
          {isThinking && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
              className="flex items-center gap-2 px-3 py-2">
              <div className="flex gap-1">
                {[0, 1, 2].map((i) => (
                  <div key={i} className="w-1.5 h-1.5 rounded-full animate-pulse"
                    style={{ background: 'var(--accent)', animationDelay: `${i * 0.2}s` }} />
                ))}
              </div>
              <span className="text-[10px]" style={{ color: 'var(--text-muted)' }}>Thinking...</span>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Suggestions */}
      {messages.length <= 1 && (
        <div className="px-4 py-2 flex flex-wrap gap-1.5 border-t" style={{ borderColor: 'var(--border)' }}>
          {SUGGESTIONS.map((s) => (
            <button key={s} onClick={() => sendMessage(s)}
              className="px-3 py-1.5 rounded-lg border text-xs font-medium transition-all hover:bg-[var(--bg-tertiary)]"
              style={{ background: 'var(--bg-secondary)', color: 'var(--text-primary)', borderColor: 'var(--border)' }}>
              {s}
            </button>
          ))}
        </div>
      )}

      {/* Input */}
      <div className="px-3 py-3 border-t" style={{ borderColor: 'var(--border)' }}>
        <div className="flex items-center gap-2 bg-[var(--bg-primary)] px-3 py-2 rounded-xl border" style={{ borderColor: 'var(--border)' }}>
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && sendMessage(input)}
            placeholder="Ask AI Copilot..."
            className="flex-1 bg-transparent outline-none text-sm font-medium placeholder-[var(--text-muted)]"
            style={{ color: 'var(--text-primary)' }}
          />
          <motion.button
            onClick={() => sendMessage(input)}
            disabled={!input.trim() || isThinking}
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            className="p-2 rounded-lg border disabled:opacity-50 transition-colors shadow-sm"
            style={{ background: 'var(--accent)', color: 'white', borderColor: 'var(--accent)' }}
          >
            <Send size={12} />
          </motion.button>
        </div>
      </div>
    </motion.div>
  );
}

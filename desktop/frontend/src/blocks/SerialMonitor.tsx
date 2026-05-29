/**
 * SerialMonitor -- WebSocket-based real-time serial output viewer.
 * Shows ESP32 serial output with color-coded severity levels.
 */

import { useState, useEffect, useRef, useCallback } from 'react';
import { createSerialWebSocket } from '../api/apiClient';

interface SerialLine {
    type: string;
    data: string;
    timestamp: string;
    level?: string;
}

export default function SerialMonitor() {
    const [lines, setLines] = useState<SerialLine[]>([]);
    const [connected, setConnected] = useState(false);
    const [autoScroll, setAutoScroll] = useState(true);
    const [filter, setFilter] = useState('');
    const wsRef = useRef<WebSocket | null>(null);
    const scrollRef = useRef<HTMLDivElement>(null);
    const maxLines = 500;

    const connect = useCallback(() => {
        if (wsRef.current?.readyState === WebSocket.OPEN) return;

        const ws = createSerialWebSocket();
        wsRef.current = ws;

        ws.onopen = () => {
            setConnected(true);
            // Start mock serial
            ws.send(JSON.stringify({ command: 'start', config: { mock: true } }));
        };

        ws.onmessage = (event) => {
            try {
                const msg: SerialLine = JSON.parse(event.data);
                if (msg.type === 'rx' || msg.type === 'tx') {
                    setLines((prev) => {
                        const next = [...prev, msg];
                        return next.length > maxLines ? next.slice(-maxLines) : next;
                    });
                }
            } catch {
                // ignore non-JSON messages
            }
        };

        ws.onclose = () => setConnected(false);
        ws.onerror = () => setConnected(false);
    }, []);

    const disconnect = useCallback(() => {
        if (wsRef.current) {
            wsRef.current.send(JSON.stringify({ command: 'stop' }));
            wsRef.current.close();
            wsRef.current = null;
        }
        setConnected(false);
    }, []);

    useEffect(() => {
        return () => {
            wsRef.current?.close();
        };
    }, []);

    useEffect(() => {
        if (autoScroll && scrollRef.current) {
            scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
        }
    }, [lines, autoScroll]);

    const filteredLines = filter
        ? lines.filter((l) => l.data.toLowerCase().includes(filter.toLowerCase()))
        : lines;

    const levelColor = (level?: string) => {
        switch (level) {
            case 'error': return 'var(--accent-rose)';
            case 'warning': return 'var(--accent-amber)';
            case 'system': return 'var(--accent-violet)';
            default: return 'var(--text-secondary)';
        }
    };

    return (
        <div className="serial-monitor">
            <div className="serial-monitor__header">
                <div className="serial-monitor__title">
                    <span>📟 Serial Monitor</span>
                    <span
                        className="serial-monitor__status"
                        style={{ background: connected ? 'var(--accent-emerald)' : 'var(--text-muted)' }}
                    />
                </div>
                <div className="serial-monitor__controls">
                    <input
                        type="text"
                        className="serial-monitor__filter"
                        placeholder="Filter..."
                        value={filter}
                        onChange={(e) => setFilter(e.target.value)}
                    />
                    <button
                        className="serial-monitor__btn"
                        onClick={connected ? disconnect : connect}
                    >
                        {connected ? '⏹ Stop' : '▶ Start'}
                    </button>
                    <button
                        className="serial-monitor__btn"
                        onClick={() => setLines([])}
                    >
                        🗑 Clear
                    </button>
                    <button
                        className={`serial-monitor__btn ${autoScroll ? 'serial-monitor__btn--active' : ''}`}
                        onClick={() => setAutoScroll(!autoScroll)}
                    >
                        ↓ Auto
                    </button>
                </div>
            </div>
            <div ref={scrollRef} className="serial-monitor__output">
                {filteredLines.map((line, i) => (
                    <div
                        key={i}
                        className="serial-monitor__line"
                        style={{ color: levelColor(line.level) }}
                    >
                        <span className="serial-monitor__timestamp">{line.timestamp}</span>
                        <span className="serial-monitor__data">{line.data}</span>
                    </div>
                ))}
                {filteredLines.length === 0 && (
                    <div className="serial-monitor__empty">
                        {connected ? 'Waiting for data...' : 'Click Start to begin monitoring'}
                    </div>
                )}
            </div>
        </div>
    );
}

/**
 * SimulationViewer — Visualize block graph simulation with timeline data.
 */

import { useState } from 'react';
import { simulationApi } from '../api/apiClient';

interface TimelinePoint {
    time_ms: number;
    node_id: string;
    node_name: string;
    value: number;
}

interface SimResult {
    status: string;
    timeline: TimelinePoint[];
    statistics: Record<string, { min: number; max: number; avg: number }>;
    duration_seconds: number;
}

interface Props {
    projectId: string;
}

export default function SimulationViewer({ projectId }: Props) {
    const [result, setResult] = useState<SimResult | null>(null);
    const [running, setRunning] = useState(false);
    const [duration, setDuration] = useState(30);

    const runSimulation = async () => {
        setRunning(true);
        try {
            const data = await simulationApi.run(projectId, duration, 1000) as SimResult;
            setResult(data);
        } catch (err) {
            console.error('Simulation failed:', err);
        } finally {
            setRunning(false);
        }
    };

    return (
        <div className="simulation-viewer">
            <div className="simulation-viewer__header">
                <span>📊 Device Simulation</span>
                <div className="simulation-viewer__controls">
                    <label className="simulation-viewer__label">
                        Duration:
                        <select
                            className="simulation-viewer__select"
                            value={duration}
                            onChange={(e) => setDuration(Number(e.target.value))}
                        >
                            <option value={10}>10s</option>
                            <option value={30}>30s</option>
                            <option value={60}>60s</option>
                            <option value={120}>2m</option>
                        </select>
                    </label>
                    <button
                        className="simulation-viewer__btn"
                        onClick={runSimulation}
                        disabled={running || !projectId}
                    >
                        {running ? '⏳ Running...' : '▶ Simulate'}
                    </button>
                </div>
            </div>

            {result && (
                <div className="simulation-viewer__results">
                    {/* Statistics cards */}
                    <div className="simulation-viewer__stats">
                        {Object.entries(result.statistics || {}).map(([name, stat]) => (
                            <div key={name} className="sim-stat-card">
                                <div className="sim-stat-card__name">{name}</div>
                                <div className="sim-stat-card__values">
                                    <span className="sim-stat-card__min">↓ {stat.min.toFixed(1)}</span>
                                    <span className="sim-stat-card__avg">μ {stat.avg.toFixed(1)}</span>
                                    <span className="sim-stat-card__max">↑ {stat.max.toFixed(1)}</span>
                                </div>
                            </div>
                        ))}
                    </div>

                    {/* Timeline visualization (simple bar chart) */}
                    <div className="simulation-viewer__timeline">
                        <div className="simulation-viewer__timeline-label">
                            Timeline ({result.timeline?.length || 0} points, {result.duration_seconds}s)
                        </div>
                        <div className="simulation-viewer__bars">
                            {(result.timeline || []).slice(-60).map((point, i) => {
                                const maxVal = Math.max(...(result.timeline || []).map(p => Math.abs(p.value)), 1);
                                const height = Math.min(Math.abs(point.value) / maxVal * 100, 100);
                                return (
                                    <div
                                        key={i}
                                        className="sim-bar"
                                        style={{ height: `${height}%` }}
                                        title={`${point.node_name}: ${point.value.toFixed(2)} @ ${point.time_ms}ms`}
                                    />
                                );
                            })}
                        </div>
                    </div>
                </div>
            )}

            {!result && !running && (
                <div className="simulation-viewer__empty">
                    Run simulation to preview block behavior with mock sensor data
                </div>
            )}
        </div>
    );
}

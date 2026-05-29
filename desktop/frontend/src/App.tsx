/**
 * App — Main application layout.
 * Three-panel layout: BlockLibrary | Canvas | ConfigPanel + AI Suggestions
 * Bottom panel: Templates | Simulation | Serial Monitor
 */

import { useState, useCallback } from 'react';
import type { Node } from '@xyflow/react';
import Canvas from './canvas/Canvas';
import BlockLibrary from './blocks/BlockLibrary';
import BlockConfigPanel from './blocks/BlockConfigPanel';
import TemplatePicker from './blocks/TemplatePicker';
import SimulationViewer from './blocks/SimulationViewer';
import SerialMonitor from './blocks/SerialMonitor';
import { pipelineApi, suggestionsApi } from './api/apiClient';
import './index.css';

// Pipeline stages
const PIPELINE_STAGES = [
  { key: 'plan', label: 'Plan', icon: '🧠' },
  { key: 'synthesize', label: 'Synthesize', icon: '⚡' },
  { key: 'signals', label: 'Signals', icon: '📡' },
  { key: 'allocate', label: 'Allocate', icon: '📋' },
  { key: 'generate', label: 'Generate', icon: '⚙️' },
  { key: 'assemble', label: 'Assemble', icon: '🔧' },
  { key: 'compile', label: 'Compile', icon: '🔨' },
];

interface Suggestion {
  id: string;
  severity: string;
  title: string;
  message: string;
  suggested_block?: string;
  source?: string;
}

export default function App() {
  const [selectedNode, setSelectedNode] = useState<Node | null>(null);
  const [showBuildBar, setShowBuildBar] = useState(false);
  const [buildStatus, setBuildStatus] = useState('Ready');
  const [activeStage, setActiveStage] = useState(-1);
  const [suggestions, setSuggestions] = useState<Suggestion[]>([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [pipelineResult, setPipelineResult] = useState<unknown>(null);
  const [bottomTab, setBottomTab] = useState<'templates' | 'simulation' | 'serial' | null>(null);

  const projectId = 'example_project';

  const handleTemplateLoad = useCallback((templateData: unknown) => {
    console.log('Template loaded:', templateData);
    // TODO: Apply template nodes/edges to canvas
    setBottomTab(null);
  }, []);

  const runPipeline = useCallback(async () => {
    setShowBuildBar(true);
    setPipelineResult(null);
    try {
      for (let i = 0; i < PIPELINE_STAGES.length; i++) {
        setActiveStage(i);
        setBuildStatus(`${PIPELINE_STAGES[i].icon} ${PIPELINE_STAGES[i].label}...`);
        await new Promise((r) => setTimeout(r, 300)); // brief visual delay
      }
      const result = await pipelineApi.run(projectId);
      setPipelineResult(result);
      setActiveStage(PIPELINE_STAGES.length);
      setBuildStatus('✅ Pipeline complete');
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Unknown error';
      setBuildStatus(`❌ ${msg}`);
      setActiveStage(-1);
    }
  }, [projectId]);

  const fetchSuggestions = useCallback(async () => {
    try {
      const result = await suggestionsApi.suggest(projectId) as {
        rule_suggestions: Suggestion[];
        ai_suggestions: Suggestion[];
      };
      setSuggestions([...result.rule_suggestions, ...result.ai_suggestions]);
      setShowSuggestions(true);
    } catch {
      setSuggestions([]);
    }
  }, [projectId]);

  const severityIcon = (s: string) =>
    ({ warning: '⚠️', info: 'ℹ️', tip: '💡', error: '🔴' })[s] || '📝';

  return (
    <div className="app">
      {/* Top toolbar */}
      <header className="toolbar">
        <div className="toolbar__left">
          <span className="toolbar__logo">🔱</span>
          <h1 className="toolbar__title">Parakram AI</h1>
          <span className="toolbar__version">v0.2.0</span>
        </div>
        <div className="toolbar__center">
          <span className="toolbar__project-name">Example Project</span>
          <span className="toolbar__target">ESP32 • FreeRTOS</span>
        </div>
        <div className="toolbar__right">
          <button
            className="toolbar__btn toolbar__btn--generate"
            onClick={runPipeline}
          >
            🚀 Build Pipeline
          </button>
          <button
            className="toolbar__btn toolbar__btn--compile"
            onClick={fetchSuggestions}
          >
            🤖 AI Suggest
          </button>
          <button className="toolbar__btn toolbar__btn--flash">
            📡 Flash
          </button>
          <button className="toolbar__btn toolbar__btn--save">
            💾 Save
          </button>
        </div>
      </header>

      {/* Pipeline progress bar */}
      {showBuildBar && (
        <div className="build-bar">
          <div className="build-bar__stages">
            {PIPELINE_STAGES.map((stage, i) => (
              <span
                key={stage.key}
                className={`build-bar__stage ${i < activeStage ? 'build-bar__stage--done' :
                  i === activeStage ? 'build-bar__stage--active' : ''
                  }`}
              >
                {stage.icon} {stage.label}
              </span>
            ))}
          </div>
          <span className="build-bar__status">{buildStatus}</span>
          <button className="build-bar__close" onClick={() => setShowBuildBar(false)}>×</button>
        </div>
      )}

      {/* Main content */}
      <main className="main-content">
        {/* Left sidebar — Block Library */}
        <aside className="sidebar sidebar--left">
          <BlockLibrary />
        </aside>

        {/* Center — Canvas + Bottom Panel */}
        <section className="canvas-wrapper" style={{ display: 'flex', flexDirection: 'column' }}>
          <div style={{ flex: 1, position: 'relative' }}>
            <Canvas onNodeSelect={setSelectedNode} />
          </div>

          {/* Bottom panel tabs */}
          <div className="bottom-tabs">
            <button
              className={`bottom-tabs__btn ${bottomTab === 'templates' ? 'bottom-tabs__btn--active' : ''}`}
              onClick={() => setBottomTab(bottomTab === 'templates' ? null : 'templates')}
            >
              🚀 Templates
            </button>
            <button
              className={`bottom-tabs__btn ${bottomTab === 'simulation' ? 'bottom-tabs__btn--active' : ''}`}
              onClick={() => setBottomTab(bottomTab === 'simulation' ? null : 'simulation')}
            >
              📊 Simulate
            </button>
            <button
              className={`bottom-tabs__btn ${bottomTab === 'serial' ? 'bottom-tabs__btn--active' : ''}`}
              onClick={() => setBottomTab(bottomTab === 'serial' ? null : 'serial')}
            >
              📟 Serial
            </button>
          </div>

          {/* Bottom panel content */}
          {bottomTab && (
            <div className="bottom-panel">
              {bottomTab === 'templates' && (
                <TemplatePicker onLoad={handleTemplateLoad} />
              )}
              {bottomTab === 'simulation' && (
                <SimulationViewer projectId={projectId} />
              )}
              {bottomTab === 'serial' && (
                <SerialMonitor />
              )}
            </div>
          )}
        </section>

        {/* Right sidebar — Config Panel + Suggestions */}
        <aside className="sidebar sidebar--right">
          <BlockConfigPanel selectedNode={selectedNode} />

          {/* AI Suggestions Panel */}
          {showSuggestions && suggestions.length > 0 && (
            <div className="suggestions-panel">
              <div className="suggestions-panel__header">
                <h3>🤖 AI Suggestions</h3>
                <button onClick={() => setShowSuggestions(false)}>×</button>
              </div>
              <div className="suggestions-panel__list">
                {suggestions.map((s) => (
                  <div
                    key={s.id}
                    className={`suggestion suggestion--${s.severity}`}
                  >
                    <span className="suggestion__icon">
                      {severityIcon(s.severity)}
                    </span>
                    <div className="suggestion__content">
                      <strong>{s.title}</strong>
                      <p>{s.message}</p>
                      {s.suggested_block && (
                        <span className="suggestion__action">
                          + Add {s.suggested_block}
                        </span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </aside>
      </main>
    </div>
  );
}

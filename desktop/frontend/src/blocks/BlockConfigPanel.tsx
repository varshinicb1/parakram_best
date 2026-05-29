/**
 * BlockConfigPanel — Right panel for editing selected block properties.
 */

import type { Node } from '@xyflow/react';
import type { BlockNodeData } from '../canvas/BlockNode';
import { BLOCK_CATEGORIES } from '../types/Block';

interface BlockConfigPanelProps {
    selectedNode: Node | null;
}

export default function BlockConfigPanel({ selectedNode }: BlockConfigPanelProps) {
    if (!selectedNode) {
        return (
            <div className="config-panel config-panel--empty">
                <div className="config-panel__placeholder">
                    <span className="config-panel__placeholder-icon">👆</span>
                    <p>Select a block on the canvas to configure it</p>
                </div>
            </div>
        );
    }

    const data = selectedNode.data as unknown as BlockNodeData;
    const categoryMeta = BLOCK_CATEGORIES[data.category] || BLOCK_CATEGORIES.logic;

    return (
        <div className="config-panel">
            <div className="config-panel__header">
                <h2 className="config-panel__title">
                    {categoryMeta.icon} {data.name}
                </h2>
                <span
                    className="config-panel__badge"
                    style={{ background: data.color || categoryMeta.color }}
                >
                    {categoryMeta.label}
                </span>
            </div>

            {data.description && (
                <p className="config-panel__description">{data.description}</p>
            )}

            {/* Node ID */}
            <div className="config-panel__section">
                <h3 className="config-panel__section-title">Identity</h3>
                <div className="config-panel__field">
                    <label>Node ID</label>
                    <input type="text" value={selectedNode.id} readOnly className="config-panel__input config-panel__input--readonly" />
                </div>
            </div>

            {/* Position */}
            <div className="config-panel__section">
                <h3 className="config-panel__section-title">Position</h3>
                <div className="config-panel__field-row">
                    <div className="config-panel__field">
                        <label>X</label>
                        <input type="number" value={Math.round(selectedNode.position.x)} readOnly className="config-panel__input config-panel__input--small" />
                    </div>
                    <div className="config-panel__field">
                        <label>Y</label>
                        <input type="number" value={Math.round(selectedNode.position.y)} readOnly className="config-panel__input config-panel__input--small" />
                    </div>
                </div>
            </div>

            {/* Configuration */}
            <div className="config-panel__section">
                <h3 className="config-panel__section-title">⚙️ Configuration</h3>
                {data.configuration && Object.keys(data.configuration).length > 0 ? (
                    Object.entries(data.configuration).map(([key, value]) => (
                        <div key={key} className="config-panel__field">
                            <label>{key}</label>
                            <input
                                type="text"
                                defaultValue={String(value)}
                                className="config-panel__input"
                                placeholder={`Enter ${key}...`}
                            />
                        </div>
                    ))
                ) : (
                    <p className="config-panel__empty-text">No configuration parameters</p>
                )}
            </div>

            {/* Inputs */}
            {data.inputs && data.inputs.length > 0 && (
                <div className="config-panel__section">
                    <h3 className="config-panel__section-title">📥 Inputs</h3>
                    {data.inputs.map((input) => (
                        <div key={input.name} className="config-panel__port">
                            <span className="config-panel__port-name">{input.name}</span>
                            <span className="config-panel__port-type">{input.data_type}</span>
                        </div>
                    ))}
                </div>
            )}

            {/* Outputs */}
            {data.outputs && data.outputs.length > 0 && (
                <div className="config-panel__section">
                    <h3 className="config-panel__section-title">📤 Outputs</h3>
                    {data.outputs.map((output) => (
                        <div key={output.name} className="config-panel__port">
                            <span className="config-panel__port-name">{output.name}</span>
                            <span className="config-panel__port-type">{output.data_type}</span>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}

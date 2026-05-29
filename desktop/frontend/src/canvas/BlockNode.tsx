/**
 * BlockNode — Custom React Flow node for hardware/software blocks.
 * Shows block name, category icon, and input/output handles.
 */

import { memo } from 'react';
import { Handle, Position, type NodeProps } from '@xyflow/react';
import type { BlockPort } from '../types/Block';
import { BLOCK_CATEGORIES } from '../types/Block';

export interface BlockNodeData {
    name: string;
    category: keyof typeof BLOCK_CATEGORIES;
    description: string;
    inputs: BlockPort[];
    outputs: BlockPort[];
    configuration: Record<string, unknown>;
    icon?: string;
    color?: string;
    [key: string]: unknown;
}

function BlockNode({ data, selected }: NodeProps) {
    const nodeData = data as unknown as BlockNodeData;
    const categoryMeta = BLOCK_CATEGORIES[nodeData.category] || BLOCK_CATEGORIES.logic;
    const nodeColor = nodeData.color || categoryMeta.color;

    return (
        <div
            className={`block-node ${selected ? 'block-node--selected' : ''}`}
            style={{ '--node-color': nodeColor } as React.CSSProperties}
        >
            {/* Header */}
            <div className="block-node__header">
                <span className="block-node__icon">{categoryMeta.icon}</span>
                <span className="block-node__name">{nodeData.name}</span>
                <span className="block-node__badge">{categoryMeta.label}</span>
            </div>

            {/* Description */}
            {nodeData.description && (
                <div className="block-node__description">{nodeData.description}</div>
            )}

            {/* Ports */}
            <div className="block-node__ports">
                {/* Input ports */}
                <div className="block-node__inputs">
                    {(nodeData.inputs || []).map((input: BlockPort, i: number) => (
                        <div key={input.name} className="block-node__port block-node__port--input">
                            <Handle
                                type="target"
                                position={Position.Left}
                                id={input.name}
                                className="block-node__handle block-node__handle--input"
                                style={{ top: `${30 + i * 24}px` }}
                            />
                            <span className="block-node__port-name">{input.name}</span>
                            <span className="block-node__port-type">{input.data_type}</span>
                        </div>
                    ))}
                </div>

                {/* Output ports */}
                <div className="block-node__outputs">
                    {(nodeData.outputs || []).map((output: BlockPort, i: number) => (
                        <div key={output.name} className="block-node__port block-node__port--output">
                            <span className="block-node__port-type">{output.data_type}</span>
                            <span className="block-node__port-name">{output.name}</span>
                            <Handle
                                type="source"
                                position={Position.Right}
                                id={output.name}
                                className="block-node__handle block-node__handle--output"
                                style={{ top: `${30 + i * 24}px` }}
                            />
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
}

export default memo(BlockNode);

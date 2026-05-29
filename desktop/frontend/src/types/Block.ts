/**
 * Block type definitions -- mirrors backend Pydantic models.
 */

export interface BlockPort {
    name: string;
    data_type: string;
    description?: string;
}

export interface BlockConfig {
    key: string;
    label: string;
    value_type: 'string' | 'int' | 'float' | 'bool' | 'select';
    default?: string;
    options?: string[];
    description?: string;
}

export interface Block {
    id: string;
    name: string;
    category: 'sensor' | 'communication' | 'actuator' | 'logic' | 'output' | 'control' | 'security' | 'audio' | 'display' | 'freertos';
    description: string;
    inputs: BlockPort[];
    outputs: BlockPort[];
    configuration: BlockConfig[];
    code_template: string;
    icon: string;
    color: string;
    libraries?: string[];
    memory_estimate?: { flash: number; sram: number };
}

export interface BlockInstance {
    id: string;
    block_id: string;
    name: string;
    category: string;
    description: string;
    inputs: BlockPort[];
    outputs: BlockPort[];
    configuration: Record<string, unknown>;
    position: { x: number; y: number };
}

// Category metadata for the block library UI
export const BLOCK_CATEGORIES = {
    sensor: { label: 'Sensors', icon: '📡', color: '#ef4444' },
    communication: { label: 'Communication', icon: '📶', color: '#8b5cf6' },
    actuator: { label: 'Actuators', icon: '⚡', color: '#10b981' },
    logic: { label: 'Logic', icon: '🧠', color: '#f59e0b' },
    output: { label: 'Output', icon: '📤', color: '#06b6d4' },
    control: { label: 'Control', icon: '🎛️', color: '#ec4899' },
    security: { label: 'Security', icon: '🔒', color: '#dc2626' },
    audio: { label: 'Audio', icon: '🎵', color: '#a855f7' },
    display: { label: 'Display', icon: '🖥️', color: '#0ea5e9' },
    freertos: { label: 'FreeRTOS', icon: '🧵', color: '#059669' },
} as const;

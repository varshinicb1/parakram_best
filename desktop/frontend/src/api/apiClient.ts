/**
 * API Client -- communicates with the FastAPI backend.
 */

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

async function request<T>(
    endpoint: string,
    options: RequestInit = {}
): Promise<T> {
    const url = `${API_BASE}${endpoint}`;
    const response = await fetch(url, {
        headers: {
            'Content-Type': 'application/json',
            ...options.headers,
        },
        ...options,
    });

    if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'Request failed' }));
        throw new Error(error.detail || `HTTP ${response.status}`);
    }

    return response.json();
}

// ─── Project APIs ────────────────────────────────────────
export const projectApi = {
    list: () => request<{ projects: unknown[] }>('/api/projects'),
    create: (project: unknown) =>
        request('/api/projects', { method: 'POST', body: JSON.stringify(project) }),
    get: (id: string) => request(`/api/projects/${id}`),
    delete: (id: string) =>
        request(`/api/projects/${id}`, { method: 'DELETE' }),
};

// ─── Canvas APIs ─────────────────────────────────────────
export const canvasApi = {
    load: (projectId: string) => request(`/api/canvas/${projectId}`),
    save: (projectId: string, graph: unknown) =>
        request(`/api/canvas/${projectId}`, {
            method: 'PUT',
            body: JSON.stringify(graph),
        }),
    export: (projectId: string) =>
        request(`/api/canvas/${projectId}/export`, { method: 'POST' }),
};

// ─── Build APIs ──────────────────────────────────────────
export const buildApi = {
    generate: (projectId: string) =>
        request('/api/build/generate', {
            method: 'POST',
            body: JSON.stringify({ project_id: projectId }),
        }),
    compile: (projectId: string, maxRetries = 3) =>
        request('/api/build/compile', {
            method: 'POST',
            body: JSON.stringify({ project_id: projectId, max_retries: maxRetries }),
        }),
    generateAndCompile: (projectId: string, maxRetries = 3) =>
        request('/api/build/generate-and-compile', {
            method: 'POST',
            body: JSON.stringify({ project_id: projectId, max_retries: maxRetries }),
        }),
    status: (projectId: string) => request(`/api/build/status/${projectId}`),
};

// ─── Flash APIs ──────────────────────────────────────────
export const flashApi = {
    listDevices: () => request<{ devices: unknown[] }>('/api/flash/devices'),
    upload: (projectId: string, port?: string) =>
        request('/api/flash/upload', {
            method: 'POST',
            body: JSON.stringify({ project_id: projectId, port }),
        }),
    startMonitor: (port?: string) =>
        request('/api/flash/monitor', {
            method: 'POST',
            body: JSON.stringify({ port }),
        }),
    stopMonitor: () =>
        request('/api/flash/monitor', { method: 'DELETE' }),
};

// ─── Pipeline APIs ───────────────────────────────────────
export const pipelineApi = {
    plan: (projectId: string) =>
        request('/api/pipeline/plan', {
            method: 'POST',
            body: JSON.stringify({ project_id: projectId }),
        }),
    synthesize: (projectId: string) =>
        request('/api/pipeline/synthesize', {
            method: 'POST',
            body: JSON.stringify({ project_id: projectId }),
        }),
    signals: (projectId: string) =>
        request('/api/pipeline/signals', {
            method: 'POST',
            body: JSON.stringify({ project_id: projectId }),
        }),
    allocate: (projectId: string, board = 'esp32dev') =>
        request('/api/pipeline/allocate', {
            method: 'POST',
            body: JSON.stringify({ project_id: projectId, board }),
        }),
    run: (projectId: string, board = 'esp32dev', skipCompile = false) =>
        request('/api/pipeline/run', {
            method: 'POST',
            body: JSON.stringify({
                project_id: projectId,
                board,
                skip_compile: skipCompile,
            }),
        }),
    status: (projectId: string) => request(`/api/pipeline/status/${projectId}`),
};

// ─── Suggestions APIs ────────────────────────────────────
export const suggestionsApi = {
    suggest: (projectId: string) =>
        request('/api/suggestions/suggest', {
            method: 'POST',
            body: JSON.stringify({ project_id: projectId }),
        }),
};

// ─── Template APIs ───────────────────────────────────────
export const templateApi = {
    list: () => request<{ templates: unknown[] }>('/api/templates/list'),
    get: (templateId: string) => request(`/api/templates/${templateId}`),
};

// ─── Simulation APIs ─────────────────────────────────────
export const simulationApi = {
    run: (projectId: string, durationSec = 60, stepMs = 1000) =>
        request('/api/simulation/run', {
            method: 'POST',
            body: JSON.stringify({
                project_id: projectId,
                duration_seconds: durationSec,
                time_step_ms: stepMs,
            }),
        }),
};

// ─── Serial Monitor APIs ─────────────────────────────────
export const serialApi = {
    start: (port = 'mock', mock = true) =>
        request('/api/serial/start', {
            method: 'POST',
            body: JSON.stringify({ port, mock }),
        }),
    stop: () => request('/api/serial/stop', { method: 'POST' }),
    status: () => request('/api/serial/status'),
};

// WebSocket helper for serial monitor
export function createSerialWebSocket(): WebSocket {
    const wsUrl = `ws://${window.location.hostname}:8000/api/serial/ws`;
    return new WebSocket(wsUrl);
}

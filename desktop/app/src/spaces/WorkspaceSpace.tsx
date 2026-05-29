/**
 * WorkspaceSpace — VS Code-style code editor with file tree, project creation,
 * MISRA compliance analysis, and intelligent code editing.
 */
import { useState } from 'react';
import {
  Folder, ChevronRight, ChevronDown, Save,
  AlertTriangle, CheckCircle, FileCode, FolderPlus, Shield
} from 'lucide-react';
import { useLiveQuery } from 'dexie-react-hooks';
import { db } from '../lib/db';

interface FileNode {
  name: string;
  path: string;
  type: 'file' | 'directory';
  extension?: string;
  size?: number;
  children?: FileNode[];
}


interface MISRAViolation {
  rule: string;
  severity: string;
  line: number;
  message: string;
  suggestion: string;
}

const API = 'http://localhost:8000/api/workspace';
const ANALYSIS_API = 'http://localhost:8000/api/analysis';

export default function WorkspaceSpace() {
  const dbProjects = useLiveQuery(() => db.projects.orderBy('createdAt').reverse().toArray(), []);
  
  const [activeProject, setActiveProject] = useState<string | null>(null);
  const [fileTree, setFileTree] = useState<FileNode[]>([]);
  const [activeFile, setActiveFile] = useState<string | null>(null);
  const [fileContent, setFileContent] = useState('');
  const [modified, setModified] = useState(false);
  const [violations, setViolations] = useState<MISRAViolation[]>([]);
  const [compliance, setCompliance] = useState<{ score: number; grade: string } | null>(null);
  const [newProjectName, setNewProjectName] = useState('');
  const [showNewProject, setShowNewProject] = useState(false);
  const [saving, setSaving] = useState(false);

  const loadProject = async (name: string) => {
    setActiveProject(name);
    try {
      const res = await fetch(`${API}/files/${name}`);
      const data = await res.json();
      setFileTree(data.tree || []);
    } catch { /* ignore */ }
  };

  const openFile = async (path: string) => {
    if (!activeProject) return;
    try {
      const res = await fetch(`${API}/files/${activeProject}/read?path=${encodeURIComponent(path)}`);
      const data = await res.json();
      setActiveFile(path);
      setFileContent(data.content || '');
      setModified(false);
      setViolations([]);
      setCompliance(null);
    } catch { /* ignore */ }
  };

  const saveFile = async () => {
    if (!activeProject || !activeFile) return;
    setSaving(true);
    try {
      await fetch(`${API}/files/${activeProject}/write`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path: activeFile, content: fileContent }),
      });
      setModified(false);
    } catch { /* ignore */ }
    setSaving(false);
  };

  const runMISRA = async () => {
    if (!fileContent) return;
    try {
      const res = await fetch(`${ANALYSIS_API}/misra/check`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ code: fileContent, filename: activeFile || 'main.cpp' }),
      });
      const data = await res.json();
      setViolations(data.violations || []);
      setCompliance(data.compliance || null);
    } catch { /* ignore */ }
  };

  const createProject = async (template: string) => {
    if (!newProjectName.trim()) return;
    try {
      // 1. Tell backend to create physical files
      await fetch(`${API}/projects/create`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: newProjectName.trim(), template }),
      });
      
      // 2. Save metadata to local Dexie DB
      await db.projects.add({
        id: crypto.randomUUID(),
        name: newProjectName.trim(),
        description: `Created from ${template} template`,
        board: 'Generic ESP32',
        createdAt: new Date().toISOString(),
        blocks: [],
      });

      setShowNewProject(false);
      setNewProjectName('');
    } catch (e) { console.error("Failed to create project", e); }
  };

  const FileTreeNode = ({ node, depth = 0 }: { node: FileNode; depth?: number }) => {
    const [expanded, setExpanded] = useState(depth < 2);
    const isActive = activeFile === node.path;
    const Icon = node.type === 'directory' ? (expanded ? ChevronDown : ChevronRight) : FileCode;

    return (
      <div>
        <button
          onClick={() => node.type === 'directory' ? setExpanded(!expanded) : openFile(node.path)}
          className="w-full flex items-center gap-2 px-3 py-1.5 text-left text-xs font-medium transition-colors hover:bg-[var(--bg-tertiary)]"
          style={{
            paddingLeft: `${12 + depth * 16}px`,
            background: isActive ? 'var(--bg-tertiary)' : 'transparent',
            color: isActive ? 'var(--text-primary)' : 'var(--text-secondary)',
            borderLeft: isActive ? '2px solid var(--accent)' : '2px solid transparent'
          }}>
          <Icon size={14} style={{ color: node.type === 'directory' ? 'var(--text-muted)' : 'var(--text-secondary)' }} />
          <span className="truncate">{node.name}</span>
        </button>
        {expanded && node.children?.map(child => (
          <FileTreeNode key={child.path} node={child} depth={depth + 1} />
        ))}
      </div>
    );
  };

  return (
    <div className="flex-1 flex overflow-hidden">
      {/* Left: Project Explorer */}
      <div className="w-64 border-r flex flex-col shrink-0" style={{ borderColor: 'var(--border)', background: 'var(--bg-secondary)' }}>
        <div className="flex items-center justify-between px-4 py-3 border-b" style={{ borderColor: 'var(--border)' }}>
          <span className="text-xs font-semibold" style={{ color: 'var(--text-muted)' }}>Explorer</span>
          <button onClick={() => setShowNewProject(!showNewProject)} className="p-1 rounded-md transition-colors hover:bg-[var(--bg-tertiary)]" style={{ color: 'var(--text-secondary)' }}>
            <FolderPlus size={16} />
          </button>
        </div>

        {showNewProject && (
          <div className="p-3 border-b space-y-3 bg-[var(--bg-tertiary)]" style={{ borderColor: 'var(--border)' }}>
            <input value={newProjectName} onChange={e => setNewProjectName(e.target.value)}
              placeholder="Project name..." className="w-full bg-[var(--bg-primary)] border rounded-md px-3 py-1.5 text-sm outline-none placeholder:text-[var(--text-muted)]"
              style={{ borderColor: 'var(--border)', color: 'var(--text-primary)' }} />
            <div className="grid grid-cols-2 gap-2">
              {['blank', 'blink', 'sensor', 'iot'].map(t => (
                <button key={t} onClick={() => createProject(t)}
                  className="text-xs font-medium px-2 py-1.5 border rounded-lg transition-colors hover:bg-[var(--bg-secondary)]"
                  style={{ borderColor: 'var(--border)', color: 'var(--text-secondary)' }}>
                  <span className="capitalize">{t}</span>
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Projects list */}
        <div className="flex-1 overflow-y-auto py-2">
          {!dbProjects || dbProjects.length === 0 ? (
            <div className="text-center py-10 px-4 text-sm" style={{ color: 'var(--text-muted)' }}>
               No local projects found.<br /><span className="text-xs mt-2 inline-block">Click the + icon to create one.</span>
            </div>
          ) : (
            dbProjects.map(p => (
              <div key={p.id}>
                <button onClick={() => loadProject(p.name)}
                  className="w-full flex items-center gap-2 px-3 py-2 text-sm font-semibold transition-colors hover:bg-[var(--bg-tertiary)]"
                  style={{
                    background: activeProject === p.name ? 'var(--bg-tertiary)' : 'transparent',
                    color: activeProject === p.name ? 'var(--text-primary)' : 'var(--text-secondary)',
                  }}>
                  <Folder size={14} style={{ color: 'var(--text-muted)' }} /> {p.name}
                </button>
                {activeProject === p.name && (
                  <div className="py-1">
                    {fileTree.map(node => (
                      <FileTreeNode key={node.path} node={node} />
                    ))}
                  </div>
                )}
              </div>
            ))
          )}
        </div>
      </div>

      {/* Center: Code Editor */}
      <div className="flex-1 flex flex-col min-w-0">
        {activeFile && (
          <div className="flex items-center justify-between px-4 py-2 border-b bg-[var(--bg-secondary)]" style={{ borderColor: 'var(--border)' }}>
            <div className="flex items-center gap-2">
              <FileCode size={14} style={{ color: 'var(--text-secondary)' }} />
              <span className="text-sm font-mono font-medium" style={{ color: 'var(--text-primary)' }}>
                {activeFile} {modified && <span style={{ color: 'var(--warning)' }}>●</span>}
              </span>
            </div>
            <div className="flex items-center gap-3">
              <button onClick={saveFile} disabled={saving || !modified}
                className="flex items-center gap-2 px-4 py-1.5 text-xs font-semibold rounded-lg transition-colors disabled:opacity-50 shadow-sm"
                style={{ background: modified ? 'var(--text-primary)' : 'var(--bg-tertiary)', color: modified ? 'var(--bg-primary)' : 'var(--text-muted)' }}>
                <Save size={14} /> {saving ? 'Saving...' : 'Save File'}
              </button>
              <button onClick={runMISRA}
                className="flex items-center gap-2 px-3 py-1.5 text-xs font-semibold border rounded-lg transition-colors hover:bg-[var(--bg-tertiary)] shadow-sm"
                style={{ borderColor: 'var(--border)', color: 'var(--text-secondary)' }}>
                <Shield size={14} /> MISRA Analysis
              </button>
            </div>
          </div>
        )}

        {activeFile ? (
          <textarea value={fileContent}
            onChange={e => { setFileContent(e.target.value); setModified(true); }}
            className="flex-1 resize-none p-6 font-mono text-sm leading-relaxed outline-none"
            style={{ background: 'var(--bg-primary)', color: 'var(--text-secondary)' }}
            spellCheck={false}
          />
        ) : (
          <div className="flex-1 flex items-center justify-center flex-col gap-4">
            <FileCode size={48} style={{ color: 'var(--text-muted)', opacity: 0.3 }} />
            <p className="text-sm font-semibold" style={{ color: 'var(--text-muted)' }}>Select a file to edit</p>
          </div>
        )}
      </div>

      {/* Right: MISRA Compliance Panel */}
      {violations.length > 0 && (
        <div className="w-80 border-l overflow-y-auto shrink-0" style={{ borderColor: 'var(--border)', background: 'var(--bg-secondary)' }}>
          <div className="p-4 border-b space-y-3 bg-[var(--bg-tertiary)]" style={{ borderColor: 'var(--border)' }}>
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold" style={{ color: 'var(--text-muted)' }}>MISRA Compliance</span>
              {compliance && (
                <span className="text-xl font-bold"
                  style={{ color: compliance.score >= 75 ? 'var(--success)' : compliance.score >= 50 ? 'var(--warning)' : 'var(--error)' }}>
                  {compliance.grade}
                </span>
              )}
            </div>
            {compliance && (
              <div className="w-full h-2 rounded-full overflow-hidden" style={{ background: 'var(--bg-primary)' }}>
                <div className="h-full rounded-full transition-all" style={{
                  width: `${compliance.score}%`,
                  background: compliance.score >= 75 ? 'var(--success)' : compliance.score >= 50 ? 'var(--warning)' : 'var(--error)',
                }} />
              </div>
            )}
          </div>
          <div className="p-2">
            {violations.map((v, i) => (
              <div key={i} className="px-3 py-3 border-b border-transparent hover:bg-[var(--bg-tertiary)] hover:border-[var(--border)] rounded-md transition-colors">
                <div className="flex items-center gap-2 mb-1.5">
                  {v.severity === 'error' ? <AlertTriangle size={14} style={{ color: 'var(--error)' }} /> :
                   v.severity === 'warning' ? <AlertTriangle size={14} style={{ color: 'var(--warning)' }} /> :
                   <CheckCircle size={14} style={{ color: 'var(--accent)' }} />}
                  <span className="text-xs font-bold"
                    style={{ color: v.severity === 'error' ? 'var(--error)' : v.severity === 'warning' ? 'var(--warning)' : 'var(--accent)' }}>
                    Rule {v.rule} · Line {v.line}
                  </span>
                </div>
                <p className="text-xs leading-relaxed" style={{ color: 'var(--text-primary)' }}>{v.message}</p>
                <div className="mt-2 text-xs p-2 rounded-lg bg-[var(--bg-primary)] border" style={{ color: 'var(--text-secondary)', borderColor: 'var(--border)' }}>
                  <span className="font-semibold text-xs mb-1 block" style={{ color: 'var(--text-muted)' }}>Suggestion</span>
                  {v.suggestion}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

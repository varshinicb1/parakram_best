/**
 * CommandPalette — kbar-powered Ctrl+K command launcher.
 * Inspired by Raycast/VSCode command palette.
 */
import {
  KBarPortal,
  KBarPositioner,
  KBarAnimator,
  KBarSearch,
  KBarResults,
  useMatches,
  useRegisterActions,
} from 'kbar';
import { useAppStore } from '../stores/appStore';
import type { Theme, Space } from '../stores/appStore';

export default function CommandPalette() {
  const setActiveSpace = useAppStore((s) => s.setActiveSpace);
  const setTheme = useAppStore((s) => s.setTheme);

  useRegisterActions([
    {
      id: 'home', name: 'Go Home', shortcut: ['g', 'h'], section: 'Navigation',
      perform: () => setActiveSpace('home'),
    },
    {
      id: 'workspace', name: 'Open Workspace', shortcut: ['g', 'w'], section: 'Navigation',
      perform: () => setActiveSpace('workspace'),
    },
    {
      id: 'devices', name: 'Open Devices', shortcut: ['g', 'd'], section: 'Navigation',
      perform: () => setActiveSpace('devices' as Space),
    },
    {
      id: 'telemetry', name: 'Open Telemetry', shortcut: ['g', 't'], section: 'Navigation',
      perform: () => setActiveSpace('telemetry' as Space),
    },
    {
      id: 'theme-dark', name: 'Theme: Dark Lab', section: 'Settings',
      perform: () => setTheme('dark-lab' as Theme),
    },
    {
      id: 'theme-cyber', name: 'Theme: Cyberpunk', section: 'Settings',
      perform: () => setTheme('cyberpunk' as Theme),
    },
    {
      id: 'theme-midnight', name: 'Theme: Midnight', section: 'Settings',
      perform: () => setTheme('midnight' as Theme),
    },
    {
      id: 'theme-solarized', name: 'Theme: Solarized', section: 'Settings',
      perform: () => setTheme('solarized' as Theme),
    },
    {
      id: 'theme-retro', name: 'Theme: Retro Terminal', section: 'Settings',
      perform: () => setTheme('retro' as Theme),
    },
    {
      id: 'theme-glass', name: 'Theme: Glass UI', section: 'Settings',
      perform: () => setTheme('glass' as Theme),
    },
  ], [setActiveSpace, setTheme]);

  return (
    <KBarPortal>
      <KBarPositioner className="fixed inset-0 z-[9999]"
        style={{ background: 'rgba(0, 0, 0, 0.6)', backdropFilter: 'blur(8px)' }}>
        <KBarAnimator className="w-full max-w-[600px] overflow-hidden rounded-2xl"
          style={{
            background: 'var(--bg-secondary)',
            border: '1px solid var(--border)',
            boxShadow: '0 24px 80px rgba(0,0,0,0.5)',
          }}>
          <KBarSearch
            className="w-full px-5 py-4 text-base outline-none border-b"
            style={{
              background: 'transparent',
              color: 'var(--text-primary)',
              borderColor: 'var(--border)',
              fontFamily: 'var(--font-sans)',
            }}
            defaultPlaceholder="Type a command..."
          />
          <div className="max-h-[400px] overflow-auto py-2">
            <RenderResults />
          </div>
          <div className="flex items-center justify-between px-4 py-2 border-t text-xs"
            style={{ borderColor: 'var(--border)', color: 'var(--text-muted)' }}>
            <span>↑↓ to navigate</span>
            <span>↵ to select</span>
            <span>esc to close</span>
          </div>
        </KBarAnimator>
      </KBarPositioner>
    </KBarPortal>
  );
}

function RenderResults() {
  const { results } = useMatches();
  return (
    <KBarResults
      items={results}
      onRender={({ item, active }) =>
        typeof item === 'string' ? (
          <div className="px-4 py-2 text-xs font-semibold"
            style={{ color: 'var(--text-muted)' }}>
            {item}
          </div>
        ) : (
          <div
            className="flex items-center gap-3 px-4 py-2.5 mx-2 rounded-lg cursor-pointer transition-colors"
            style={{
              background: active ? 'var(--accent-subtle)' : 'transparent',
              color: active ? 'var(--accent)' : 'var(--text-primary)',
            }}
          >
            <span className="flex-1 text-sm">{item.name}</span>
            {item.shortcut?.length && (
              <span className="flex gap-1">
                {item.shortcut.map((s: string) => (
                  <kbd key={s} className="px-1.5 py-0.5 rounded text-xs font-mono"
                    style={{ background: 'var(--bg-elevated)', color: 'var(--text-secondary)' }}>
                    {s}
                  </kbd>
                ))}
              </span>
            )}
          </div>
        )
      }
    />
  );
}

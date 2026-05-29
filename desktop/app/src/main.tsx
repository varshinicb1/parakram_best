import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { KBarProvider } from 'kbar';
import App from './App';
import './index.css';

const actions = [
  { id: 'build', name: 'Build Firmware', shortcut: ['b'], keywords: 'compile generate', section: 'Actions' },
  { id: 'flash', name: 'Flash Device', shortcut: ['f'], keywords: 'upload deploy', section: 'Actions' },
  { id: 'simulate', name: 'Run Simulation', shortcut: ['s'], keywords: 'wokwi test', section: 'Actions' },
  { id: 'home', name: 'Go Home', shortcut: ['g', 'h'], keywords: 'dashboard', section: 'Navigation' },
  { id: 'new-project', name: 'New Project', shortcut: ['n'], keywords: 'create', section: 'Navigation' },
  { id: 'theme-dark', name: 'Theme: Dark Lab', keywords: 'theme', section: 'Settings' },
  { id: 'theme-cyber', name: 'Theme: Cyberpunk', keywords: 'theme neon', section: 'Settings' },
  { id: 'theme-midnight', name: 'Theme: Midnight', keywords: 'theme dark', section: 'Settings' },
  { id: 'theme-retro', name: 'Theme: Retro Terminal', keywords: 'theme green', section: 'Settings' },
  { id: 'theme-glass', name: 'Theme: Glass UI', keywords: 'theme mac', section: 'Settings' },
];

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <KBarProvider actions={actions}>
      <App />
    </KBarProvider>
  </StrictMode>,
);

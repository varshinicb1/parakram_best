/**
 * App — Root layout with Sidebar + Content Area + Three.js Background.
 * Parakram: 16 spaces — firmware development platform by Vidyutlabs.
 * Includes ErrorBoundary for crash recovery and OnboardingOverlay for new users.
 */
import { lazy, Suspense } from 'react';
import { useAppStore } from './stores/appStore';
import Sidebar from './components/Sidebar';
import SceneBackground from './three/SceneBackground';
import ErrorBoundary from './components/ErrorBoundary';
import OnboardingOverlay from './components/OnboardingOverlay';

// Lazy-load every space for code splitting
const HomeSpace = lazy(() => import('./spaces/HomeSpace'));
const WorkspaceSpace = lazy(() => import('./spaces/WorkspaceSpace'));
const BlocksSpace = lazy(() => import('./spaces/BlocksSpace'));
const DesignerSpace = lazy(() => import('./spaces/DesignerSpace'));
const BlocklyEditorSpace = lazy(() => import('./spaces/BlocklyEditorSpace'));
const SimulatorSpace = lazy(() => import('./spaces/SimulatorSpace'));
const DevicesSpace = lazy(() => import('./spaces/DevicesSpace'));
const TelemetrySpace = lazy(() => import('./spaces/TelemetrySpace'));
const DebugSpace = lazy(() => import('./spaces/DebugSpace'));
const CalibrationPanel = lazy(() => import('./panels/CalibrationPanel'));
const VerificationSpace = lazy(() => import('./spaces/VerificationSpace'));
const SettingsSpace = lazy(() => import('./spaces/SettingsSpace'));
const AuthSpace = lazy(() => import('./spaces/AuthSpace'));
const InstallerSpace = lazy(() => import('./spaces/InstallerSpace'));
const ExtensionSpace = lazy(() => import('./spaces/ExtensionSpace'));
const AdminSpace = lazy(() => import('./spaces/AdminSpace'));

function LoadingFallback() {
  return (
    <div className="flex-1 flex items-center justify-center"
      style={{ background: 'var(--bg-primary)' }}>
      <div className="text-center space-y-3">
        <div className="w-8 h-8 rounded-lg mx-auto animate-pulse"
          style={{ background: 'var(--accent)', opacity: 0.3 }} />
        <p className="text-xs font-medium" style={{ color: 'var(--text-muted)' }}>
          Loading space...
        </p>
      </div>
    </div>
  );
}

const SPACE_MAP: Record<string, React.LazyExoticComponent<React.ComponentType<any>>> = {
  home: HomeSpace,
  workspace: WorkspaceSpace,
  blocks: BlocksSpace,
  designer: DesignerSpace,
  blockly: BlocklyEditorSpace,
  simulator: SimulatorSpace,
  devices: DevicesSpace,
  telemetry: TelemetrySpace,
  debug: DebugSpace,
  calibration: CalibrationPanel,
  verification: VerificationSpace,
  settings: SettingsSpace,
  auth: AuthSpace,
  installer: InstallerSpace,
  extensions: ExtensionSpace,
  admin: AdminSpace,
};

export default function App() {
  const activeSpace = useAppStore((s) => s.activeSpace);
  const SpaceComponent = SPACE_MAP[activeSpace] || HomeSpace;

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-[var(--bg-primary)]">
      <SceneBackground />
      <Sidebar />
      <main className="flex-1 flex flex-col overflow-hidden">
        <ErrorBoundary key={activeSpace}>
          <Suspense fallback={<LoadingFallback />}>
            <SpaceComponent />
          </Suspense>
        </ErrorBoundary>
      </main>
      <OnboardingOverlay />
    </div>
  );
}

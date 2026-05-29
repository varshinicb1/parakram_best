/**
 * ErrorBoundary — Catches React rendering errors and shows a recovery UI.
 * Prevents the entire app from crashing when a single space has an error.
 */
import { Component, type ReactNode } from 'react';
import { AlertTriangle, RotateCcw, Home } from 'lucide-react';

interface Props {
  children: ReactNode;
  fallbackSpace?: string;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: string;
}

export default class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: '' };
  }

  static getDerivedStateFromError(error: Error): Partial<State> {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    this.setState({ errorInfo: info.componentStack || '' });
    console.error('[Parakram] Crash caught:', error, info);
  }

  handleReload = () => {
    this.setState({ hasError: false, error: null, errorInfo: '' });
  };

  handleGoHome = () => {
    this.setState({ hasError: false, error: null, errorInfo: '' });
    // Navigate home via store
    try {
      import('../stores/appStore').then(({ useAppStore }) => {
        useAppStore.getState().setActiveSpace('home');
      });
    } catch {
      window.location.reload();
    }
  };

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex-1 flex items-center justify-center p-8"
          style={{ background: 'var(--bg-primary)' }}>
          <div className="max-w-md w-full text-center space-y-5">
            <div className="w-16 h-16 rounded-2xl mx-auto flex items-center justify-center"
              style={{ background: 'rgba(239, 68, 68, 0.1)', border: '1px solid rgba(239, 68, 68, 0.2)' }}>
              <AlertTriangle size={28} color="#ef4444" />
            </div>

            <div>
              <h2 className="text-lg font-bold mb-1" style={{ color: 'var(--text-primary)' }}>
                Something went wrong
              </h2>
              <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
                This space crashed — but your data is safe. Try reloading the space or go back to Home.
              </p>
            </div>

            {this.state.error && (
              <pre className="text-left text-[10px] font-mono p-3 rounded-xl border overflow-auto max-h-32"
                style={{
                  background: 'var(--bg-secondary)',
                  borderColor: 'var(--border)',
                  color: '#ef4444',
                }}>
                {this.state.error.message}
              </pre>
            )}

            <div className="flex items-center justify-center gap-3">
              <button onClick={this.handleReload}
                className="flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-semibold border hover:bg-[var(--bg-tertiary)] transition-colors"
                style={{ borderColor: 'var(--border)', color: 'var(--text-secondary)' }}>
                <RotateCcw size={14} /> Retry
              </button>
              <button onClick={this.handleGoHome}
                className="flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-bold transition-colors"
                style={{ background: 'var(--accent)', color: 'white' }}>
                <Home size={14} /> Go Home
              </button>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

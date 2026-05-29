/**
 * AuthSpace — Login, Signup, Password Reset UI.
 * JWT-based authentication integrated with backend /api/auth endpoints.
 */
import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { LogIn, UserPlus, KeyRound, Mail, Lock, Eye, EyeOff, ArrowRight, Check, AlertCircle, Hexagon } from 'lucide-react';

type AuthView = 'login' | 'signup' | 'reset';

const API_BASE = 'http://localhost:8000';

export default function AuthSpace() {
  const [view, setView] = useState<AuthView>('login');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const handleLogin = async () => {
    if (!email || !password) { setError('All fields required'); return; }
    setLoading(true); setError('');
    try {
      const res = await fetch(`${API_BASE}/api/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      });
      const data = await res.json();
      if (res.ok) {
        localStorage.setItem('parakram_token', data.token);
        localStorage.setItem('parakram_user', JSON.stringify(data.user));
        setSuccess('Authentication successful. Welcome back.');
      } else {
        setError(data.detail || 'Invalid credentials');
      }
    } catch { setError('Connection failed — is backend running?'); }
    setLoading(false);
  };

  const handleSignup = async () => {
    if (!email || !password || !confirmPassword) { setError('All fields required'); return; }
    if (password !== confirmPassword) { setError('Passwords do not match'); return; }
    if (password.length < 8) { setError('Password must be 8+ characters'); return; }
    setLoading(true); setError('');
    try {
      const res = await fetch(`${API_BASE}/api/auth/signup`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      });
      const data = await res.json();
      if (res.ok) {
        localStorage.setItem('parakram_token', data.token);
        localStorage.setItem('parakram_user', JSON.stringify(data.user));
        setSuccess('Account created successfully.');
      } else {
        setError(data.detail || 'Signup failed');
      }
    } catch { setError('Connection failed'); }
    setLoading(false);
  };

  const handleReset = async () => {
    if (!email) { setError('Email required'); return; }
    setLoading(true); setError('');
    try {
      const res = await fetch(`${API_BASE}/api/auth/reset-password`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email }),
      });
      if (res.ok) {
        setSuccess('Password reset link sent to your email.');
      } else {
        const data = await res.json();
        setError(data.detail || 'Reset failed');
      }
    } catch { setError('Connection failed'); }
    setLoading(false);
  };

  const switchView = (v: AuthView) => { setView(v); setError(''); setSuccess(''); };

  return (
    <div className="flex-1 flex items-center justify-center bg-[var(--bg-primary)] p-6">
      <motion.div
        className="w-full max-w-md bg-[var(--bg-secondary)] border rounded-2xl p-8 shadow-sm"
        style={{ borderColor: 'var(--border)' }}
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.2 }}
      >
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="w-16 h-16 mx-auto mb-4 bg-[var(--bg-primary)] border rounded-2xl flex items-center justify-center shadow-sm" style={{ borderColor: 'var(--border)' }}>
            <Hexagon size={32} style={{ color: 'var(--text-primary)' }} />
          </div>
          <h1 className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>
            {view === 'login' ? 'Welcome Back' : view === 'signup' ? 'Create Account' : 'Reset Password'}
          </h1>
          <p className="text-sm mt-2" style={{ color: 'var(--text-muted)' }}>
            {view === 'login' ? 'Enter your credentials to access the command center.' :
             view === 'signup' ? 'Register a new operator account.' :
             'Recover your access credentials.'}
          </p>
        </div>

        {/* View tabs */}
        <div className="flex gap-2 mb-8 border-b" style={{ borderColor: 'var(--border)' }}>
          {([['login', 'Login', LogIn], ['signup', 'Register', UserPlus], ['reset', 'Reset', KeyRound]] as const).map(([id, label, Icon]) => (
            <button key={id} onClick={() => switchView(id)}
              className="flex items-center justify-center gap-2 flex-1 py-3 text-sm font-semibold border-b-2 transition-colors hover:bg-[var(--bg-primary)] rounded-t-lg"
              style={{
                borderBottomColor: view === id ? 'var(--text-primary)' : 'transparent',
                color: view === id ? 'var(--text-primary)' : 'var(--text-muted)',
              }}>
              <Icon size={16} /> {label}
            </button>
          ))}
        </div>

        {/* Form */}
        <div className="flex flex-col gap-4">
          {/* Email */}
          <div className="relative">
            <Mail size={16} className="absolute left-4 top-1/2 -translate-y-1/2" style={{ color: 'var(--text-muted)' }} />
            <input
              type="email" value={email} onChange={(e) => setEmail(e.target.value)}
              placeholder="Email address"
              className="w-full bg-[var(--bg-primary)] border rounded-xl pl-11 pr-4 py-3 text-sm font-medium outline-none focus:border-[var(--text-primary)] transition-colors shadow-sm"
              style={{ borderColor: 'var(--border)', color: 'var(--text-primary)' }}
            />
          </div>

          {/* Password */}
          {view !== 'reset' && (
            <div className="relative">
              <Lock size={16} className="absolute left-4 top-1/2 -translate-y-1/2" style={{ color: 'var(--text-muted)' }} />
              <input
                type={showPassword ? 'text' : 'password'} value={password} onChange={(e) => setPassword(e.target.value)}
                placeholder="Password"
                className="w-full bg-[var(--bg-primary)] border rounded-xl pl-11 pr-12 py-3 text-sm font-medium outline-none focus:border-[var(--text-primary)] transition-colors shadow-sm"
                style={{ borderColor: 'var(--border)', color: 'var(--text-primary)' }}
              />
              <button onClick={() => setShowPassword(!showPassword)} className="absolute right-4 top-1/2 -translate-y-1/2 p-1 hover:bg-[var(--bg-secondary)] rounded-md transition-colors"
                style={{ color: 'var(--text-muted)' }}>
                {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            </div>
          )}

          {/* Confirm Password */}
          {view === 'signup' && (
            <div className="relative">
              <Lock size={16} className="absolute left-4 top-1/2 -translate-y-1/2" style={{ color: 'var(--text-muted)' }} />
              <input
                type={showPassword ? 'text' : 'password'} value={confirmPassword} onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder="Confirm Password"
                className="w-full bg-[var(--bg-primary)] border rounded-xl pl-11 pr-4 py-3 text-sm font-medium outline-none focus:border-[var(--text-primary)] transition-colors shadow-sm"
                style={{ borderColor: 'var(--border)', color: 'var(--text-primary)' }}
              />
            </div>
          )}

          {/* Error / Success */}
          <AnimatePresence>
            {error && (
              <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }} exit={{ opacity: 0, height: 0 }}
                className="flex items-center gap-2 px-4 py-3 border rounded-xl text-sm font-medium overflow-hidden"
                style={{ borderColor: '#ef444440', color: '#ef4444', background: '#ef444410' }}>
                <AlertCircle size={16} className="shrink-0" /> <span className="truncate">{error}</span>
              </motion.div>
            )}
            {success && (
              <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }} exit={{ opacity: 0, height: 0 }}
                className="flex items-center gap-2 px-4 py-3 border rounded-xl text-sm font-medium overflow-hidden"
                style={{ borderColor: '#22c55e40', color: '#22c55e', background: '#22c55e10' }}>
                <Check size={16} className="shrink-0" /> <span className="truncate">{success}</span>
              </motion.div>
            )}
          </AnimatePresence>

          {/* Submit */}
          <button
            onClick={view === 'login' ? handleLogin : view === 'signup' ? handleSignup : handleReset}
            disabled={loading}
            className="mt-2 flex items-center justify-center gap-2 py-3 rounded-xl text-sm font-bold disabled:opacity-50 transition-colors shadow-sm"
            style={{ background: 'var(--text-primary)', color: 'var(--bg-primary)' }}
          >
            {loading ? 'Processing...' : (
              <>{view === 'login' ? 'Sign In' : view === 'signup' ? 'Create Account' : 'Send Reset Link'} <ArrowRight size={16} /></>
            )}
          </button>
        </div>
      </motion.div>
    </div>
  );
}

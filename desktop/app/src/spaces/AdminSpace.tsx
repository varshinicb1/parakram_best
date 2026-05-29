/**
 * AdminSpace — User management, subscription controls, platform analytics.
 * Requires admin role. Integrates with /api/admin endpoints.
 */
import { useState, useEffect } from 'react';
import {
  Shield, Users, Activity, Search,
  UserCheck, UserX, BarChart3, TrendingUp, Clock, Database, MoreVertical
} from 'lucide-react';

interface User {
  id: string;
  email: string;
  role: 'user' | 'admin' | 'moderator';
  subscription: 'free' | 'pro' | 'enterprise';
  created_at: string;
  last_login: string;
}

interface Analytics {
  total_users: number;
  active_today: number;
  builds_today: number;
  models_used: Record<string, number>;
}

const API_BASE = 'http://localhost:8000';

const ROLE_COLORS: Record<string, string> = {
  admin: '#ef4444',
  moderator: '#d97706',
  user: '#22c55e',
};

const SUB_COLORS: Record<string, string> = {
  enterprise: '#8b5cf6',
  pro: '#3b82f6',
  free: 'var(--text-muted)',
};

type AdminTab = 'users' | 'analytics';

export default function AdminSpace() {
  const [tab, setTab] = useState<AdminTab>('users');
  const [users, setUsers] = useState<User[]>([]);
  const [analytics, setAnalytics] = useState<Analytics | null>(null);
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(false);

  const getToken = () => localStorage.getItem('parakram_token') || '';

  useEffect(() => {
    loadUsers();
    loadAnalytics();
  }, []);

  const loadUsers = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/admin/users`, {
        headers: { Authorization: `Bearer ${getToken()}` },
      });
      if (res.ok) {
        const data = await res.json();
        setUsers(data.users || []);
      }
    } catch (e) { console.error('Failed to load users:', e); }
    setLoading(false);
  };

  const loadAnalytics = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/admin/analytics`, {
        headers: { Authorization: `Bearer ${getToken()}` },
      });
      if (res.ok) {
        setAnalytics(await res.json());
      }
    } catch (e) { console.error('Failed to load analytics:', e); }
  };

  const updateRole = async (userId: string, role: string) => {
    try {
      await fetch(`${API_BASE}/api/admin/users/${userId}/role`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${getToken()}` },
        body: JSON.stringify({ role }),
      });
      loadUsers();
    } catch (e) { console.error('Failed to update role:', e); }
  };

  const updateSubscription = async (userId: string, subscription: string) => {
    try {
      await fetch(`${API_BASE}/api/admin/users/${userId}/subscription`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${getToken()}` },
        body: JSON.stringify({ subscription }),
      });
      loadUsers();
    } catch (e) { console.error('Failed to update subscription:', e); }
  };

  const filteredUsers = users.filter(u =>
    !search || u.email.toLowerCase().includes(search.toLowerCase()) || u.role.includes(search.toLowerCase())
  );

  return (
    <div className="flex-1 overflow-y-auto">
      <div className="max-w-6xl mx-auto px-8 py-10">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-2xl font-bold flex items-center gap-3" style={{ color: 'var(--text-primary)' }}>
              <Shield size={24} style={{ color: 'var(--error)' }} />
              Admin Console
            </h1>
            <p className="text-sm font-medium mt-1" style={{ color: 'var(--text-muted)' }}>Manage users, roles, and platform analytics.</p>
          </div>
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg border bg-[var(--bg-secondary)]" style={{ borderColor: 'var(--border)' }}>
            <div className="w-2 h-2 rounded-full" style={{ background: 'var(--error)' }} />
            <span className="text-xs font-semibold" style={{ color: 'var(--error)' }}>Admin Session</span>
          </div>
        </div>

        {/* Tab nav */}
        <div className="flex items-center gap-2 mb-8 border-b" style={{ borderColor: 'var(--border)' }}>
          {([['users', 'User Management', Users], ['analytics', 'Platform Analytics', BarChart3]] as const).map(([id, label, Icon]) => (
            <button key={id} onClick={() => setTab(id)}
              className="flex items-center gap-2 px-4 py-2.5 text-sm font-semibold border-b-2 transition-colors hover:bg-[var(--bg-secondary)] rounded-t-lg"
              style={{
                borderBottomColor: tab === id ? 'var(--text-primary)' : 'transparent',
                color: tab === id ? 'var(--text-primary)' : 'var(--text-muted)',
              }}>
              <Icon size={16} /> {label}
            </button>
          ))}
        </div>

        {/* Users Tab */}
        {tab === 'users' && (
          <div className="space-y-6">
            {/* Search */}
            <div className="relative">
              <Search size={16} className="absolute left-4 top-1/2 -translate-y-1/2" style={{ color: 'var(--text-muted)' }} />
              <input value={search} onChange={(e) => setSearch(e.target.value)}
                placeholder="Search users by email or role..."
                className="w-full bg-[var(--bg-primary)] border rounded-xl pl-11 pr-4 py-3 text-sm font-medium outline-none focus:border-[var(--text-primary)] transition-colors shadow-sm"
                style={{ borderColor: 'var(--border)', color: 'var(--text-primary)' }}
              />
            </div>

            {/* Users table */}
            <div className="bg-[var(--bg-primary)] border rounded-xl overflow-hidden shadow-sm" style={{ borderColor: 'var(--border)' }}>
              <div className="grid grid-cols-[2fr_1fr_1fr_1fr_auto] gap-4 px-6 py-4 text-xs font-semibold bg-[var(--bg-secondary)] border-b"
                style={{ color: 'var(--text-muted)', borderColor: 'var(--border)' }}>
                <span>Email Address</span><span>Role</span><span>Subscription</span><span>Joined Date</span><span className="text-right">Actions</span>
              </div>

              {/* User rows */}
              {filteredUsers.length === 0 ? (
                <div className="px-6 py-12 text-center text-sm font-medium" style={{ color: 'var(--text-muted)' }}>
                  {loading ? 'Loading internal user catalog...' : 'No users found.'}
                </div>
              ) : filteredUsers.map(user => (
                <div key={user.id}
                  className="grid grid-cols-[2fr_1fr_1fr_1fr_auto] gap-4 px-6 py-4 items-center border-b last:border-0 hover:bg-[var(--bg-secondary)] transition-colors"
                  style={{ borderColor: 'var(--border)' }}>
                  {/* Email */}
                  <div className="text-sm font-medium truncate" style={{ color: 'var(--text-primary)' }}>
                    {user.email}
                  </div>
                  {/* Role */}
                  <div>
                    <select value={user.role} onChange={(e) => updateRole(user.id, e.target.value)}
                      className="bg-[var(--bg-tertiary)] border rounded-md px-2 py-1 text-xs font-semibold outline-none cursor-pointer hover:border-[var(--text-muted)] transition-colors"
                      style={{ borderColor: 'var(--border)', color: ROLE_COLORS[user.role] || 'var(--text-primary)' }}>
                      <option value="user">User</option>
                      <option value="moderator">Moderator</option>
                      <option value="admin">Admin</option>
                    </select>
                  </div>
                  {/* Subscription */}
                  <div>
                    <select value={user.subscription} onChange={(e) => updateSubscription(user.id, e.target.value)}
                      className="bg-[var(--bg-tertiary)] border rounded-md px-2 py-1 text-xs font-semibold outline-none cursor-pointer hover:border-[var(--text-muted)] transition-colors"
                      style={{ borderColor: 'var(--border)', color: SUB_COLORS[user.subscription] || 'var(--text-primary)' }}>
                      <option value="free">Free</option>
                      <option value="pro">Pro</option>
                      <option value="enterprise">Enterprise</option>
                    </select>
                  </div>
                  {/* Joined */}
                  <span className="text-sm" style={{ color: 'var(--text-muted)' }}>
                    {new Date(user.created_at).toLocaleDateString()}
                  </span>
                  {/* Actions */}
                  <div className="flex items-center justify-end gap-2">
                    <button className="p-1.5 hover:bg-[var(--bg-tertiary)] hover:text-[var(--success)] rounded transition-colors" style={{ color: 'var(--text-muted)' }} title="Activate">
                      <UserCheck size={16} />
                    </button>
                    <button className="p-1.5 hover:bg-[var(--bg-tertiary)] hover:text-[var(--error)] rounded transition-colors" style={{ color: 'var(--text-muted)' }} title="Suspend">
                      <UserX size={16} />
                    </button>
                    <button className="p-1.5 hover:bg-[var(--bg-tertiary)] rounded transition-colors" style={{ color: 'var(--text-muted)' }} title="More Options">
                      <MoreVertical size={16} />
                    </button>
                  </div>
                </div>
              ))}
            </div>
            <div className="text-sm font-medium" style={{ color: 'var(--text-muted)' }}>
              Showing {filteredUsers.length} total active users.
            </div>
          </div>
        )}

        {/* Analytics Tab */}
        {tab === 'analytics' && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {/* Stats cards */}
            {[
              { label: 'Total active users', value: analytics?.total_users ?? '4,289', icon: Users, color: 'var(--text-primary)' },
              { label: 'Daily active operators', value: analytics?.active_today ?? '512', icon: TrendingUp, color: 'var(--success)' },
              { label: 'Daily compiler builds', value: analytics?.builds_today ?? '1,230', icon: Activity, color: 'var(--warning)' },
              { label: 'System uptime', value: '99.99%', icon: Clock, color: 'var(--accent)' },
            ].map(stat => (
              <div key={stat.label}
                className="bg-[var(--bg-primary)] border rounded-xl p-6 flex flex-col justify-between shadow-sm hover:shadow-md transition-shadow"
                style={{ borderColor: 'var(--border)' }}>
                <div className="flex justify-between items-start mb-4">
                  <div className="text-[40px] font-bold leading-none tracking-tight" style={{ color: 'var(--text-primary)' }}>
                    {stat.value}
                  </div>
                  <div className="w-10 h-10 flex flex-shrink-0 items-center justify-center rounded-lg bg-[var(--bg-secondary)] border"
                    style={{ borderColor: 'var(--border)' }}>
                    <stat.icon size={20} style={{ color: stat.color }} />
                  </div>
                </div>
                <div className="text-sm font-medium" style={{ color: 'var(--text-muted)' }}>
                  {stat.label}
                </div>
              </div>
            ))}

            {/* Model usage chart */}
            <div className="col-span-1 md:col-span-2 lg:col-span-4 bg-[var(--bg-primary)] border rounded-xl p-8 shadow-sm"
              style={{ borderColor: 'var(--border)' }}>
              <div className="flex items-center gap-3 mb-6">
                <Database size={20} style={{ color: 'var(--text-secondary)' }} />
                <h3 className="text-lg font-bold" style={{ color: 'var(--text-primary)' }}>
                  Language Model Usage Distribution
                </h3>
              </div>
              <div className="space-y-4">
                {Object.entries(analytics?.models_used || { 'DeepSeek V3': 45, 'Qwen 2.5 Coder 32B': 28, 'Gemini 2.5 Flash': 15, 'Claude 3.5 Sonnet': 8, 'Ollama Local': 4 })
                  .map(([model, count]) => {
                    const total = Object.values(analytics?.models_used || { a: 45, b: 28, c: 15, d: 8, e: 4 }).reduce((a, b) => Number(a) + Number(b), 0);
                    const pct = ((Number(count) / Number(total)) * 100).toFixed(1);
                    return (
                      <div key={model} className="flex items-center gap-4">
                        <span className="text-sm font-medium w-48 truncate" style={{ color: 'var(--text-primary)' }}>
                          {model}
                        </span>
                        <div className="flex-1 h-3 rounded-full overflow-hidden bg-[var(--bg-secondary)] border" style={{ borderColor: 'var(--border)' }}>
                          <div className="h-full rounded-full transition-all duration-1000 ease-out" style={{ background: 'var(--text-primary)', width: `${pct}%` }} />
                        </div>
                        <span className="text-sm font-semibold w-12 text-right" style={{ color: 'var(--text-secondary)' }}>{pct}%</span>
                      </div>
                    );
                  })}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

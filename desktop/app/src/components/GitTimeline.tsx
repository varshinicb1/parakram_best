/**
 * GitTimeline — Visual git history with commit messages, diffs, and rollback.
 */
import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { GitBranch, GitCommit, Tag, Upload } from 'lucide-react';

interface Commit {
  hash: string;
  short_hash: string;
  message: string;
  date: string;
  author: string;
}

export default function GitTimeline() {
  const [commits, setCommits] = useState<Commit[]>([]);
  const [releaseVersion, setReleaseVersion] = useState('');

  useEffect(() => {
    // Demo data — in production, fetch from /api/git/history
    setCommits([
      { hash: 'abc1234', short_hash: 'abc1234', message: '[Parakram] Auto-commit firmware update', date: '2026-03-12 10:30:00', author: 'Parakram AI' },
      { hash: 'def5678', short_hash: 'def5678', message: '[Parakram] Added BME280 sensor module', date: '2026-03-12 10:15:00', author: 'Parakram AI' },
      { hash: 'ghi9012', short_hash: 'ghi9012', message: 'Initial commit — Parakram firmware project', date: '2026-03-12 10:00:00', author: 'Parakram AI' },
    ]);
  }, []);

  const createRelease = async () => {
    if (!releaseVersion) return;
    // POST /api/git/release
    setReleaseVersion('');
  };

  return (
    <div className="flex flex-col gap-5 p-5">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className="p-1.5 border rounded-md bg-[var(--bg-secondary)]" style={{ borderColor: 'var(--border)' }}>
            <GitBranch size={16} style={{ color: 'var(--text-primary)' }} />
          </div>
          <h2 className="text-sm font-bold" style={{ color: 'var(--text-primary)' }}>
            Version Control
          </h2>
        </div>
        <div className="flex items-center gap-2">
          <input
            value={releaseVersion}
            onChange={(e) => setReleaseVersion(e.target.value)}
            placeholder="v1.0.0"
            className="w-24 bg-[var(--bg-secondary)] border rounded-md px-2.5 py-1.5 text-xs font-mono outline-none focus:border-[var(--text-primary)] transition-colors shadow-sm"
            style={{ borderColor: 'var(--border)', color: 'var(--text-primary)' }}
          />
          <button onClick={createRelease}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-md border text-xs font-bold transition-all hover:bg-[var(--text-primary)] hover:text-[var(--bg-primary)]"
            style={{ borderColor: 'var(--text-primary)', color: 'var(--text-primary)' }}>
            <Tag size={12} /> Release
          </button>
          <button className="flex items-center gap-1.5 px-3 py-1.5 rounded-md border text-xs font-bold transition-colors hover:bg-[var(--bg-secondary)]"
            style={{ borderColor: 'var(--border)', color: 'var(--text-secondary)' }}>
            <Upload size={12} /> Push
          </button>
        </div>
      </div>

      {/* Timeline */}
      <div className="flex flex-col">
        {commits.map((commit, i) => (
          <motion.div key={commit.hash}
            initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }}
            transition={{ delay: i * 0.1 }}
            className="flex items-start gap-4 py-4 border-l-2 pl-5 relative"
            style={{ borderLeftColor: i === 0 ? 'var(--text-primary)' : 'var(--border)' }}>
            {/* Dot */}
            <div className="absolute -left-[5px] top-5 w-2 h-2 rounded-full border-2"
              style={{ background: 'var(--bg-primary)', borderColor: i === 0 ? 'var(--text-primary)' : 'var(--border)' }} />
            {/* Content */}
            <div className="flex-1">
              <div className="flex items-center gap-2">
                <GitCommit size={14} style={{ color: i === 0 ? 'var(--text-primary)' : 'var(--text-muted)' }} />
                <span className="text-sm font-semibold" style={{ color: i === 0 ? 'var(--text-primary)' : 'var(--text-secondary)' }}>
                  {commit.message}
                </span>
              </div>
              <div className="flex items-center gap-3 mt-1.5 ml-5">
                <span className="text-xs font-mono font-bold" style={{ color: 'var(--text-primary)' }}>
                  {commit.short_hash}
                </span>
                <span className="text-xs font-medium" style={{ color: 'var(--text-muted)' }}>
                  {commit.date}
                </span>
                <span className="text-xs font-medium" style={{ color: 'var(--text-muted)' }}>
                  · {commit.author}
                </span>
              </div>
            </div>
          </motion.div>
        ))}
      </div>
    </div>
  );
}

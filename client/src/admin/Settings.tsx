import { useState, useEffect, useMemo, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import type { SettingItem, HealthResponse, LogLine, SystemInfo } from '../api';
import { fetchSettings, updateSettings, fetchHealth, fetchLogs, fetchSystemInfo, backupUrl } from '../api';

const GROUP_ORDER = ['weather', 'integrations', 'display', 'lightning', 'system'];

const GROUP_LABELS: Record<string, { title: string; icon: string; desc: string }> = {
  weather: { title: 'Weather', icon: '🌤', desc: 'Tempest station and timezone' },
  integrations: { title: 'Integrations', icon: '🔗', desc: 'External services' },
  display: { title: 'Display & Rotation', icon: '📺', desc: 'Page rotation behavior' },
  lightning: { title: 'Lightning Safety', icon: '⚡', desc: 'Pool alert configuration' },
  system: { title: 'System', icon: '⚙️', desc: 'Logging and CORS' },
};

interface SettingsProps {
  onNavigate?: (tab: string) => void;
}

export default function Settings({ onNavigate }: SettingsProps) {
  const token = localStorage.getItem('signboard_token') || '';
  const navigate = useNavigate();

  const [items, setItems] = useState<SettingItem[]>([]);
  const [dirty, setDirty] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);
  const [savingGroup, setSavingGroup] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [toast, setToast] = useState<string | null>(null);
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [sysinfo, setSysinfo] = useState<SystemInfo | null>(null);
  const [logs, setLogs] = useState<LogLine[]>([]);
  const [logLevel, setLogLevel] = useState<string>('');
  const [loadingLogs, setLoadingLogs] = useState(false);

  const load = useCallback(async () => {
    try {
      setItems(await fetchSettings(token));
      setDirty({});
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Load failed');
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => { load(); }, [load]);

  useEffect(() => {
    const loadHealth = async () => {
      try { setHealth(await fetchHealth()); } catch { /* ignore */ }
    };
    loadHealth();
    const id = setInterval(loadHealth, 10000);
    return () => clearInterval(id);
  }, []);

  useEffect(() => {
    (async () => {
      try { setSysinfo(await fetchSystemInfo(token)); } catch { /* ignore */ }
    })();
  }, [token]);

  const loadLogs = useCallback(async () => {
    setLoadingLogs(true);
    try {
      setLogs(await fetchLogs(token, 200, logLevel || undefined));
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Logs unavailable');
    } finally {
      setLoadingLogs(false);
    }
  }, [token, logLevel]);

  const handleBackup = async () => {
    const resp = await fetch(backupUrl(), { headers: { Authorization: `Bearer ${token}` } });
    if (!resp.ok) {
      setError('Backup failed');
      return;
    }
    const blob = await resp.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = resp.headers.get('Content-Disposition')?.match(/filename=([^;]+)/)?.[1]?.replace(/"/g, '') || 'signboard.db';
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
    setToast('Backup downloaded');
    setTimeout(() => setToast(null), 2500);
  };

  const grouped = useMemo(() => {
    const g: Record<string, SettingItem[]> = {};
    for (const item of items) {
      (g[item.group] ||= []).push(item);
    }
    return g;
  }, [items]);

  const setVal = (key: string, value: string) => {
    setDirty((d) => ({ ...d, [key]: value }));
  };

  const effectiveValue = (item: SettingItem): string => (dirty[item.key] ?? item.value);

  const hasChanges = (group: string): boolean => {
    const keys = (grouped[group] || []).map((i) => i.key);
    return keys.some((k) => dirty[k] !== undefined);
  };

  const saveGroup = async (group: string) => {
    const groupKeys = new Set((grouped[group] || []).map((i) => i.key));
    const updates = Object.entries(dirty)
      .filter(([k]) => groupKeys.has(k))
      .map(([key, value]) => ({ key, value }));
    if (updates.length === 0) return;
    setSavingGroup(group);
    setError(null);
    try {
      await updateSettings(token, updates);
      await load();
      setToast(`${GROUP_LABELS[group]?.title || group} saved`);
      setTimeout(() => setToast(null), 2500);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Save failed');
    } finally {
      setSavingGroup(null);
    }
  };

  if (loading) {
    return <div className="p-6 text-gray-500">Loading settings…</div>;
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-800">Settings</h1>
        <p className="text-gray-500 text-sm mt-1">Configure weather, integrations, and system behavior.</p>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
          {error}
        </div>
      )}
      {toast && (
        <div className="bg-green-50 border border-green-200 text-green-700 px-4 py-3 rounded">
          {toast}
        </div>
      )}

      {/* Account section (static — links to the existing change-password flow) */}
      <section className="bg-white rounded-lg shadow p-5">
        <header className="flex items-center gap-3 mb-4">
          <span className="text-2xl">👤</span>
          <div>
            <h2 className="font-bold text-gray-800">Account</h2>
            <p className="text-gray-500 text-sm">Admin credentials</p>
          </div>
        </header>
        <button
          onClick={() => navigate('/admin/change-password')}
          className="px-4 py-2 bg-[#0B1F3A] text-white rounded hover:bg-[#162d52]"
        >
          Change Password
        </button>
      </section>

      {/* Settings groups — dynamic from registry */}
      {GROUP_ORDER.filter((g) => grouped[g]?.length).map((group) => {
        const meta = GROUP_LABELS[group] || { title: group, icon: '•', desc: '' };
        const rows = grouped[group];
        return (
          <section key={group} className="bg-white rounded-lg shadow p-5">
            <header className="flex items-center gap-3 mb-4">
              <span className="text-2xl">{meta.icon}</span>
              <div>
                <h2 className="font-bold text-gray-800">{meta.title}</h2>
                <p className="text-gray-500 text-sm">{meta.desc}</p>
              </div>
            </header>
            <div className="space-y-4">
              {rows.map((item) => (
                <SettingRow key={item.key} item={item} value={effectiveValue(item)} onChange={(v) => setVal(item.key, v)} />
              ))}
            </div>
            <div className="mt-5 flex justify-end">
              <button
                disabled={!hasChanges(group) || savingGroup === group}
                onClick={() => saveGroup(group)}
                className="px-4 py-2 bg-[#C9960C] text-white rounded hover:bg-[#b38309] disabled:opacity-40 disabled:cursor-not-allowed"
              >
                {savingGroup === group ? 'Saving…' : 'Save Changes'}
              </button>
            </div>
          </section>
        );
      })}

      {/* System Health */}
      <section className="bg-white rounded-lg shadow p-5">
        <header className="flex items-center gap-3 mb-4">
          <span className="text-2xl">💚</span>
          <div>
            <h2 className="font-bold text-gray-800">System Health</h2>
            <p className="text-gray-500 text-sm">Live status of background services (updates every 10s)</p>
          </div>
        </header>
        <HealthPanel health={health} />
      </section>

      {/* Links out */}
      <section className="bg-white rounded-lg shadow p-5">
        <header className="flex items-center gap-3 mb-4">
          <span className="text-2xl">🧭</span>
          <div>
            <h2 className="font-bold text-gray-800">Managers</h2>
            <p className="text-gray-500 text-sm">Data managed on their own pages</p>
          </div>
        </header>
        <div className="grid grid-cols-2 gap-3">
          <LinkTile label="Channels" icon="📺" onClick={() => onNavigate?.('channels')} />
          <LinkTile label="Pages" icon="📄" onClick={() => onNavigate?.('pages')} />
          <LinkTile label="Tide Stations" icon="🌊" onClick={() => onNavigate?.('tides')} />
          <LinkTile label="Fishing Locations" icon="🎣" onClick={() => onNavigate?.('fishing')} />
          <LinkTile label="Surf Spots" icon="🏄" onClick={() => onNavigate?.('surf')} />
        </div>
      </section>

      {/* Maintenance */}
      <section className="bg-white rounded-lg shadow p-5">
        <header className="flex items-center gap-3 mb-4">
          <span className="text-2xl">🛠</span>
          <div>
            <h2 className="font-bold text-gray-800">Maintenance</h2>
            <p className="text-gray-500 text-sm">Backups, logs, and diagnostics</p>
          </div>
        </header>

        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="font-medium text-gray-800">Database Backup</p>
              <p className="text-sm text-gray-500">Download a consistent snapshot of signboard.db</p>
            </div>
            <button onClick={handleBackup} className="px-4 py-2 bg-[#0B1F3A] text-white rounded hover:bg-[#162d52]">
              Download .db
            </button>
          </div>

          <div className="border-t border-gray-100 pt-4">
            <div className="flex items-center justify-between mb-3">
              <div>
                <p className="font-medium text-gray-800">Server Logs</p>
                <p className="text-sm text-gray-500">Most recent 200 lines from the server log buffer</p>
              </div>
              <div className="flex items-center gap-2">
                <select
                  value={logLevel}
                  onChange={(e) => setLogLevel(e.target.value)}
                  className="border border-gray-300 rounded px-2 py-1 text-sm"
                >
                  <option value="">All levels</option>
                  <option value="INFO">INFO</option>
                  <option value="WARNING">WARNING</option>
                  <option value="ERROR">ERROR</option>
                </select>
                <button onClick={loadLogs} className="px-3 py-1 bg-gray-200 rounded hover:bg-gray-300 text-sm">
                  {loadingLogs ? 'Loading…' : logs.length ? 'Refresh' : 'View Logs'}
                </button>
              </div>
            </div>
            {logs.length > 0 && (
              <div className="bg-gray-900 rounded p-3 max-h-96 overflow-y-auto font-mono text-xs text-gray-100 space-y-0.5">
                {logs.map((l, i) => (
                  <div key={i} className="flex gap-3">
                    <span className="text-gray-500 shrink-0">
                      {new Date(l.timestamp).toLocaleTimeString([], { hour12: false })}
                    </span>
                    <span className={`shrink-0 w-16 ${levelColor(l.level)}`}>{l.level}</span>
                    <span className="break-all">{l.message}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </section>

      {/* About */}
      <section className="bg-white rounded-lg shadow p-5">
        <header className="flex items-center gap-3 mb-4">
          <span className="text-2xl">ℹ️</span>
          <div>
            <h2 className="font-bold text-gray-800">About</h2>
            <p className="text-gray-500 text-sm">SignBoard build info</p>
          </div>
        </header>
        <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
          <dt className="text-gray-500">Version</dt>
          <dd className="text-gray-800">{sysinfo?.version ?? '—'}</dd>
          <dt className="text-gray-500">Python</dt>
          <dd className="text-gray-800 font-mono text-xs">{sysinfo?.python_version ?? '—'}</dd>
          <dt className="text-gray-500">FastAPI</dt>
          <dd className="text-gray-800 font-mono text-xs">{sysinfo?.fastapi_version ?? '—'}</dd>
          <dt className="text-gray-500">Platform</dt>
          <dd className="text-gray-800 font-mono text-xs">{sysinfo?.platform ?? '—'}</dd>
          <dt className="text-gray-500">Started at</dt>
          <dd className="text-gray-800 font-mono text-xs">
            {sysinfo?.started_at ? new Date(sysinfo.started_at).toLocaleString() : '—'}
          </dd>
          <dt className="text-gray-500">Database size</dt>
          <dd className="text-gray-800">
            {sysinfo?.database_size_bytes != null ? `${(sysinfo.database_size_bytes / (1024 * 1024)).toFixed(2)} MB` : '—'}
          </dd>
          <dt className="text-gray-500">Free disk</dt>
          <dd className="text-gray-800">
            {sysinfo?.disk?.free_gb != null && sysinfo.disk.total_gb != null
              ? `${sysinfo.disk.free_gb} / ${sysinfo.disk.total_gb} GB`
              : '—'}
          </dd>
          <dt className="text-gray-500">Overall status</dt>
          <dd className={health?.status === 'healthy' ? 'text-green-600' : 'text-yellow-600'}>
            {health?.status ?? '—'}
          </dd>
        </dl>
      </section>
    </div>
  );
}

function levelColor(level: string): string {
  if (level === 'ERROR') return 'text-red-400';
  if (level === 'WARNING') return 'text-yellow-400';
  if (level === 'DEBUG') return 'text-gray-400';
  return 'text-green-400';
}


function SettingRow({ item, value, onChange }: { item: SettingItem; value: string; onChange: (v: string) => void }) {
  const id = `setting-${item.key}`;
  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-3 items-start">
      <label htmlFor={id} className="md:col-span-1 pt-2">
        <div className="font-medium text-gray-800">{item.label}</div>
        {item.description && <div className="text-xs text-gray-500 mt-1">{item.description}</div>}
      </label>
      <div className="md:col-span-2">
        {renderInput(item, value, onChange, id)}
      </div>
    </div>
  );
}

function renderInput(item: SettingItem, value: string, onChange: (v: string) => void, id: string) {
  const disabled = item.is_readonly;
  const base = "w-full border border-gray-300 rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-[#C9960C]/40 disabled:bg-gray-100";

  if (item.value_type === 'toggle') {
    const on = value === 'true' || value === '1';
    return (
      <button
        id={id}
        type="button"
        disabled={disabled}
        onClick={() => onChange(on ? 'false' : 'true')}
        className={`px-3 py-1 rounded text-sm font-medium ${on ? 'bg-green-600 text-white' : 'bg-gray-200 text-gray-700'}`}
      >
        {on ? 'Enabled' : 'Disabled'}
      </button>
    );
  }

  if (item.value_type === 'dropdown') {
    const opts = (item.options || '').split(',').map((s) => s.trim()).filter(Boolean);
    return (
      <select id={id} value={value} onChange={(e) => onChange(e.target.value)} disabled={disabled} className={base}>
        {opts.map((o) => <option key={o} value={o}>{o}</option>)}
      </select>
    );
  }

  if (item.value_type === 'number') {
    return <input id={id} type="number" value={value} onChange={(e) => onChange(e.target.value)} disabled={disabled} className={base} />;
  }

  if (item.value_type === 'password') {
    return (
      <input
        id={id}
        type="password"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        disabled={disabled}
        placeholder={item.is_secret && value === '••••••••' ? 'Leave unchanged, or retype to replace' : ''}
        className={base}
      />
    );
  }

  return <input id={id} type="text" value={value} onChange={(e) => onChange(e.target.value)} disabled={disabled} className={base} />;
}

function HealthPanel({ health }: { health: HealthResponse | null }) {
  if (!health) {
    return <p className="text-gray-500 text-sm">Waiting for data…</p>;
  }
  const svcs = health.services || {};
  const rows = Object.entries(svcs);
  const totalDisplays = Object.values(health.connections.display_clients || {}).reduce((a, b) => a + b, 0);
  return (
    <div className="space-y-2">
      {rows.map(([name, s]) => (
        <div key={name} className="flex items-center justify-between border-b border-gray-100 py-2">
          <span className="font-medium text-gray-700 capitalize">{name.replace(/_/g, ' ')}</span>
          <span className="flex items-center gap-3 text-sm">
            <StatusDot status={s.status} />
            <span className="text-gray-600">{s.status}</span>
            {s.last_check && (
              <span className="text-gray-400 text-xs">
                {new Date(s.last_check).toLocaleTimeString()}
              </span>
            )}
          </span>
        </div>
      ))}
      <div className="flex items-center justify-between pt-2 text-sm">
        <span className="font-medium text-gray-700">Display clients connected</span>
        <span className="text-gray-800">{totalDisplays}</span>
      </div>
      <div className="flex items-center justify-between text-sm">
        <span className="font-medium text-gray-700">Admin sessions</span>
        <span className="text-gray-800">{health.connections.admin_clients ?? 0}</span>
      </div>
    </div>
  );
}

function StatusDot({ status }: { status: string }) {
  const color =
    status === 'healthy' ? 'bg-green-500' :
    status === 'degraded' ? 'bg-yellow-500' :
    status === 'disabled' ? 'bg-gray-400' :
    status === 'error' ? 'bg-red-500' :
    'bg-gray-300';
  return <span className={`w-2.5 h-2.5 rounded-full ${color}`} />;
}

function LinkTile({ label, icon, onClick }: { label: string; icon: string; onClick?: () => void }) {
  return (
    <button
      onClick={onClick}
      className="flex items-center gap-3 p-3 border border-gray-200 rounded hover:bg-gray-50 text-left"
    >
      <span className="text-2xl">{icon}</span>
      <span className="font-medium text-gray-800">{label}</span>
    </button>
  );
}

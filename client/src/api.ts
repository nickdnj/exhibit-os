const BASE_URL = '/api';

export interface ChannelDisplay {
  channel: {
    name: string;
    slug: string;
    rotation_interval: number;
  };
  pages: DisplayPage[];
  timestamp: string;
}

export interface DisplayPage {
  page_id: number;
  title: string;
  page_type: string;
  config_json: Record<string, unknown> | null;
  image_path: string | null;
  duration: number;
  announcement?: {
    body_text: string;
    priority: string;
  };
}

export async function fetchChannelDisplay(slug: string): Promise<ChannelDisplay> {
  const resp = await fetch(`${BASE_URL}/channels/${slug}/display`);
  if (!resp.ok) throw new Error(`Channel ${slug} not found`);
  return resp.json();
}

// ---- Settings ----

export interface SettingItem {
  key: string;
  group: string;
  value_type: 'text' | 'number' | 'toggle' | 'dropdown' | 'password';
  label: string;
  description: string | null;
  options: string | null;
  value: string;
  is_secret: boolean;
  is_readonly: boolean;
  sort_order: number;
}

export interface ServiceStatus {
  status: string;
  last_check: string | null;
  last_data?: string | null;
}

export interface HealthResponse {
  status: string;
  timestamp: string;
  services: Record<string, ServiceStatus>;
  connections: {
    display_clients?: Record<string, number>;
    admin_clients?: number;
    total_connections?: number;
  };
}

export async function fetchSettings(token: string): Promise<SettingItem[]> {
  const resp = await fetch(`${BASE_URL}/settings`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!resp.ok) throw new Error('Settings unavailable');
  return resp.json();
}

export async function updateSettings(token: string, updates: { key: string; value: string }[]): Promise<void> {
  const resp = await fetch(`${BASE_URL}/settings`, {
    method: 'PATCH',
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ updates }),
  });
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({}));
    throw new Error(err.detail?.message || err.detail || 'Save failed');
  }
}

export async function fetchHealth(): Promise<HealthResponse> {
  const resp = await fetch(`${BASE_URL}/health`);
  if (!resp.ok) throw new Error('Health check unavailable');
  return resp.json();
}

export interface LogLine {
  timestamp: string;
  level: string;
  logger: string;
  message: string;
}

export async function fetchLogs(token: string, limit = 200, level?: string): Promise<LogLine[]> {
  const params = new URLSearchParams({ limit: String(limit) });
  if (level) params.set('level', level);
  const resp = await fetch(`${BASE_URL}/admin/logs?${params}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!resp.ok) throw new Error('Logs unavailable');
  const data = await resp.json();
  return data.lines || [];
}

export interface SystemInfo {
  version: string;
  python_version: string;
  fastapi_version: string;
  platform: string;
  disk: { total_gb: number | null; free_gb: number | null };
  database_size_bytes: number | null;
  uploads_dir: string;
  started_at: string | null;
}

export async function fetchSystemInfo(token: string): Promise<SystemInfo> {
  const resp = await fetch(`${BASE_URL}/admin/info`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!resp.ok) throw new Error('System info unavailable');
  return resp.json();
}

export function backupUrl(): string {
  return `${BASE_URL}/admin/backup`;
}

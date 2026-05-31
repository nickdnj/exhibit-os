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

export interface WeatherCurrent {
  temperature_f: number | null;
  feels_like_f: number | null;
  humidity: number | null;
  wind_speed_mph: number | null;
  wind_direction: number | null;
  wind_gust_mph: number | null;
  pressure_inhg: number | null;
  pressure_trend: string | null;
  uv_index: number | null;
  rain_today_in: number | null;
  conditions: string | null;
  icon: string | null;
  last_updated: string | null;
}

export interface ForecastDay {
  day_name: string;
  high_f: number;
  low_f: number;
  conditions: string;
  icon: string;
  precip_pct: number;
}

export interface ForecastHour {
  time: string;
  temp_f: number | null;
  conditions: string;
  icon: string;
  precip_pct: number;
  wind_mph: number | null;
  wind_dir: string | null;
}

export interface TideEvent {
  type: 'High' | 'Low';
  time: string;
  height_ft: number;
}

export interface TidePrediction {
  time: string;
  date: string;
  height_ft: number;
  type: 'High' | 'Low';
}

export interface TideStationState {
  noaa_id: string;
  name: string;
  is_local: boolean;
  status: 'available' | 'unavailable';
  direction: 'rising' | 'falling' | 'unknown';
  next_tide: TideEvent | null;
  prev_tide: TideEvent | null;
  predictions: TidePrediction[];
  last_fetched: string | null;
  error?: string | null;
}

export interface TideState {
  stations: TideStationState[];
  count: number;
}

export interface TideStationConfig {
  id: number;
  noaa_id: string;
  name: string;
  is_local: boolean;
  enabled: boolean;
  sort_order: number;
}

export interface FishingWindow {
  start: string;
  end: string;
  length_min: number;
  avg_score: number;
  peak_score: number;
  rating: number;
  reasons: string[];
}

export interface FishingLocationReport {
  id: number;
  name: string;
  latitude: number;
  longitude: number;
  is_local: boolean;
  date: string;
  overall_rating: number;
  sun: { sunrise: string | null; sunset: string | null };
  moon: {
    phase_name: string;
    illumination_pct: number;
    rise: string | null;
    set: string | null;
  };
  tides: { type: 'High' | 'Low'; time: string; height_ft: number }[];
  best_windows: FishingWindow[];
}

export interface FishingReport {
  date: string;
  locations: FishingLocationReport[];
  count: number;
}

export interface FishingLocationConfig {
  id: number;
  name: string;
  latitude: number;
  longitude: number;
  tide_station_id: number | null;
  is_local: boolean;
  enabled: boolean;
  sort_order: number;
}

export interface SurfHour {
  time: string;
  wave_height_ft: number | null;
  wave_period_s: number | null;
}

export interface SurfWind {
  speed_mph: number | null;
  direction_deg: number | null;
  direction_compass: string | null;
  relationship: 'offshore' | 'side-offshore' | 'cross-shore' | 'side-onshore' | 'onshore' | 'unknown';
}

export interface SurfSpotReport {
  id: number;
  name: string;
  is_local: boolean;
  latitude: number;
  longitude: number;
  shore_facing_deg: number;
  status: 'available' | 'unavailable';
  error?: string | null;
  rating: number;
  label: string;
  wave_height_ft: number | null;
  wave_period_s: number | null;
  wave_direction_deg: number | null;
  wave_direction_compass: string | null;
  swell_height_ft: number | null;
  swell_period_s: number | null;
  wind_wave_height_ft: number | null;
  wind: SurfWind;
  hourly: SurfHour[];
  fetched_at: string | null;
}

export interface SurfReport {
  spots: SurfSpotReport[];
  count: number;
}

export interface SurfSpotConfig {
  id: number;
  name: string;
  latitude: number;
  longitude: number;
  shore_facing_deg: number;
  is_local: boolean;
  enabled: boolean;
  sort_order: number;
}

export async function fetchChannelDisplay(slug: string): Promise<ChannelDisplay> {
  const resp = await fetch(`${BASE_URL}/channels/${slug}/display`);
  if (!resp.ok) throw new Error(`Channel ${slug} not found`);
  return resp.json();
}

export async function fetchWeatherCurrent(): Promise<WeatherCurrent> {
  const resp = await fetch(`${BASE_URL}/weather/current`);
  if (!resp.ok) throw new Error('Weather data unavailable');
  return resp.json();
}

export async function fetchWeatherForecast(): Promise<ForecastDay[]> {
  const resp = await fetch(`${BASE_URL}/weather/forecast`);
  if (!resp.ok) throw new Error('Forecast data unavailable');
  return resp.json();
}

export async function fetchWeatherHourly(): Promise<ForecastHour[]> {
  const resp = await fetch(`${BASE_URL}/weather/hourly`);
  if (!resp.ok) throw new Error('Hourly forecast unavailable');
  return resp.json();
}

export async function fetchTides(): Promise<TideState> {
  const resp = await fetch(`${BASE_URL}/tides`);
  if (!resp.ok) throw new Error('Tide data unavailable');
  return resp.json();
}

export async function fetchFishing(): Promise<FishingReport> {
  const resp = await fetch(`${BASE_URL}/fishing`);
  if (!resp.ok) throw new Error('Fishing report unavailable');
  return resp.json();
}

export async function fetchSurf(): Promise<SurfReport> {
  const resp = await fetch(`${BASE_URL}/surf`);
  if (!resp.ok) throw new Error('Surf report unavailable');
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

// ---- Lightning ----

export interface LightningStrike {
  epoch: number;
  time: string;
  distance_mi: number;
  source: string;
}

export interface LightningState {
  state: 'idle' | 'alert' | 'countdown' | 'offline';
  state_since: string;
  enabled: boolean;
  threshold_mi: number;
  countdown_minutes: number;
  alert_channels: string[];
  last_strike: LightningStrike | null;
  nearest_strike_in_alert: LightningStrike | null;
  countdown_remaining_seconds: number | null;
  countdown_end: string | null;
  sources: { tempest_weather: boolean; tempest_cloud: boolean };
}

export async function fetchLightningState(): Promise<LightningState> {
  const resp = await fetch(`${BASE_URL}/lightning/state`);
  if (!resp.ok) throw new Error('Lightning state unavailable');
  return resp.json();
}

export async function simulateStrike(token: string, distance_km: number): Promise<LightningState> {
  const resp = await fetch(`${BASE_URL}/lightning/simulate?distance_km=${distance_km}`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!resp.ok) throw new Error('Simulate failed');
  const data = await resp.json();
  return data.state;
}

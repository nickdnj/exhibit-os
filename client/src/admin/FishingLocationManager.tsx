import { useState, useEffect } from 'react';
import type { FishingLocationConfig, TideStationConfig } from '../api';

type Editable = Omit<FishingLocationConfig, 'id'> & { id?: number };

const BLANK: Omit<FishingLocationConfig, 'id'> = {
  name: '',
  latitude: 40.33,
  longitude: -73.98,
  tide_station_id: null,
  is_local: false,
  enabled: true,
  sort_order: 0,
};

export default function FishingLocationManager() {
  const [locations, setLocations] = useState<FishingLocationConfig[]>([]);
  const [stations, setStations] = useState<TideStationConfig[]>([]);
  const [editing, setEditing] = useState<Editable | null>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const token = localStorage.getItem('signboard_token');

  useEffect(() => {
    load();
  }, []);

  const load = async () => {
    const [l, s] = await Promise.all([
      fetch('/api/fishing-locations', { headers: { Authorization: `Bearer ${token}` } }).then((r) => r.json()),
      fetch('/api/tide-stations', { headers: { Authorization: `Bearer ${token}` } }).then((r) => r.json()),
    ]);
    setLocations(l);
    setStations(s);
  };

  const save = async () => {
    if (!editing) return;
    setSaving(true);
    setError(null);
    try {
      const url = editing.id ? `/api/fishing-locations/${editing.id}` : '/api/fishing-locations';
      const method = editing.id ? 'PUT' : 'POST';
      const { id: _id, ...body } = editing;
      const resp = await fetch(url, {
        method,
        headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      if (!resp.ok) {
        const err = await resp.json().catch(() => ({}));
        throw new Error(err.detail || 'Save failed');
      }
      setEditing(null);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Save failed');
    } finally {
      setSaving(false);
    }
  };

  const remove = async (id: number) => {
    if (!confirm('Remove this fishing location?')) return;
    await fetch(`/api/fishing-locations/${id}`, {
      method: 'DELETE',
      headers: { Authorization: `Bearer ${token}` },
    });
    await load();
  };

  const toggle = async (loc: FishingLocationConfig) => {
    await fetch(`/api/fishing-locations/${loc.id}`, {
      method: 'PUT',
      headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({ enabled: !loc.enabled }),
    });
    await load();
  };

  if (editing) {
    return (
      <div>
        <button onClick={() => setEditing(null)} className="text-sm text-gray-500 hover:text-gray-700 mb-4">
          ← Back to locations
        </button>
        <h1 className="text-2xl font-bold text-gray-800 mb-6">
          {editing.id ? 'Edit Fishing Location' : 'Add Fishing Location'}
        </h1>

        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 max-w-xl space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Name</label>
            <input type="text" value={editing.name}
              onChange={(e) => setEditing({ ...editing, name: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg" />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Latitude</label>
              <input type="number" step="0.0001" value={editing.latitude}
                onChange={(e) => setEditing({ ...editing, latitude: parseFloat(e.target.value) || 0 })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Longitude</label>
              <input type="number" step="0.0001" value={editing.longitude}
                onChange={(e) => setEditing({ ...editing, longitude: parseFloat(e.target.value) || 0 })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg" />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Tide Station</label>
            <select value={editing.tide_station_id ?? ''}
              onChange={(e) => setEditing({ ...editing, tide_station_id: e.target.value ? parseInt(e.target.value, 10) : null })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg">
              <option value="">— None —</option>
              {stations.map((s) => (
                <option key={s.id} value={s.id}>{s.name} (NOAA {s.noaa_id})</option>
              ))}
            </select>
            <p className="text-xs text-gray-500 mt-1">
              Tide station controls the tide timing used for this location's fishing calc.
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Sort Order</label>
            <input type="number" value={editing.sort_order}
              onChange={(e) => setEditing({ ...editing, sort_order: parseInt(e.target.value, 10) || 0 })}
              className="w-24 px-3 py-2 border border-gray-300 rounded-lg" />
          </div>

          <label className="flex items-center gap-3 cursor-pointer">
            <input type="checkbox" checked={editing.is_local}
              onChange={(e) => setEditing({ ...editing, is_local: e.target.checked })} className="w-4 h-4" />
            <span className="text-sm text-gray-700">Mark as local (featured)</span>
          </label>

          <label className="flex items-center gap-3 cursor-pointer">
            <input type="checkbox" checked={editing.enabled}
              onChange={(e) => setEditing({ ...editing, enabled: e.target.checked })} className="w-4 h-4" />
            <span className="text-sm text-gray-700">Enabled</span>
          </label>

          {error && <p className="text-sm text-red-600">{error}</p>}

          <div className="flex gap-3 pt-4">
            <button onClick={save} disabled={saving || !editing.name.trim()}
              className="px-5 py-2 bg-[#0B1F3A] text-white rounded-lg hover:bg-[#0B1F3A]/90 disabled:opacity-50">
              {saving ? 'Saving...' : 'Save'}
            </button>
            <button onClick={() => setEditing(null)}
              className="px-5 py-2 border border-gray-300 rounded-lg hover:bg-gray-50">Cancel</button>
          </div>
        </div>
      </div>
    );
  }

  const stationName = (id: number | null) => {
    if (id === null) return '— none —';
    const s = stations.find((x) => x.id === id);
    return s ? s.name : `#${id}`;
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-800">Fishing Locations</h1>
        <button onClick={() => setEditing({ ...BLANK, sort_order: locations.length })}
          className="px-4 py-2 bg-[#0B1F3A] text-white rounded-lg hover:bg-[#0B1F3A]/90">
          + Add Location
        </button>
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-gray-200 divide-y divide-gray-100">
        {locations.length === 0 && (
          <div className="p-8 text-center text-gray-400">
            No fishing locations yet. Add one to enable the Fishing Report page.
          </div>
        )}
        {locations.map((loc) => (
          <div key={loc.id} className={`flex items-center gap-4 p-4 ${!loc.enabled ? 'opacity-50' : ''}`}>
            <span className="text-2xl">🎣</span>
            <div className="flex-1">
              <div className="flex items-center gap-2">
                <span className="font-semibold text-gray-800">{loc.name}</span>
                {loc.is_local && (
                  <span className="text-xs bg-[#C9960C]/20 text-[#8A6B00] px-2 py-0.5 rounded">Local</span>
                )}
              </div>
              <p className="text-xs text-gray-500 mt-1">
                {loc.latitude.toFixed(3)}, {loc.longitude.toFixed(3)} · tide: {stationName(loc.tide_station_id)}
              </p>
            </div>

            <button onClick={() => toggle(loc)}
              className={`w-12 h-7 rounded-full transition-colors relative ${loc.enabled ? 'bg-green-500' : 'bg-gray-300'}`}>
              <div className={`w-5 h-5 bg-white rounded-full absolute top-1 transition-transform ${loc.enabled ? 'translate-x-6' : 'translate-x-1'}`} />
            </button>
            <button onClick={() => setEditing({ ...loc })} className="text-sm text-blue-600 hover:underline">Edit</button>
            <button onClick={() => remove(loc.id)} className="text-sm text-red-600 hover:underline">Remove</button>
          </div>
        ))}
      </div>
    </div>
  );
}

import { useState, useEffect } from 'react';
import type { TideStationConfig } from '../api';

const BLANK: Omit<TideStationConfig, 'id'> = {
  noaa_id: '',
  name: '',
  is_local: false,
  enabled: true,
  sort_order: 0,
};

export default function TideStationManager() {
  const [stations, setStations] = useState<TideStationConfig[]>([]);
  const [editing, setEditing] = useState<Omit<TideStationConfig, 'id'> & { id?: number } | null>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const token = localStorage.getItem('signboard_token');

  useEffect(() => {
    load();
  }, []);

  const load = async () => {
    const resp = await fetch('/api/tide-stations', {
      headers: { Authorization: `Bearer ${token}` },
    });
    setStations(await resp.json());
  };

  const save = async () => {
    if (!editing) return;
    setSaving(true);
    setError(null);
    try {
      const url = editing.id ? `/api/tide-stations/${editing.id}` : '/api/tide-stations';
      const method = editing.id ? 'PUT' : 'POST';
      const { id: _id, ...body } = editing;
      const resp = await fetch(url, {
        method,
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
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
    if (!confirm('Remove this tide station?')) return;
    await fetch(`/api/tide-stations/${id}`, {
      method: 'DELETE',
      headers: { Authorization: `Bearer ${token}` },
    });
    await load();
  };

  const toggleEnabled = async (s: TideStationConfig) => {
    await fetch(`/api/tide-stations/${s.id}`, {
      method: 'PUT',
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ enabled: !s.enabled }),
    });
    await load();
  };

  if (editing) {
    return (
      <div>
        <button onClick={() => setEditing(null)} className="text-sm text-gray-500 hover:text-gray-700 mb-4">
          ← Back to stations
        </button>
        <h1 className="text-2xl font-bold text-gray-800 mb-6">
          {editing.id ? 'Edit Tide Station' : 'Add Tide Station'}
        </h1>

        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 max-w-xl space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">NOAA Station ID</label>
            <input
              type="text"
              value={editing.noaa_id}
              onChange={(e) => setEditing({ ...editing, noaa_id: e.target.value })}
              placeholder="e.g. 8531680"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
            <p className="text-xs text-gray-500 mt-1">
              Find stations at{' '}
              <a href="https://tidesandcurrents.noaa.gov/stations.html?type=Tide+Predictions"
                target="_blank" rel="noreferrer" className="text-blue-600 hover:underline">
                tidesandcurrents.noaa.gov
              </a>
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Display Name</label>
            <input
              type="text"
              value={editing.name}
              onChange={(e) => setEditing({ ...editing, name: e.target.value })}
              placeholder="e.g. Sandy Hook"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Sort Order</label>
            <input
              type="number"
              value={editing.sort_order}
              onChange={(e) => setEditing({ ...editing, sort_order: parseInt(e.target.value, 10) || 0 })}
              className="w-24 px-3 py-2 border border-gray-300 rounded-lg"
            />
          </div>

          <label className="flex items-center gap-3 cursor-pointer">
            <input
              type="checkbox"
              checked={editing.is_local}
              onChange={(e) => setEditing({ ...editing, is_local: e.target.checked })}
              className="w-4 h-4"
            />
            <span className="text-sm text-gray-700">Mark as local station (featured)</span>
          </label>

          <label className="flex items-center gap-3 cursor-pointer">
            <input
              type="checkbox"
              checked={editing.enabled}
              onChange={(e) => setEditing({ ...editing, enabled: e.target.checked })}
              className="w-4 h-4"
            />
            <span className="text-sm text-gray-700">Enabled</span>
          </label>

          {error && <p className="text-sm text-red-600">{error}</p>}

          <div className="flex gap-3 pt-4">
            <button
              onClick={save}
              disabled={saving || !editing.noaa_id.trim() || !editing.name.trim()}
              className="px-5 py-2 bg-[#0B1F3A] text-white rounded-lg hover:bg-[#0B1F3A]/90 disabled:opacity-50"
            >
              {saving ? 'Saving...' : 'Save'}
            </button>
            <button onClick={() => setEditing(null)} className="px-5 py-2 border border-gray-300 rounded-lg hover:bg-gray-50">
              Cancel
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-800">Tide Stations</h1>
        <button
          onClick={() => setEditing({ ...BLANK, sort_order: stations.length })}
          className="px-4 py-2 bg-[#0B1F3A] text-white rounded-lg hover:bg-[#0B1F3A]/90"
        >
          + Add Station
        </button>
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-gray-200 divide-y divide-gray-100">
        {stations.length === 0 && (
          <div className="p-8 text-center text-gray-400">
            No tide stations configured. Add one to show tides on the display.
          </div>
        )}
        {stations.map((s) => (
          <div key={s.id} className={`flex items-center gap-4 p-4 ${!s.enabled ? 'opacity-50' : ''}`}>
            <span className="text-2xl">🌊</span>
            <div className="flex-1">
              <div className="flex items-center gap-2">
                <span className="font-semibold text-gray-800">{s.name}</span>
                {s.is_local && (
                  <span className="text-xs bg-[#C9960C]/20 text-[#8A6B00] px-2 py-0.5 rounded">Local</span>
                )}
              </div>
              <p className="text-xs text-gray-500 mt-1">NOAA {s.noaa_id} · sort {s.sort_order}</p>
            </div>

            <button
              onClick={() => toggleEnabled(s)}
              className={`w-12 h-7 rounded-full transition-colors relative ${
                s.enabled ? 'bg-green-500' : 'bg-gray-300'
              }`}
              title={s.enabled ? 'Enabled' : 'Disabled'}
            >
              <div
                className={`w-5 h-5 bg-white rounded-full absolute top-1 transition-transform ${
                  s.enabled ? 'translate-x-6' : 'translate-x-1'
                }`}
              />
            </button>

            <button
              onClick={() => setEditing({ ...s })}
              className="text-sm text-blue-600 hover:underline"
            >
              Edit
            </button>
            <button
              onClick={() => remove(s.id)}
              className="text-sm text-red-600 hover:underline"
            >
              Remove
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}

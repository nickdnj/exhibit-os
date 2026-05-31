import { useState, useEffect } from 'react';

interface ChannelStatus {
  id: number;
  name: string;
  slug: string;
  rotation_interval: number;
  is_active: boolean;
  page_count: number;
}

interface HealthData {
  status: string;
  services: Record<string, { status: string; last_check: string | null }>;
}

export default function AdminDashboard() {
  const [channels, setChannels] = useState<ChannelStatus[]>([]);
  const [health, setHealth] = useState<HealthData | null>(null);
  const token = localStorage.getItem('signboard_token');

  useEffect(() => {
    const headers = { Authorization: `Bearer ${token}` };

    fetch('/api/channels', { headers })
      .then((r) => r.json())
      .then(setChannels)
      .catch(() => {});

    fetch('/health')
      .then((r) => r.json())
      .then(setHealth)
      .catch(() => {});
  }, [token]);

  const statusColor = (status: string) => {
    switch (status) {
      case 'healthy': return 'bg-green-500';
      case 'degraded': return 'bg-yellow-500';
      case 'error': return 'bg-red-500';
      case 'disabled': return 'bg-gray-400';
      default: return 'bg-gray-300';
    }
  };

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-800 mb-6">Dashboard</h1>

      {/* System Status */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 mb-6">
        <h2 className="text-lg font-semibold text-gray-700 mb-4">System Status</h2>
        <div className="flex items-center gap-2 mb-4">
          <div className={`w-3 h-3 rounded-full ${statusColor(health?.status || 'unknown')}`} />
          <span className="text-gray-600 capitalize">{health?.status || 'Checking...'}</span>
        </div>
        {health?.services && (
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            {Object.entries(health.services).map(([name, svc]) => (
              <div key={name} className="flex items-center gap-2 p-3 bg-gray-50 rounded-lg">
                <div className={`w-2 h-2 rounded-full ${statusColor(svc.status)}`} />
                <span className="text-sm text-gray-600">{name.replace(/_/g, ' ')}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Channels */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 mb-6">
        <h2 className="text-lg font-semibold text-gray-700 mb-4">Channels</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {channels.map((ch) => (
            <div key={ch.id} className="p-4 border border-gray-200 rounded-lg">
              <div className="flex items-center justify-between mb-2">
                <h3 className="font-semibold text-gray-800">{ch.name}</h3>
                <span className={`text-xs px-2 py-1 rounded-full ${ch.is_active ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'}`}>
                  {ch.is_active ? 'Active' : 'Inactive'}
                </span>
              </div>
              <p className="text-sm text-gray-500">
                {ch.page_count} pages &middot; {ch.rotation_interval}s interval
              </p>
              <p className="text-xs text-gray-400 mt-1">
                /display/{ch.slug}
              </p>
            </div>
          ))}
        </div>
      </div>

      {/* Quick Actions */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
        <h2 className="text-lg font-semibold text-gray-700 mb-4">Quick Actions</h2>
        <div className="flex flex-wrap gap-3">
          <button className="px-4 py-2 bg-[#0B1F3A] text-white rounded-lg text-sm font-medium hover:bg-[#132B50] transition-colors">
            + New Announcement
          </button>
          <button className="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg text-sm font-medium hover:bg-gray-50 transition-colors">
            View Office Display
          </button>
          <button className="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg text-sm font-medium hover:bg-gray-50 transition-colors">
            View Pool Display
          </button>
        </div>
      </div>
    </div>
  );
}

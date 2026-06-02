import { useState, useEffect } from 'react';

interface PageAssignment {
  assignment_id: number;
  page_id: number;
  sort_order: number;
  is_enabled: boolean;
  duration_override: number | null;
  page: {
    id: number;
    title: string;
    page_type: string;
    is_system: boolean;
    is_published: boolean;
  };
}

interface Channel {
  id: number;
  name: string;
  slug: string;
  rotation_interval: number;
  is_active: boolean;
  page_count: number;
  pages?: PageAssignment[];
}

interface AvailablePage {
  id: number;
  title: string;
  page_type: string;
  is_system: boolean;
  is_published: boolean;
}

export default function ChannelManager() {
  const [channels, setChannels] = useState<Channel[]>([]);
  const [selectedChannel, setSelectedChannel] = useState<Channel | null>(null);
  const [saving, setSaving] = useState(false);
  const [showAddPicker, setShowAddPicker] = useState(false);
  const [allPages, setAllPages] = useState<AvailablePage[]>([]);
  const token = localStorage.getItem('exhibitos_token');

  useEffect(() => {
    loadChannels();
  }, []);

  const loadChannels = async () => {
    const resp = await fetch('/api/channels', {
      headers: { Authorization: `Bearer ${token}` },
    });
    setChannels(await resp.json());
  };

  const loadChannelDetail = async (id: number) => {
    const resp = await fetch(`/api/channels/${id}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    setSelectedChannel(await resp.json());
  };

  const loadAllPages = async () => {
    const resp = await fetch('/api/pages', { headers: { Authorization: `Bearer ${token}` } });
    setAllPages(await resp.json());
  };

  const addPage = async (pageId: number) => {
    if (!selectedChannel?.pages) return;
    const existing = selectedChannel.pages.map((p) => ({
      page_id: p.page_id,
      sort_order: p.sort_order,
      is_enabled: p.is_enabled,
      duration_override: p.duration_override,
    }));
    existing.push({
      page_id: pageId,
      sort_order: existing.length,
      is_enabled: true,
      duration_override: null,
    });
    setSaving(true);
    try {
      const resp = await fetch(`/api/channels/${selectedChannel.id}/pages`, {
        method: 'PUT',
        headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ pages: existing }),
      });
      setSelectedChannel(await resp.json());
      setShowAddPicker(false);
    } finally {
      setSaving(false);
    }
  };

  const removePage = async (pageId: number) => {
    if (!selectedChannel?.pages) return;
    if (!confirm('Remove this page from the channel?')) return;
    const remaining = selectedChannel.pages
      .filter((p) => p.page_id !== pageId)
      .map((p, i) => ({
        page_id: p.page_id,
        sort_order: i,
        is_enabled: p.is_enabled,
        duration_override: p.duration_override,
      }));
    setSaving(true);
    try {
      const resp = await fetch(`/api/channels/${selectedChannel.id}/pages`, {
        method: 'PUT',
        headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ pages: remaining }),
      });
      setSelectedChannel(await resp.json());
    } finally {
      setSaving(false);
    }
  };

  const movePage = async (index: number, direction: 'up' | 'down') => {
    if (!selectedChannel?.pages) return;

    const pages = [...selectedChannel.pages];
    const swapIndex = direction === 'up' ? index - 1 : index + 1;
    if (swapIndex < 0 || swapIndex >= pages.length) return;

    [pages[index], pages[swapIndex]] = [pages[swapIndex], pages[index]];

    // Update sort orders
    const assignments = pages.map((p, i) => ({
      page_id: p.page_id,
      sort_order: i,
      is_enabled: p.is_enabled,
      duration_override: p.duration_override,
    }));

    setSaving(true);
    try {
      const resp = await fetch(`/api/channels/${selectedChannel.id}/pages`, {
        method: 'PUT',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ pages: assignments }),
      });
      setSelectedChannel(await resp.json());
    } finally {
      setSaving(false);
    }
  };

  const togglePage = async (index: number) => {
    if (!selectedChannel?.pages) return;

    const pages = [...selectedChannel.pages];
    pages[index] = { ...pages[index], is_enabled: !pages[index].is_enabled };

    const assignments = pages.map((p, i) => ({
      page_id: p.page_id,
      sort_order: i,
      is_enabled: p.is_enabled,
      duration_override: p.duration_override,
    }));

    setSaving(true);
    try {
      const resp = await fetch(`/api/channels/${selectedChannel.id}/pages`, {
        method: 'PUT',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ pages: assignments }),
      });
      setSelectedChannel(await resp.json());
    } finally {
      setSaving(false);
    }
  };

  const pageTypeIcon = (type: string) => {
    switch (type) {
      case 'announcement': return '📢';
      default: return '📄';
    }
  };

  if (selectedChannel) {
    return (
      <div>
        <button
          onClick={() => setSelectedChannel(null)}
          className="text-sm text-gray-500 hover:text-gray-700 mb-4 flex items-center gap-1"
        >
          ← Back to channels
        </button>

        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold text-gray-800">{selectedChannel.name}</h1>
            <p className="text-gray-400 text-sm">/display/{selectedChannel.slug}</p>
          </div>
          {saving && <span className="text-sm text-gray-400">Saving...</span>}
        </div>

        {/* Page list */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200">
          <div className="p-4 border-b border-gray-100 flex items-center justify-between">
            <h2 className="font-semibold text-gray-700">Pages ({selectedChannel.pages?.length || 0})</h2>
            <button
              onClick={async () => { await loadAllPages(); setShowAddPicker(true); }}
              className="px-3 py-1.5 text-sm bg-[#0B1F3A] text-white rounded-lg hover:bg-[#0B1F3A]/90"
            >
              + Add Page
            </button>
          </div>

          {showAddPicker && (() => {
            const assignedIds = new Set((selectedChannel.pages || []).map((p) => p.page_id));
            const available = allPages.filter((p) => !assignedIds.has(p.id) && p.is_published);
            return (
              <div className="p-4 bg-gray-50 border-b border-gray-100">
                <div className="flex items-center justify-between mb-3">
                  <p className="text-sm font-semibold text-gray-700">Select a page to add:</p>
                  <button onClick={() => setShowAddPicker(false)} className="text-sm text-gray-500 hover:text-gray-700">Cancel</button>
                </div>
                {available.length === 0 ? (
                  <p className="text-sm text-gray-400">No pages available to add.</p>
                ) : (
                  <div className="grid gap-2">
                    {available.map((p) => (
                      <button
                        key={p.id}
                        onClick={() => addPage(p.id)}
                        disabled={saving}
                        className="flex items-center gap-3 p-3 bg-white border border-gray-200 rounded-lg hover:border-[#0B1F3A] text-left disabled:opacity-50"
                      >
                        <span>{pageTypeIcon(p.page_type)}</span>
                        <span className="font-medium text-gray-800 flex-1">{p.title}</span>
                        {p.is_system && (
                          <span className="text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded">System</span>
                        )}
                        <span className="text-xs text-gray-400">{p.page_type.replace(/_/g, ' ')}</span>
                      </button>
                    ))}
                  </div>
                )}
              </div>
            );
          })()}

          {selectedChannel.pages?.map((assignment, i) => (
            <div
              key={assignment.assignment_id}
              className={`flex items-center gap-3 p-4 border-b border-gray-50 last:border-0 ${
                !assignment.is_enabled ? 'opacity-50' : ''
              }`}
            >
              {/* Reorder arrows */}
              <div className="flex flex-col gap-1">
                <button
                  onClick={() => movePage(i, 'up')}
                  disabled={i === 0}
                  className="w-8 h-8 flex items-center justify-center rounded bg-gray-100 hover:bg-gray-200 disabled:opacity-30 disabled:hover:bg-gray-100 text-gray-600"
                >
                  ▲
                </button>
                <button
                  onClick={() => movePage(i, 'down')}
                  disabled={i === (selectedChannel.pages?.length || 0) - 1}
                  className="w-8 h-8 flex items-center justify-center rounded bg-gray-100 hover:bg-gray-200 disabled:opacity-30 disabled:hover:bg-gray-100 text-gray-600"
                >
                  ▼
                </button>
              </div>

              {/* Page info */}
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <span>{pageTypeIcon(assignment.page.page_type)}</span>
                  <span className="font-medium text-gray-800">{assignment.page.title}</span>
                  {assignment.page.is_system && (
                    <span className="text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded">System</span>
                  )}
                  {!assignment.page.is_published && (
                    <span className="text-xs bg-yellow-100 text-yellow-700 px-2 py-0.5 rounded">Draft</span>
                  )}
                </div>
                <p className="text-xs text-gray-400 mt-1">
                  {assignment.page.page_type.replace(/_/g, ' ')}
                  {assignment.duration_override ? ` · ${assignment.duration_override}s` : ''}
                </p>
              </div>

              {/* Enable/disable toggle */}
              <button
                onClick={() => togglePage(i)}
                className={`w-12 h-7 rounded-full transition-colors relative ${
                  assignment.is_enabled ? 'bg-green-500' : 'bg-gray-300'
                }`}
              >
                <div
                  className={`w-5 h-5 bg-white rounded-full absolute top-1 transition-transform ${
                    assignment.is_enabled ? 'translate-x-6' : 'translate-x-1'
                  }`}
                />
              </button>

              {/* Remove */}
              <button
                onClick={() => removePage(assignment.page_id)}
                className="text-sm text-red-600 hover:underline ml-1"
                title="Remove from channel"
              >
                ✕
              </button>
            </div>
          ))}

          {(!selectedChannel.pages || selectedChannel.pages.length === 0) && (
            <div className="p-8 text-center text-gray-400">
              No pages assigned to this channel yet
            </div>
          )}
        </div>
      </div>
    );
  }

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-800 mb-6">Channels</h1>

      <div className="space-y-3">
        {channels.map((ch) => (
          <button
            key={ch.id}
            onClick={() => loadChannelDetail(ch.id)}
            className="w-full text-left bg-white rounded-xl shadow-sm border border-gray-200 p-5 hover:border-gray-300 transition-colors"
          >
            <div className="flex items-center justify-between">
              <div>
                <h3 className="font-semibold text-gray-800 text-lg">{ch.name}</h3>
                <p className="text-sm text-gray-400 mt-1">
                  {ch.page_count} pages &middot; {ch.rotation_interval}s &middot; /display/{ch.slug}
                </p>
              </div>
              <span className="text-gray-300 text-xl">→</span>
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}

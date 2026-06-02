import { useState, useEffect } from 'react';

interface PageData {
  id: number;
  title: string;
  page_type: string;
  is_system: boolean;
  is_published: boolean;
  announcement?: {
    body_text: string;
    priority: string;
    starts_at: string | null;
    expires_at: string | null;
  };
}

export default function PageManager() {
  const [pages, setPages] = useState<PageData[]>([]);
  const [showCreate, setShowCreate] = useState(false);
  const [newTitle, setNewTitle] = useState('');
  const [newBody, setNewBody] = useState('');
  const [newPriority, setNewPriority] = useState('normal');
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editTitle, setEditTitle] = useState('');
  const [editBody, setEditBody] = useState('');
  const [editPriority, setEditPriority] = useState('normal');
  const [saving, setSaving] = useState(false);
  const token = localStorage.getItem('exhibitos_token');

  useEffect(() => {
    loadPages();
  }, []);

  const loadPages = async () => {
    const resp = await fetch('/api/pages', {
      headers: { Authorization: `Bearer ${token}` },
    });
    setPages(await resp.json());
  };

  const createAnnouncement = async () => {
    if (!newTitle.trim()) return;
    setSaving(true);
    try {
      await fetch('/api/pages/announcement', {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          title: newTitle,
          body_text: newBody,
          priority: newPriority,
        }),
      });
      setNewTitle('');
      setNewBody('');
      setNewPriority('normal');
      setShowCreate(false);
      loadPages();
    } finally {
      setSaving(false);
    }
  };

  const startEdit = (page: PageData) => {
    setEditingId(page.id);
    setEditTitle(page.title);
    setEditBody(page.announcement?.body_text ?? '');
    setEditPriority(page.announcement?.priority ?? 'normal');
    setShowCreate(false);
  };

  const cancelEdit = () => {
    setEditingId(null);
  };

  const saveEdit = async () => {
    if (editingId === null || !editTitle.trim()) return;
    setSaving(true);
    try {
      await fetch(`/api/pages/${editingId}`, {
        method: 'PUT',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ title: editTitle }),
      });
      await fetch(`/api/pages/${editingId}/announcement`, {
        method: 'PUT',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          body_text: editBody,
          priority: editPriority,
        }),
      });
      setEditingId(null);
      loadPages();
    } finally {
      setSaving(false);
    }
  };

  const togglePublish = async (page: PageData) => {
    await fetch(`/api/pages/${page.id}`, {
      method: 'PUT',
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ is_published: !page.is_published }),
    });
    loadPages();
  };

  const deletePage = async (page: PageData) => {
    if (!confirm(`Delete "${page.title}"?`)) return;
    await fetch(`/api/pages/${page.id}`, {
      method: 'DELETE',
      headers: { Authorization: `Bearer ${token}` },
    });
    loadPages();
  };

  const pageTypeIcon = (type: string) => {
    switch (type) {
      case 'announcement': return '📢';
      default: return '📄';
    }
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-800">Pages</h1>
        <button
          onClick={() => setShowCreate(true)}
          className="px-4 py-2 bg-[#0B1F3A] text-white rounded-lg text-sm font-medium hover:bg-[#132B50] transition-colors"
        >
          + New Announcement
        </button>
      </div>

      {/* Create announcement form */}
      {showCreate && (
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 mb-6">
          <h2 className="font-semibold text-gray-700 mb-4">New Announcement</h2>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Title</label>
              <input
                type="text"
                value={newTitle}
                onChange={(e) => setNewTitle(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#0B1F3A]"
                placeholder="e.g., Pool Opens May 15"
                maxLength={200}
                autoFocus
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Body Text <span className="text-gray-400">({300 - newBody.length} chars remaining)</span>
              </label>
              <textarea
                value={newBody}
                onChange={(e) => setNewBody(e.target.value.slice(0, 300))}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#0B1F3A] h-24 resize-none"
                placeholder="Announcement details..."
                maxLength={300}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Priority</label>
              <select
                value={newPriority}
                onChange={(e) => setNewPriority(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#0B1F3A]"
              >
                <option value="normal">Normal</option>
                <option value="urgent">Urgent</option>
              </select>
            </div>
            <div className="flex gap-3 pt-2">
              <button
                onClick={createAnnouncement}
                disabled={saving || !newTitle.trim()}
                className="px-4 py-2 bg-[#0B1F3A] text-white rounded-lg text-sm font-medium hover:bg-[#132B50] disabled:opacity-50"
              >
                {saving ? 'Creating...' : 'Create (Draft)'}
              </button>
              <button
                onClick={() => setShowCreate(false)}
                className="px-4 py-2 text-gray-500 hover:text-gray-700 text-sm"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Page list */}
      <div className="space-y-2">
        {pages.map((page) => (
          editingId === page.id ? (
            <div
              key={page.id}
              className="bg-white rounded-xl shadow-sm border border-[#0B1F3A] border-2 p-6"
            >
              <h2 className="font-semibold text-gray-700 mb-4">Edit Announcement</h2>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Title</label>
                  <input
                    type="text"
                    value={editTitle}
                    onChange={(e) => setEditTitle(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#0B1F3A]"
                    maxLength={200}
                    autoFocus
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Body Text <span className="text-gray-400">({300 - editBody.length} chars remaining)</span>
                  </label>
                  <textarea
                    value={editBody}
                    onChange={(e) => setEditBody(e.target.value.slice(0, 300))}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#0B1F3A] h-24 resize-none"
                    maxLength={300}
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Priority</label>
                  <select
                    value={editPriority}
                    onChange={(e) => setEditPriority(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#0B1F3A]"
                  >
                    <option value="normal">Normal</option>
                    <option value="urgent">Urgent</option>
                  </select>
                </div>
                <div className="flex gap-3 pt-2">
                  <button
                    onClick={saveEdit}
                    disabled={saving || !editTitle.trim()}
                    className="px-4 py-2 bg-[#0B1F3A] text-white rounded-lg text-sm font-medium hover:bg-[#132B50] disabled:opacity-50"
                  >
                    {saving ? 'Saving...' : 'Save'}
                  </button>
                  <button
                    onClick={cancelEdit}
                    className="px-4 py-2 text-gray-500 hover:text-gray-700 text-sm"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            </div>
          ) : (
            <div
              key={page.id}
              className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 flex items-center gap-4"
            >
              <span className="text-xl">{pageTypeIcon(page.page_type)}</span>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="font-medium text-gray-800 truncate">{page.title}</span>
                  {page.is_system && (
                    <span className="text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded shrink-0">System</span>
                  )}
                </div>
                <p className="text-xs text-gray-400 mt-1">
                  {page.page_type.replace(/_/g, ' ')}
                  {page.announcement ? ` · ${page.announcement.body_text.slice(0, 60)}...` : ''}
                </p>
              </div>
              <div className="flex items-center gap-2 shrink-0">
                {page.page_type === 'announcement' && (
                  <button
                    onClick={() => startEdit(page)}
                    className="text-xs px-3 py-1 rounded-full font-medium bg-gray-100 text-gray-700 hover:bg-gray-200"
                  >
                    Edit
                  </button>
                )}
                <button
                  onClick={() => togglePublish(page)}
                  className={`text-xs px-3 py-1 rounded-full font-medium ${
                    page.is_published
                      ? 'bg-green-100 text-green-700'
                      : 'bg-yellow-100 text-yellow-700'
                  }`}
                >
                  {page.is_published ? 'Published' : 'Draft'}
                </button>
                {!page.is_system && (
                  <button
                    onClick={() => deletePage(page)}
                    className="text-gray-400 hover:text-red-500 text-sm"
                  >
                    ✕
                  </button>
                )}
              </div>
            </div>
          )
        ))}
      </div>
    </div>
  );
}

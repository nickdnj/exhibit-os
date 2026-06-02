import { useState, useEffect } from 'react';

interface ExhibitSummary {
  slug: string;
  title: string;
  year_introduced: number | null;
  source_ref: string;
  has_hero: boolean;
  has_video: boolean;
}

interface IngestCounts {
  created: number;
  updated: number;
  unchanged: number;
  total: number;
}

export default function ExhibitManager() {
  const [exhibits, setExhibits] = useState<ExhibitSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [ingesting, setIngesting] = useState(false);
  const [result, setResult] = useState<IngestCounts | null>(null);
  const [error, setError] = useState<string | null>(null);
  const token = localStorage.getItem('exhibitos_token');

  const loadExhibits = async () => {
    setLoading(true);
    try {
      const resp = await fetch('/api/exhibits');
      if (!resp.ok) throw new Error('Failed to load exhibits');
      setExhibits(await resp.json());
      setError(null);
    } catch {
      setError('Could not load exhibits.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadExhibits();
  }, []);

  const reingest = async () => {
    setIngesting(true);
    setResult(null);
    setError(null);
    try {
      const resp = await fetch('/api/exhibits/ingest', {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!resp.ok) throw new Error('Re-ingest failed');
      setResult(await resp.json());
      await loadExhibits();
    } catch {
      setError('Re-ingest failed. Check that you are logged in and the wiki export is available.');
    } finally {
      setIngesting(false);
    }
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-800">Exhibits</h1>
        <button
          onClick={reingest}
          disabled={ingesting}
          className="px-4 py-2 bg-[#0B1F3A] text-white rounded-lg text-sm font-medium hover:bg-[#132B50] disabled:opacity-50 transition-colors"
        >
          {ingesting ? 'Re-ingesting…' : 'Re-ingest from wiki'}
        </button>
      </div>

      {/* Read-only / source-of-truth banner */}
      <div className="bg-amber-50 border border-amber-200 text-amber-900 rounded-xl px-4 py-3 mb-6 text-sm">
        Exhibit text is authored in the docent wiki — read-only here. Use{' '}
        <strong>Re-ingest</strong> to pull the latest.
      </div>

      {result && (
        <div className="bg-green-50 border border-green-200 text-green-900 rounded-xl px-4 py-3 mb-6 text-sm">
          Ingest complete: {result.created} created, {result.updated} updated,{' '}
          {result.unchanged} unchanged ({result.total} total).
        </div>
      )}

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-800 rounded-xl px-4 py-3 mb-6 text-sm">
          {error}
        </div>
      )}

      {loading ? (
        <p className="text-gray-400 text-sm">Loading exhibits…</p>
      ) : exhibits.length === 0 ? (
        <p className="text-gray-500 text-sm">
          No exhibits yet. Use “Re-ingest from wiki” to pull content from the docent wiki.
        </p>
      ) : (
        <div className="space-y-2">
          {exhibits.map((ex) => (
            <a
              key={ex.slug}
              href={`/exhibit/${ex.slug}`}
              target="_blank"
              rel="noopener noreferrer"
              className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 flex items-center gap-4 hover:border-[#0B1F3A] transition-colors"
            >
              <span className="text-xl">🏛️</span>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="font-medium text-gray-800 truncate">{ex.title}</span>
                  {ex.year_introduced != null && (
                    <span className="text-xs text-gray-400 font-mono shrink-0">
                      {ex.year_introduced}
                    </span>
                  )}
                </div>
                <p className="text-xs text-gray-400 mt-1 truncate">{ex.source_ref}</p>
              </div>
              <span className="text-gray-300 text-sm shrink-0">↗</span>
            </a>
          ))}
        </div>
      )}
    </div>
  );
}

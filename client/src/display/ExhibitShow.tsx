import { useState, useEffect } from 'react';
import ExhibitCard from './ExhibitCard';

interface ExhibitSummary {
  slug: string;
  title: string;
  year_introduced: number | null;
}

const ROTATE_MS = 14000;

/**
 * Auto-rotating kiosk "show" of the museum's exhibits, in chronological order.
 * Leads with the real collection (ENIAC, the minicomputers, the micros…),
 * not any one featured item. Reuses ExhibitCard for the per-exhibit layout.
 */
export default function ExhibitShow() {
  const [exhibits, setExhibits] = useState<ExhibitSummary[]>([]);
  const [index, setIndex] = useState(0);

  useEffect(() => {
    let cancelled = false;
    fetch('/api/exhibits')
      .then((r) => (r.ok ? r.json() : []))
      .then((data: ExhibitSummary[]) => {
        if (cancelled) return;
        // The API returns exhibits in the docent wiki's approximate-chronological
        // source order — use it as-is for the tour.
        setExhibits(Array.isArray(data) ? data : []);
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (exhibits.length === 0) return;
    const t = setInterval(() => {
      setIndex((i) => (i + 1) % exhibits.length);
    }, ROTATE_MS);
    return () => clearInterval(t);
  }, [exhibits.length]);

  if (exhibits.length === 0) {
    return (
      <div
        className="min-h-screen w-full flex items-center justify-center"
        style={{ backgroundColor: 'var(--brand-navy)' }}
      >
        <p className="text-white/60 text-2xl">No exhibits to display yet.</p>
      </div>
    );
  }

  const current = exhibits[index];

  return (
    <div className="relative min-h-screen w-full" style={{ backgroundColor: 'var(--brand-navy)' }}>
      <ExhibitCard slug={current.slug} />
      {/* Progress indicator */}
      <div className="fixed bottom-5 left-0 right-0 flex items-center justify-center gap-3">
        <span className="text-white/40 text-sm font-mono">
          {index + 1} / {exhibits.length}
        </span>
      </div>
    </div>
  );
}

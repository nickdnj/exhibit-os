import { useState, useEffect } from 'react';
import { fetchFishing } from '../api';
import type { FishingReport, FishingLocationReport, FishingWindow } from '../api';

function formatTime(t: string | null | undefined): string {
  if (!t) return '--';
  const [hh, mm] = t.split(':');
  const h = parseInt(hh, 10);
  const ampm = h >= 12 ? 'PM' : 'AM';
  const h12 = h % 12 === 0 ? 12 : h % 12;
  return `${h12}:${mm} ${ampm}`;
}

function stars(n: number): string {
  return '★'.repeat(Math.max(0, Math.min(5, n))) + '☆'.repeat(5 - Math.max(0, Math.min(5, n)));
}

function moonIcon(phase: string): string {
  if (phase.includes('New')) return '🌑';
  if (phase.includes('Waxing Crescent')) return '🌒';
  if (phase.includes('Waxing Gibbous')) return '🌔';
  if (phase.includes('Full')) return '🌕';
  if (phase.includes('Waning Gibbous')) return '🌖';
  if (phase.includes('Waning Crescent')) return '🌘';
  if (phase.includes('First')) return '🌓';
  if (phase.includes('Last')) return '🌗';
  return '🌙';
}

export default function FishingPage() {
  const [report, setReport] = useState<FishingReport | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      try {
        setReport(await fetchFishing());
        setError(null);
      } catch {
        setError('Fishing report unavailable');
      }
    };
    load();
    const interval = setInterval(load, 15 * 60 * 1000);
    return () => clearInterval(interval);
  }, []);

  if (error) {
    return (
      <div className="h-full flex items-center justify-center">
        <p className="text-[48px]" style={{ color: 'var(--status-yellow)' }}>{error}</p>
      </div>
    );
  }

  if (!report || report.locations.length === 0) {
    return (
      <div className="h-full flex items-center justify-center">
        <p className="text-white/50 text-[40px]">Loading fishing report...</p>
      </div>
    );
  }

  const local = report.locations.find((l) => l.is_local) || report.locations[0];
  const others = report.locations.filter((l) => l.id !== local.id);

  return (
    <div className="h-full flex flex-col items-center px-8 py-3">
      <p className="text-[22px] uppercase tracking-[0.1em]" style={{ color: 'var(--brand-gold)' }}>
        Fishing Report · {moonIcon(local.moon.phase_name)} {local.moon.phase_name}
      </p>

      <FeaturedLocation loc={local} />

      {others.length > 0 && (
        <div className="w-full max-w-[1600px] mt-4 grid gap-3"
          style={{ gridTemplateColumns: `repeat(${Math.min(others.length, 3)}, minmax(0, 1fr))` }}>
          {others.map((loc) => <SecondaryLocation key={loc.id} loc={loc} />)}
        </div>
      )}
    </div>
  );
}

function FeaturedLocation({ loc }: { loc: FishingLocationReport }) {
  return (
    <div className="w-full max-w-[1600px] mt-2">
      <div className="flex items-baseline justify-between mb-2">
        <p className="text-white text-[40px] font-bold">
          {loc.name}
          {loc.is_local && <span style={{ color: 'var(--brand-gold)' }} className="text-[22px] ml-3">⚓ Local</span>}
        </p>
        <p className="text-[36px]" style={{ color: 'var(--brand-gold)' }}>{stars(loc.overall_rating)}</p>
      </div>

      {/* Best windows — the hero */}
      <div className="grid gap-3" style={{ gridTemplateColumns: `repeat(${Math.min(loc.best_windows.length || 1, 3)}, minmax(0, 1fr))` }}>
        {loc.best_windows.slice(0, 3).map((w, i) => <WindowCard key={i} w={w} big />)}
        {loc.best_windows.length === 0 && (
          <div className="rounded-xl p-5 text-center" style={{ backgroundColor: 'var(--brand-navy-mid)' }}>
            <p className="text-white/50 text-[28px]">No prime windows today</p>
          </div>
        )}
      </div>

      {/* Sun / moon / tide summary strip — solunar inputs */}
      <div className="mt-3 rounded-xl p-4 flex items-center justify-around"
        style={{ backgroundColor: 'var(--brand-navy-mid)' }}>
        <SummaryItem label="☀ Sunrise" value={formatTime(loc.sun.sunrise)} />
        <SummaryItem label="☀ Sunset" value={formatTime(loc.sun.sunset)} />
        <SummaryItem label="🌙 Moonrise" value={formatTime(loc.moon.rise)} />
        <SummaryItem label="🌙 Moonset" value={formatTime(loc.moon.set)} />
        <SummaryItem label="Illum" value={`${loc.moon.illumination_pct}%`} />
      </div>

      {/* Tide strip */}
      <div className="mt-3 flex gap-2 justify-center flex-wrap">
        {loc.tides.map((t, i) => (
          <div key={i} className="rounded-lg px-5 py-3 text-[26px]"
            style={{ backgroundColor: t.type === 'High' ? 'var(--brand-navy-mid)' : 'var(--brand-navy)',
              border: t.type === 'High' ? '2px solid var(--brand-gold)' : '1px solid rgba(255,255,255,0.15)' }}>
            <span style={{ color: t.type === 'High' ? 'var(--brand-gold)' : 'var(--brand-white)', opacity: t.type === 'High' ? 1 : 0.6 }}>
              {t.type === 'High' ? '▲' : '▼'} {t.type}
            </span>
            <span className="text-white ml-2 font-bold">{formatTime(t.time)}</span>
            <span className="text-white/60 ml-2 text-[22px]">{t.height_ft}ft</span>
          </div>
        ))}
      </div>

      {/* Solunar methodology legend */}
      <p className="text-center text-[18px] text-white/40 mt-3 italic">
        Solunar: best bite when dawn/dusk · moon rise/set/overhead · and tide turns align.
        New &amp; full moon boost the day.
      </p>
    </div>
  );
}

function WindowCard({ w, big }: { w: FishingWindow; big?: boolean }) {
  const titleSize = big ? '42px' : '28px';
  const reasonSize = big ? '20px' : '16px';
  return (
    <div className="rounded-xl p-4 text-center" style={{
      backgroundColor: 'var(--brand-navy-mid)',
      borderLeft: `6px solid ${w.rating >= 5 ? 'var(--brand-gold)' : w.rating >= 4 ? 'var(--brand-gold-light)' : 'rgba(255,255,255,0.3)'}`,
    }}>
      <p style={{ color: 'var(--brand-gold)', fontSize: big ? '24px' : '18px' }}>{stars(w.rating)}</p>
      <p className="text-white font-bold mt-1" style={{ fontSize: titleSize, lineHeight: 1.1 }}>
        {formatTime(w.start)} – {formatTime(w.end)}
      </p>
      <p className="text-white/60 mt-1" style={{ fontSize: reasonSize, textTransform: 'capitalize' }}>
        {w.reasons.slice(0, 3).join(' · ')}
      </p>
    </div>
  );
}

function SummaryItem({ label, value }: { label: string; value: string }) {
  return (
    <div className="text-center">
      <p className="uppercase tracking-wider text-[20px]" style={{ color: 'var(--brand-gold)' }}>{label}</p>
      <p className="text-white font-bold text-[34px] leading-tight">{value}</p>
    </div>
  );
}

function SecondaryLocation({ loc }: { loc: FishingLocationReport }) {
  const top = loc.best_windows[0];
  return (
    <div className="rounded-xl p-3" style={{ backgroundColor: 'var(--brand-navy-mid)' }}>
      <div className="flex items-baseline justify-between mb-1">
        <p className="text-white text-[24px] font-bold">{loc.name}</p>
        <p className="text-[20px]" style={{ color: 'var(--brand-gold)' }}>{stars(loc.overall_rating)}</p>
      </div>
      {top ? (
        <>
          <p className="text-white text-[26px] font-bold">
            {formatTime(top.start)} – {formatTime(top.end)}
          </p>
          <p className="text-white/60 text-[16px] capitalize">{top.reasons.slice(0, 2).join(' · ')}</p>
        </>
      ) : (
        <p className="text-white/50 text-[18px]">No prime window</p>
      )}
    </div>
  );
}

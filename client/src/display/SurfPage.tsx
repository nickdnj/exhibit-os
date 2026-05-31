import { useState, useEffect } from 'react';
import { fetchSurf } from '../api';
import type { SurfReport, SurfSpotReport, SurfHour } from '../api';

function formatHour(t: string): string {
  const [hh] = t.split(':');
  const h = parseInt(hh, 10);
  const ampm = h >= 12 ? 'PM' : 'AM';
  const h12 = h % 12 === 0 ? 12 : h % 12;
  return `${h12}${ampm.toLowerCase()}`;
}

function stars(n: number): string {
  return '★'.repeat(Math.max(0, Math.min(5, n))) + '☆'.repeat(5 - Math.max(0, Math.min(5, n)));
}

function windColor(rel: string): string {
  if (rel === 'offshore') return 'var(--brand-gold)';
  if (rel === 'side-offshore') return 'var(--brand-gold-light)';
  if (rel === 'onshore') return 'var(--status-red)';
  if (rel === 'side-onshore') return 'var(--status-yellow)';
  return 'var(--brand-white)';
}

export default function SurfPage() {
  const [report, setReport] = useState<SurfReport | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      try {
        setReport(await fetchSurf());
        setError(null);
      } catch {
        setError('Surf report unavailable');
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

  if (!report || report.spots.length === 0) {
    return (
      <div className="h-full flex items-center justify-center">
        <p className="text-white/50 text-[40px]">Loading surf report...</p>
      </div>
    );
  }

  const local = report.spots.find((s) => s.is_local && s.status === 'available') || report.spots[0];
  const others = report.spots.filter((s) => s.id !== local.id);

  return (
    <div className="h-full flex flex-col items-center px-8 py-3">
      <p className="text-[22px] uppercase tracking-[0.1em]" style={{ color: 'var(--brand-gold)' }}>
        🏄 Surf Report
      </p>

      <FeaturedSpot spot={local} />

      {others.length > 0 && (
        <div className="w-full max-w-[1600px] mt-4 grid gap-3"
          style={{ gridTemplateColumns: `repeat(${Math.min(others.length, 3)}, minmax(0, 1fr))` }}>
          {others.map((s) => <SecondarySpot key={s.id} spot={s} />)}
        </div>
      )}
    </div>
  );
}

function FeaturedSpot({ spot }: { spot: SurfSpotReport }) {
  if (spot.status !== 'available') {
    return (
      <div className="text-center py-10">
        <p className="text-white text-[48px] font-bold">{spot.name}</p>
        <p className="text-[32px] mt-2" style={{ color: 'var(--status-yellow)' }}>{spot.error || 'Data unavailable'}</p>
      </div>
    );
  }

  return (
    <div className="w-full max-w-[1600px] mt-2">
      <div className="flex items-baseline justify-between mb-3">
        <p className="text-white text-[40px] font-bold">
          {spot.name}
          {spot.is_local && <span style={{ color: 'var(--brand-gold)' }} className="text-[22px] ml-3">⚓ Local</span>}
        </p>
        <div className="text-right">
          <p className="text-[36px]" style={{ color: 'var(--brand-gold)' }}>{stars(spot.rating)}</p>
          <p className="text-white text-[28px] -mt-1">{spot.label}</p>
        </div>
      </div>

      {/* Hero reading */}
      <div className="rounded-xl p-5 flex items-center justify-around gap-4"
        style={{ backgroundColor: 'var(--brand-navy-mid)' }}>
        <MetricBig label="Wave Height" value={`${spot.wave_height_ft ?? '--'} ft`} />
        <MetricBig label="Period" value={`${spot.wave_period_s ?? '--'} s`} />
        <MetricBig label="From" value={spot.wave_direction_compass ?? '--'} />
        <MetricBig
          label={`Wind ${spot.wind.speed_mph ?? '--'} mph`}
          value={spot.wind.direction_compass ?? '--'}
          valueColor={windColor(spot.wind.relationship)}
          sublabel={spot.wind.relationship.replace('-', ' ')}
        />
      </div>

      {/* 12h outlook */}
      {spot.hourly.length > 0 && (
        <div className="mt-4">
          <p className="text-[20px] uppercase tracking-wider mb-2" style={{ color: 'var(--brand-gold)' }}>
            Next 12 hours
          </p>
          <div className="grid gap-2" style={{ gridTemplateColumns: `repeat(${Math.min(spot.hourly.length, 12)}, minmax(0, 1fr))` }}>
            {spot.hourly.slice(0, 12).map((h, i) => <HourCell key={i} h={h} />)}
          </div>
        </div>
      )}
    </div>
  );
}

function HourCell({ h }: { h: SurfHour }) {
  const height = h.wave_height_ft ?? 0;
  const barHeight = Math.min(100, height * 20); // 5ft = full bar
  return (
    <div className="rounded-lg p-2 text-center" style={{ backgroundColor: 'var(--brand-navy-mid)' }}>
      <p className="text-white/60 text-[16px]">{formatHour(h.time)}</p>
      <div className="h-12 flex items-end justify-center my-1">
        <div className="w-4 rounded-t"
          style={{ height: `${barHeight}%`, backgroundColor: 'var(--brand-gold)' }} />
      </div>
      <p className="text-white text-[20px] font-bold">{h.wave_height_ft ?? '--'}<span className="text-[14px] text-white/60">ft</span></p>
      <p className="text-white/50 text-[14px]">{h.wave_period_s ?? '--'}s</p>
    </div>
  );
}

function MetricBig({ label, value, valueColor, sublabel }: { label: string; value: string; valueColor?: string; sublabel?: string }) {
  return (
    <div className="text-center">
      <p className="uppercase tracking-wider text-[20px]" style={{ color: 'var(--brand-gold)' }}>{label}</p>
      <p className="font-bold text-[48px]" style={{ color: valueColor || 'white' }}>{value}</p>
      {sublabel && <p className="text-white/50 text-[18px] capitalize">{sublabel}</p>}
    </div>
  );
}

function SecondarySpot({ spot }: { spot: SurfSpotReport }) {
  if (spot.status !== 'available') {
    return (
      <div className="rounded-xl p-4 text-center" style={{ backgroundColor: 'var(--brand-navy-mid)' }}>
        <p className="text-white text-[24px] font-bold">{spot.name}</p>
        <p className="text-[22px] mt-2" style={{ color: 'var(--status-yellow)' }}>Unavailable</p>
      </div>
    );
  }

  return (
    <div className="rounded-xl p-3" style={{ backgroundColor: 'var(--brand-navy-mid)' }}>
      <div className="flex items-baseline justify-between mb-1">
        <p className="text-white text-[24px] font-bold">{spot.name}</p>
        <p className="text-[18px]" style={{ color: 'var(--brand-gold)' }}>{stars(spot.rating)}</p>
      </div>
      <p className="text-white text-[32px] font-bold">
        {spot.wave_height_ft}<span className="text-[18px] text-white/60">ft</span>
        <span className="text-[18px] text-white/60 ml-2">@ {spot.wave_period_s}s</span>
      </p>
      <p className="text-[16px]" style={{ color: windColor(spot.wind.relationship) }}>
        {spot.wind.speed_mph ?? '--'}mph {spot.wind.direction_compass ?? ''} · {spot.wind.relationship.replace('-', ' ')}
      </p>
    </div>
  );
}

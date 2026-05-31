import { useState, useEffect } from 'react';
import { fetchTides } from '../api';
import type { TideState, TideStationState } from '../api';

function formatTime(t: string | null | undefined): string {
  if (!t) return '--';
  const [hh, mm] = t.split(':');
  const h = parseInt(hh, 10);
  const ampm = h >= 12 ? 'PM' : 'AM';
  const h12 = h % 12 === 0 ? 12 : h % 12;
  return `${h12}:${mm} ${ampm}`;
}

function tideArrow(direction: string): string {
  if (direction === 'rising') return '▲';
  if (direction === 'falling') return '▼';
  return '•';
}

export default function TidePage() {
  const [tides, setTides] = useState<TideState | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      try {
        setTides(await fetchTides());
        setError(null);
      } catch {
        setError('Tide data unavailable');
      }
    };
    load();
    const interval = setInterval(load, 15 * 60 * 1000);
    return () => clearInterval(interval);
  }, []);

  if (error) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-center">
          <p className="text-[48px]" style={{ color: 'var(--status-yellow)' }}>Tides Unavailable</p>
          <p className="text-white/50 text-[32px] mt-4">Retrying...</p>
        </div>
      </div>
    );
  }

  if (!tides || tides.stations.length === 0) {
    return (
      <div className="h-full flex items-center justify-center">
        <p className="text-white/50 text-[40px]">Loading tides...</p>
      </div>
    );
  }

  const local = tides.stations.find((s) => s.is_local && s.status === 'available') || tides.stations[0];
  const others = tides.stations.filter((s) => s.noaa_id !== local.noaa_id);

  return (
    <div className="h-full flex flex-col items-center justify-center px-8 py-4">
      <p className="text-[24px] uppercase tracking-[0.1em] mb-2" style={{ color: 'var(--brand-gold)' }}>
        Tides
      </p>

      <FeaturedStation station={local} />

      {others.length > 0 && (
        <div className="w-full max-w-[1400px] mt-6">
          <div className="grid gap-3" style={{ gridTemplateColumns: `repeat(${Math.min(others.length, 3)}, minmax(0, 1fr))` }}>
            {others.map((s) => <SecondaryStation key={s.noaa_id} station={s} />)}
          </div>
        </div>
      )}
    </div>
  );
}

function FeaturedStation({ station }: { station: TideStationState }) {
  if (station.status !== 'available' || !station.next_tide) {
    return (
      <div className="text-center py-6">
        <p className="text-white text-[48px] font-bold">{station.name}</p>
        <p className="text-[32px] mt-2" style={{ color: 'var(--status-yellow)' }}>Data unavailable</p>
      </div>
    );
  }

  const today = new Date().toISOString().split('T')[0];
  const todayEvents = station.predictions.filter((p) => p.date === today);

  return (
    <div className="text-center w-full max-w-[1400px]">
      <p className="text-white text-[40px] font-bold mb-3">
        {station.name} {station.is_local && <span style={{ color: 'var(--brand-gold)' }} className="text-[28px]">⚓ Local</span>}
      </p>

      <div className="mb-4">
        <p className="text-white font-black" style={{ fontSize: '88px', lineHeight: 1 }}>
          <span style={{ color: 'var(--brand-gold)' }}>{tideArrow(station.direction)}</span>{' '}
          {station.next_tide.type} at {formatTime(station.next_tide.time)}
        </p>
        <p className="text-[28px] mt-2" style={{ color: 'var(--brand-gold-light)' }}>
          {station.direction === 'rising' ? 'Rising' : station.direction === 'falling' ? 'Falling' : '—'}
          {' · '}
          {station.next_tide.height_ft} ft
        </p>
      </div>

      {todayEvents.length > 0 && (
        <div className="grid gap-3" style={{ gridTemplateColumns: `repeat(${Math.min(todayEvents.length, 4)}, minmax(0, 1fr))` }}>
          {todayEvents.slice(0, 4).map((p, i) => (
            <div key={i} className="rounded-xl p-4" style={{ backgroundColor: 'var(--brand-navy-mid)' }}>
              <p className="text-[22px] uppercase tracking-wider" style={{ color: p.type === 'High' ? 'var(--brand-gold)' : 'var(--brand-white)', opacity: p.type === 'High' ? 1 : 0.6 }}>
                {p.type}
              </p>
              <p className="text-white text-[36px] font-bold mt-1">{formatTime(p.time)}</p>
              <p className="text-white/50 text-[24px]">{p.height_ft} ft</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function SecondaryStation({ station }: { station: TideStationState }) {
  const bg = 'var(--brand-navy-mid)';
  if (station.status !== 'available' || !station.next_tide) {
    return (
      <div className="rounded-xl p-4 text-center" style={{ backgroundColor: bg }}>
        <p className="text-white text-[24px] font-bold">{station.name}</p>
        <p className="text-[22px] mt-2" style={{ color: 'var(--status-yellow)' }}>Unavailable</p>
      </div>
    );
  }

  return (
    <div className="rounded-xl p-4" style={{ backgroundColor: bg }}>
      <p className="text-white text-[24px] font-bold mb-2">{station.name}</p>
      <p className="text-white text-[36px] font-black">
        <span style={{ color: 'var(--brand-gold)' }}>{tideArrow(station.direction)}</span> {station.next_tide.type}
      </p>
      <p className="text-white text-[28px]">{formatTime(station.next_tide.time)}</p>
      <p className="text-white/60 text-[22px] mt-1">{station.next_tide.height_ft} ft</p>
    </div>
  );
}

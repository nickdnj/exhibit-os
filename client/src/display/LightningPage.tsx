import { useEffect, useState } from 'react';
import type { LightningState } from '../api';

interface Props {
  state: LightningState;
}

/**
 * Full-bleed pool safety alert screen. Wording mirrors American Red Cross
 * / NWS guidance: when a strike is detected inside the 30/30 threshold,
 * clear the pool and keep it closed for 30 minutes after the last strike.
 */
export default function LightningPage({ state }: Props) {
  const [tick, setTick] = useState(0);
  useEffect(() => {
    const id = setInterval(() => setTick((t) => t + 1), 1000);
    return () => clearInterval(id);
  }, []);

  if (state.state === 'offline') {
    return (
      <div
        className="h-full w-full flex flex-col items-center justify-center px-12 text-center"
        style={{ backgroundColor: '#1f1207', color: '#fff' }}
      >
        <span style={{ fontSize: '140px', lineHeight: 1 }}>⚠️</span>
        <p className="text-white font-black mt-4" style={{ fontSize: '88px' }}>
          SYSTEM OFFLINE
        </p>
        <p className="text-white/90 mt-4" style={{ fontSize: '40px' }}>
          Lightning detection unavailable.
        </p>
        <p className="text-white/80 mt-2" style={{ fontSize: '36px' }}>
          Monitor conditions manually.
        </p>
      </div>
    );
  }

  const active = state.state === 'alert';
  const bg = active ? '#7f1d1d' : '#78350f'; // red-900 for ALERT, amber-900 for COUNTDOWN
  const headline = active ? 'POOL CLOSED' : 'POOL STILL CLOSED';
  const distanceMi = state.nearest_strike_in_alert?.distance_mi ?? state.last_strike?.distance_mi;
  const countdownSec = state.countdown_remaining_seconds ?? 0;
  // Force re-render on tick so countdown counts down smoothly
  void tick;
  const mm = Math.floor(countdownSec / 60).toString().padStart(2, '0');
  const ss = (countdownSec % 60).toString().padStart(2, '0');

  return (
    <div
      className="h-full w-full flex flex-col items-center justify-center px-12 text-center"
      style={{ backgroundColor: bg, color: '#fff' }}
    >
      <span style={{ fontSize: '160px', lineHeight: 1 }}>⚡</span>
      <p className="text-white font-black mt-2" style={{ fontSize: '120px', lineHeight: 1 }}>
        {headline}
      </p>
      <p className="text-white/95 font-bold mt-4" style={{ fontSize: '48px' }}>
        Lightning detected within {state.threshold_mi} miles
        {distanceMi !== undefined ? ` — last strike ${distanceMi} mi away` : ''}
      </p>
      <p className="text-white/90 mt-6" style={{ fontSize: '40px' }}>
        Shelter indoors until the area is clear.
      </p>

      {state.state === 'countdown' && (
        <div className="mt-10">
          <p className="text-white/70 uppercase tracking-widest" style={{ fontSize: '28px' }}>
            All-clear in
          </p>
          <p className="text-white font-black font-mono mt-2" style={{ fontSize: '120px', lineHeight: 1 }}>
            {mm}:{ss}
          </p>
        </div>
      )}

      {state.state === 'alert' && (
        <p className="text-white/70 mt-10" style={{ fontSize: '32px' }}>
          Pool will reopen 30 minutes after the last strike.
        </p>
      )}
    </div>
  );
}

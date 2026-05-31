import { useState, useEffect, useCallback } from 'react';
import { useParams } from 'react-router-dom';
import { fetchChannelDisplay, fetchLightningState } from '../api';
import type { ChannelDisplay, WeatherCurrent, LightningState } from '../api';
import { useWebSocket } from '../hooks/useWebSocket';
import PageCarousel from './PageCarousel';
import LightningPage from './LightningPage';

export default function ChannelDisplayView() {
  const { slug } = useParams<{ slug: string }>();
  const [data, setData] = useState<ChannelDisplay | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [weatherData, setWeatherData] = useState<WeatherCurrent | null>(null);
  const [lightning, setLightning] = useState<LightningState | null>(null);

  const loadPages = useCallback(async () => {
    if (!slug) return;
    try {
      const result = await fetchChannelDisplay(slug);
      setData(result);
      setError(null);
    } catch {
      setError(`Channel "${slug}" not found`);
    }
  }, [slug]);

  // Handle WebSocket messages
  const handleWsMessage = useCallback((msg: Record<string, unknown>) => {
    switch (msg.type) {
      case 'weather_update':
        setWeatherData(msg.payload as WeatherCurrent);
        break;
      case 'page_list_changed':
        loadPages(); // Refetch page list when admin makes changes
        break;
      case 'lightning_state':
        setLightning(msg.payload as LightningState);
        break;
    }
  }, [loadPages]);

  // Connect WebSocket for real-time updates
  const { connected } = useWebSocket({
    url: `/ws/display/${slug}`,
    onMessage: handleWsMessage,
  });

  useEffect(() => {
    loadPages();
    // Still poll every 60s as a fallback if WebSocket is disconnected
    const interval = setInterval(loadPages, 60000);
    return () => clearInterval(interval);
  }, [loadPages]);

  // Polling fallback for lightning state in case WebSocket is disconnected.
  // The WS lightning_state message is the primary channel; this keeps us
  // correct on cold start and when the socket drops.
  useEffect(() => {
    const load = async () => {
      try { setLightning(await fetchLightningState()); } catch { /* ignore */ }
    };
    load();
    const id = setInterval(load, 15000);
    return () => clearInterval(id);
  }, []);

  const shouldInterrupt =
    !!lightning &&
    lightning.enabled &&
    lightning.alert_channels?.includes(slug || '') &&
    (lightning.state === 'alert' || lightning.state === 'countdown' || lightning.state === 'offline');

  if (error) {
    return (
      <div className="h-screen w-screen flex items-center justify-center"
        style={{ backgroundColor: 'var(--brand-navy)' }}>
        <div className="text-center">
          <p className="text-[48px] font-bold" style={{ color: 'var(--status-red)' }}>
            Display Error
          </p>
          <p className="text-white text-[36px] mt-4">{error}</p>
          <p className="text-white/40 text-[28px] mt-8">Retrying every 60 seconds...</p>
        </div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="h-screen w-screen flex items-center justify-center"
        style={{ backgroundColor: 'var(--brand-navy)' }}>
        <div className="text-center">
          <p className="text-[48px] font-bold" style={{ color: 'var(--brand-gold)' }}>⚓</p>
          <p className="text-white text-[36px] mt-4">Connecting to SignBoard...</p>
        </div>
      </div>
    );
  }

  if (shouldInterrupt && lightning) {
    return (
      <div className="h-screen w-screen relative overflow-hidden">
        <LightningPage state={lightning} />
      </div>
    );
  }

  return (
    <PageCarousel
      pages={data.pages}
      defaultDuration={data.channel.rotation_interval}
      channelName={data.channel.name}
      weatherData={weatherData}
      wsConnected={connected}
    />
  );
}

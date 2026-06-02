import { useState, useEffect, useCallback } from 'react';
import { useParams } from 'react-router-dom';
import { fetchChannelDisplay } from '../api';
import type { ChannelDisplay } from '../api';
import { useWebSocket } from '../hooks/useWebSocket';
import PageCarousel from './PageCarousel';

export default function ChannelDisplayView() {
  const { slug } = useParams<{ slug: string }>();
  const [data, setData] = useState<ChannelDisplay | null>(null);
  const [error, setError] = useState<string | null>(null);

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
      case 'page_list_changed':
        loadPages(); // Refetch page list when admin makes changes
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
          <p className="text-white text-[36px] mt-4">Connecting to ExhibitOS...</p>
        </div>
      </div>
    );
  }

  return (
    <PageCarousel
      pages={data.pages}
      defaultDuration={data.channel.rotation_interval}
      channelName={data.channel.name}
      wsConnected={connected}
    />
  );
}

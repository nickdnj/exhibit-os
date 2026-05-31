import { useState, useEffect, useCallback } from 'react';
import type { DisplayPage, WeatherCurrent } from '../api';
import WeatherPage from './WeatherPage';
import AnnouncementPage from './AnnouncementPage';
import TidePage from './TidePage';
import FishingPage from './FishingPage';
import SurfPage from './SurfPage';

interface PageCarouselProps {
  pages: DisplayPage[];
  defaultDuration: number;
  channelName: string;
  weatherData?: WeatherCurrent | null;
  wsConnected?: boolean;
}

export default function PageCarousel({ pages, defaultDuration, channelName, weatherData, wsConnected }: PageCarouselProps) {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [isTransitioning, setIsTransitioning] = useState(false);
  const [currentTime, setCurrentTime] = useState(new Date());

  const activePage = pages[currentIndex];
  const duration = activePage?.duration || defaultDuration;

  const advancePage = useCallback(() => {
    if (pages.length <= 1) return;
    setIsTransitioning(true);
    setTimeout(() => {
      setCurrentIndex((prev) => (prev + 1) % pages.length);
      setIsTransitioning(false);
    }, 500);
  }, [pages.length]);

  useEffect(() => {
    if (pages.length <= 1) return;
    const timer = setInterval(advancePage, duration * 1000);
    return () => clearInterval(timer);
  }, [advancePage, duration, pages.length]);

  // Update clock every minute
  useEffect(() => {
    const timer = setInterval(() => setCurrentTime(new Date()), 60000);
    return () => clearInterval(timer);
  }, []);

  // Reset index if page count changes
  useEffect(() => {
    if (currentIndex >= pages.length) {
      setCurrentIndex(0);
    }
  }, [pages.length, currentIndex]);

  if (pages.length === 0) {
    return (
      <div className="h-screen w-screen flex items-center justify-center" style={{ backgroundColor: 'var(--brand-navy)' }}>
        <div className="text-center">
          <p className="text-white text-[48px] font-bold">Wharfside Manor</p>
          <p className="text-[28px] mt-4" style={{ color: 'var(--brand-gold)' }}>
            {channelName}
          </p>
          <p className="text-white/50 text-[32px] mt-8">No pages configured</p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-screen w-screen relative overflow-hidden" style={{ backgroundColor: 'var(--brand-navy)' }}>
      {/* Header */}
      <div className="absolute top-0 left-0 right-0 h-16 flex items-center justify-between px-8 z-10"
        style={{ backgroundColor: 'var(--brand-navy-mid)' }}>
        <div className="flex items-center gap-4">
          <span className="text-[28px] font-bold" style={{ color: 'var(--brand-gold)' }}>⚓</span>
          <span className="text-white text-[24px] font-semibold tracking-wide">WHARFSIDE MANOR</span>
        </div>
        <div className="flex items-center gap-4">
          {/* Connection indicator */}
          <div className={`w-2 h-2 rounded-full ${wsConnected ? 'bg-green-500' : 'bg-yellow-500'}`}
            title={wsConnected ? 'Connected' : 'Reconnecting...'} />
          <span className="text-white text-[28px] font-mono">
            {currentTime.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' })}
            <span className="mx-3 text-white/40">·</span>
            {currentTime.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })}
          </span>
        </div>
      </div>

      {/* Page Content */}
      <div className={`absolute inset-0 pt-16 pb-12 transition-opacity duration-500 ${isTransitioning ? 'opacity-0' : 'opacity-100'}`}>
        {renderPage(activePage, weatherData)}
      </div>

      {/* Footer */}
      <div className="absolute bottom-0 left-0 right-0 h-12 flex items-center justify-center gap-2 z-10"
        style={{ backgroundColor: 'var(--brand-navy-mid)' }}>
        {pages.map((_, i) => (
          <div
            key={i}
            className={`w-3 h-3 rounded-full transition-all ${i === currentIndex ? 'scale-125' : 'opacity-40'}`}
            style={{ backgroundColor: i === currentIndex ? 'var(--brand-gold)' : 'var(--brand-white)' }}
          />
        ))}
      </div>
    </div>
  );
}

function renderPage(page: DisplayPage, weatherData?: WeatherCurrent | null) {
  switch (page.page_type) {
    case 'weather_current':
      return <WeatherPage pushedData={weatherData} />;
    case 'weather_hourly':
      return <WeatherPage hourly />;
    case 'weather_forecast':
      return <WeatherPage forecast />;
    case 'tide_current':
      return <TidePage />;
    case 'fishing_report':
      return <FishingPage />;
    case 'surf_report':
      return <SurfPage />;
    case 'announcement':
      return <AnnouncementPage page={page} />;
    default:
      return (
        <div className="h-full flex items-center justify-center">
          <p className="text-white text-[48px]">{page.title}</p>
        </div>
      );
  }
}

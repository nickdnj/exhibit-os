import { useState, useEffect } from 'react';
import { fetchWeatherCurrent, fetchWeatherForecast, fetchWeatherHourly } from '../api';
import type { WeatherCurrent, ForecastDay, ForecastHour } from '../api';

interface WeatherPageProps {
  forecast?: boolean;
  hourly?: boolean;
  pushedData?: WeatherCurrent | null;
}

function windDirectionLabel(degrees: number | null): string {
  if (degrees === null) return '--';
  const dirs = ['N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE', 'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW'];
  return dirs[Math.round(degrees / 22.5) % 16];
}

function isNightNow(): boolean {
  const h = new Date().getHours();
  return h < 6 || h >= 19;
}

function weatherIcon(icon: string | null, forceNight?: boolean): string {
  if (!icon) return '🌡️';
  const key = icon.toLowerCase();
  const night = forceNight || key.includes('night') || (!key.includes('day') && isNightNow());

  if (key.includes('thunder')) return '⛈️';
  if (key.includes('snow') || key.includes('flurries') || key.includes('sleet')) return '❄️';
  if (key.includes('rain') || key.includes('drizzle')) {
    return night ? '🌧️' : '🌧️';
  }
  if (key.includes('fog') || key.includes('mist') || key.includes('haze')) return '🌫️';
  if (key.includes('wind')) return '💨';
  if (key.includes('hail')) return '🧊';
  if (key.includes('partly') || key.includes('mostly cloudy')) {
    return night ? '☁️🌙' : '⛅';
  }
  if (key.includes('cloudy') || key.includes('overcast')) return '☁️';
  if (key.includes('clear') || key.includes('sunny') || key.includes('fair')) {
    return night ? '🌙' : '☀️';
  }
  return night ? '🌙' : '🌡️';
}

const WEEKDAY_SHORT = ['SUN', 'MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT'];

function dayLabel(index: number, day_name: string | undefined): string {
  if (index === 0) return 'TODAY';
  if (day_name && day_name.trim()) return day_name.toUpperCase().slice(0, 3);
  const d = new Date();
  d.setDate(d.getDate() + index);
  return WEEKDAY_SHORT[d.getDay()];
}

export default function WeatherPage({ forecast = false, hourly = false, pushedData }: WeatherPageProps) {
  const [current, setCurrent] = useState<WeatherCurrent | null>(null);
  const [forecastData, setForecastData] = useState<ForecastDay[]>([]);
  const [hourlyData, setHourlyData] = useState<ForecastHour[]>([]);
  const [error, setError] = useState<string | null>(null);

  // Use pushed WebSocket data when available (for current weather)
  // Only prefer pushedData if it actually has temperature data
  const isCurrent = !forecast && !hourly;
  const displayWeather = (isCurrent && pushedData && pushedData.temperature_f !== null) ? pushedData : current;

  useEffect(() => {
    const load = async () => {
      try {
        if (hourly) {
          setHourlyData(await fetchWeatherHourly());
        } else if (forecast) {
          setForecastData(await fetchWeatherForecast());
        } else {
          setCurrent(await fetchWeatherCurrent());
        }
        setError(null);
      } catch {
        setError('Weather data unavailable');
      }
    };
    load();
    const interval = setInterval(load, isCurrent ? 300000 : 1800000); // current 5min; hourly/forecast 30min
    return () => clearInterval(interval);
  }, [forecast, hourly, isCurrent]);

  if (error) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-center">
          <p className="text-[48px]" style={{ color: 'var(--status-yellow)' }}>Weather Unavailable</p>
          <p className="text-white/50 text-[32px] mt-4">Retrying...</p>
        </div>
      </div>
    );
  }

  if (hourly) {
    return <HourlyView hours={hourlyData} />;
  }

  if (forecast) {
    return <ForecastView days={forecastData} />;
  }

  return <CurrentView weather={displayWeather ?? null} />;
}

function CurrentView({ weather }: { weather: WeatherCurrent | null }) {
  if (!weather || weather.temperature_f === null) {
    return (
      <div className="h-full flex items-center justify-center">
        <p className="text-white/50 text-[40px]">Loading weather...</p>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col items-center justify-center px-12">
      {/* Hero temperature + icon */}
      <div className="flex items-center justify-center gap-8 mb-6">
        <span style={{ fontSize: '140px', lineHeight: 1 }}>{weatherIcon(weather.icon)}</span>
        <div className="text-left">
          <p className="text-white font-black" style={{ fontSize: '140px', lineHeight: 1 }}>
            {Math.round(weather.temperature_f)}°F
          </p>
          {weather.conditions && (
            <p className="text-white/80 text-[36px] mt-1">{weather.conditions}</p>
          )}
          {weather.feels_like_f !== null && (
            <p className="text-[28px] mt-1" style={{ color: 'var(--brand-gold-light)' }}>
              Feels like {Math.round(weather.feels_like_f)}°F
            </p>
          )}
        </div>
      </div>

      {/* Metrics grid */}
      <div className="grid grid-cols-4 gap-6 w-full max-w-[1200px]">
        <MetricCard label="Humidity" value={weather.humidity !== null ? `${Math.round(weather.humidity)}%` : '--'} />
        <MetricCard label="Wind" value={weather.wind_speed_mph !== null ? `${Math.round(weather.wind_speed_mph)} mph ${windDirectionLabel(weather.wind_direction)}` : '--'} />
        <MetricCard label="UV Index" value={weather.uv_index !== null ? `${weather.uv_index}` : '--'} />
        <MetricCard label="Rain Today" value={weather.rain_today_in !== null ? `${weather.rain_today_in}"` : '--'} />
      </div>

      {/* Last updated */}
      {weather.last_updated && (
        <p className="text-[28px] mt-8" style={{ color: 'var(--brand-white)', opacity: 0.4 }}>
          Updated {new Date(weather.last_updated).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })}
        </p>
      )}
    </div>
  );
}

function MetricCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl p-6 text-center" style={{ backgroundColor: 'var(--brand-navy-mid)' }}>
      <p className="text-[28px] uppercase tracking-wider mb-2" style={{ color: 'var(--brand-gold)' }}>{label}</p>
      <p className="text-white text-[48px] font-bold">{value}</p>
    </div>
  );
}

function hourLabel(isoTime: string, index: number): string {
  const d = new Date(isoTime);
  if (index === 0) return 'NOW';
  return d.toLocaleTimeString('en-US', { hour: 'numeric', hour12: true }).replace(' ', '').toUpperCase();
}

function HourlyView({ hours }: { hours: ForecastHour[] }) {
  if (hours.length === 0) {
    return (
      <div className="h-full flex items-center justify-center">
        <p className="text-white/50 text-[40px]">Loading hourly forecast...</p>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col items-center justify-center px-12">
      <p className="text-white text-[48px] font-bold mb-6">Next 5 Hours</p>
      <div className="grid grid-cols-5 gap-4 w-full max-w-[1400px]">
        {hours.map((hour, i) => {
          const d = new Date(hour.time);
          const forceNight = d.getHours() < 6 || d.getHours() >= 19;
          return (
            <div key={hour.time} className="rounded-xl p-5 text-center" style={{ backgroundColor: 'var(--brand-navy-mid)' }}>
              <p className="text-[32px] uppercase font-bold" style={{ color: 'var(--brand-gold)' }}>
                {hourLabel(hour.time, i)}
              </p>
              <div style={{ fontSize: '80px', lineHeight: 1 }} className="my-2">
                {weatherIcon(hour.icon, forceNight)}
              </div>
              <p className="text-white text-[56px] font-bold leading-none">
                {hour.temp_f !== null ? `${Math.round(hour.temp_f)}°` : '--'}
              </p>
              <p className="text-[24px] mt-3" style={{ color: hour.precip_pct > 50 ? 'var(--status-yellow)' : 'var(--brand-white)', opacity: 0.7 }}>
                💧 {hour.precip_pct}%
              </p>
              <p className="text-[22px] mt-1" style={{ color: 'var(--brand-white)', opacity: 0.7 }}>
                💨 {hour.wind_mph !== null ? `${Math.round(hour.wind_mph)} mph${hour.wind_dir ? ` ${hour.wind_dir}` : ''}` : '--'}
              </p>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function ForecastView({ days }: { days: ForecastDay[] }) {
  if (days.length === 0) {
    return (
      <div className="h-full flex items-center justify-center">
        <p className="text-white/50 text-[40px]">Loading forecast...</p>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col items-center justify-center px-12">
      <p className="text-white text-[48px] font-bold mb-6">5-Day Forecast</p>
      <div className="grid grid-cols-5 gap-4 w-full max-w-[1400px]">
        {days.map((day, i) => (
          <div key={i} className="rounded-xl p-5 text-center" style={{ backgroundColor: 'var(--brand-navy-mid)' }}>
            <p className="text-[32px] uppercase font-bold" style={{ color: 'var(--brand-gold)' }}>
              {dayLabel(i, day.day_name)}
            </p>
            <div style={{ fontSize: '80px', lineHeight: 1 }} className="my-2">
              {weatherIcon(day.icon)}
            </div>
            <p className="text-white text-[48px] font-bold leading-none">{Math.round(day.high_f)}°</p>
            <p className="text-white/50 text-[32px] leading-none mt-1">{Math.round(day.low_f)}°</p>
            <p className="text-[24px] mt-3" style={{ color: day.precip_pct > 50 ? 'var(--status-yellow)' : 'var(--brand-white)', opacity: 0.7 }}>
              💧 {day.precip_pct}%
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}

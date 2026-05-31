import type { DisplayPage } from '../api';

interface AnnouncementPageProps {
  page: DisplayPage;
}

export default function AnnouncementPage({ page }: AnnouncementPageProps) {
  const isUrgent = page.announcement?.priority === 'urgent';

  return (
    <div className="h-full flex items-center justify-center px-16">
      <div className={`w-full max-w-[1400px] rounded-2xl p-12 ${isUrgent ? 'border-l-8' : ''}`}
        style={{
          backgroundColor: 'var(--brand-navy-mid)',
          borderLeftColor: isUrgent ? 'var(--status-red)' : undefined,
        }}>
        {/* Label */}
        <p className="text-[28px] uppercase tracking-[0.1em] mb-4"
          style={{ color: isUrgent ? 'var(--status-red)' : 'var(--brand-gold)' }}>
          {isUrgent ? 'URGENT NOTICE' : 'ANNOUNCEMENT'}
        </p>

        {/* Title */}
        <h2 className="text-white text-[56px] font-bold leading-tight mb-8">
          {page.title}
        </h2>

        <div className="flex gap-12">
          {/* Body text */}
          <div className={page.image_path ? 'flex-1' : 'w-full'}>
            <p className="text-white text-[36px] leading-relaxed opacity-90">
              {page.announcement?.body_text || ''}
            </p>
          </div>

          {/* Optional image */}
          {page.image_path && (
            <div className="w-[500px] shrink-0">
              <img
                src={page.image_path}
                alt=""
                className="w-full h-auto rounded-xl object-cover"
              />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

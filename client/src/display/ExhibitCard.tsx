import { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';

interface Exhibit {
  slug: string;
  title: string;
  year_introduced: number | null;
  body_text: string;
  key_facts: string[];
  people: string | null;
  related_exhibits: string | null;
  source_ref: string;
  ingested_at: string | null;
  hero_image: string | null;
  video_url: string | null;
  deep_content_url: string | null;
  location: string | null;
}

type State =
  | { status: 'loading' }
  | { status: 'error' }
  | { status: 'ready'; exhibit: Exhibit };

export default function ExhibitCard() {
  const { slug } = useParams<{ slug: string }>();
  const [state, setState] = useState<State>({ status: 'loading' });

  useEffect(() => {
    let cancelled = false;
    if (!slug) {
      setState({ status: 'error' });
      return;
    }
    fetch(`/api/exhibits/${slug}`)
      .then((resp) => {
        if (!resp.ok) throw new Error('not found');
        return resp.json();
      })
      .then((exhibit: Exhibit) => {
        if (!cancelled) setState({ status: 'ready', exhibit });
      })
      .catch(() => {
        if (!cancelled) setState({ status: 'error' });
      });
    return () => {
      cancelled = true;
    };
  }, [slug]);

  if (state.status === 'loading') {
    return (
      <div
        className="min-h-screen w-full flex items-center justify-center"
        style={{ backgroundColor: 'var(--brand-navy)' }}
      >
        <p className="text-white/70 text-2xl">Loading…</p>
      </div>
    );
  }

  if (state.status === 'error') {
    return (
      <div
        className="min-h-screen w-full flex items-center justify-center px-6"
        style={{ backgroundColor: 'var(--brand-navy)' }}
      >
        <div className="text-center">
          <p className="text-3xl font-bold" style={{ color: 'var(--brand-gold)' }}>
            Exhibit not found
          </p>
          <p className="text-white/60 text-lg mt-3">
            This exhibit isn’t available. Check the link or QR code and try again.
          </p>
        </div>
      </div>
    );
  }

  const e = state.exhibit;
  const bodyParagraphs = e.body_text
    .split('\n')
    .map((p) => p.trim())
    .filter(Boolean);

  return (
    <div className="min-h-screen w-full" style={{ backgroundColor: 'var(--brand-navy)' }}>
      <article className="max-w-2xl mx-auto px-6 py-12">
        {/* Amber accent label */}
        <p
          className="text-sm uppercase tracking-[0.18em] mb-3"
          style={{ color: 'var(--brand-gold)' }}
        >
          {e.location || 'VCF Museum @ InfoAge'}
        </p>

        {/* Title */}
        <h1 className="text-white text-4xl md:text-5xl font-bold leading-tight">
          {e.title}
        </h1>

        {/* Dateline */}
        {e.year_introduced != null && (
          <p className="text-white/50 text-base mt-2 font-mono">{e.year_introduced}</p>
        )}

        {/* Optional hero image */}
        {e.hero_image && (
          <img
            src={e.hero_image}
            alt={e.title}
            className="w-full h-auto rounded-xl mt-8 object-cover"
          />
        )}

        {/* Body */}
        {bodyParagraphs.length > 0 && (
          <div className="mt-8 space-y-4">
            {bodyParagraphs.map((p, i) => (
              <p key={i} className="text-white/90 text-lg leading-relaxed">
                {p}
              </p>
            ))}
          </div>
        )}

        {/* Key facts */}
        {e.key_facts.length > 0 && (
          <section className="mt-10">
            <h2
              className="text-sm uppercase tracking-[0.18em] mb-4"
              style={{ color: 'var(--brand-gold)' }}
            >
              Key facts
            </h2>
            <ul className="space-y-2">
              {e.key_facts.map((fact, i) => (
                <li key={i} className="text-white/85 text-base flex gap-3">
                  <span style={{ color: 'var(--brand-gold)' }} aria-hidden>
                    •
                  </span>
                  <span>{fact}</span>
                </li>
              ))}
            </ul>
          </section>
        )}

        {/* People */}
        {e.people && (
          <p className="text-white/70 text-base mt-8">
            <span style={{ color: 'var(--brand-gold)' }}>People:</span> {e.people}
          </p>
        )}

        {/* See also */}
        {e.related_exhibits && (
          <p className="text-white/70 text-base mt-4">
            <span style={{ color: 'var(--brand-gold)' }}>See also:</span> {e.related_exhibits}
          </p>
        )}

        {/* Deep-dive link */}
        {e.deep_content_url && (
          <a
            href={e.deep_content_url}
            className="inline-block mt-10 text-base underline"
            style={{ color: 'var(--brand-gold-light)' }}
          >
            Learn more →
          </a>
        )}
      </article>
    </div>
  );
}

import { useEffect, useState, type ReactNode } from 'react';

/**
 * Locks the display to a fixed 1920×1080 design canvas and scales it with
 * a CSS transform to fit the browser's reported viewport.
 *
 * Why: kiosk devices (Fully Kiosk on Android TV, Onn streaming sticks,
 * 4K monitors via 1080p boxes) report widely varying CSS viewports even
 * when the physical panel is 1080p. Without this wrapper, hard-coded-px
 * layouts either overflow or shrink awkwardly. With it, every kiosk
 * renders exactly what the Pi renders, just scaled to fit.
 *
 * Uses transform-origin: top left + translate for centering so the
 * scaled content anchors to a known point.
 */
export default function DisplayCanvas({ children }: { children: ReactNode }) {
  const DESIGN_W = 1920;
  const DESIGN_H = 1080;

  const [dims, setDims] = useState(() => ({
    scale: 1,
    offsetX: 0,
    offsetY: 0,
    viewportW: DESIGN_W,
    viewportH: DESIGN_H,
  }));

  useEffect(() => {
    const compute = () => {
      const w = window.innerWidth;
      const h = window.innerHeight;
      const scale = Math.min(w / DESIGN_W, h / DESIGN_H);
      const offsetX = (w - DESIGN_W * scale) / 2;
      const offsetY = (h - DESIGN_H * scale) / 2;
      setDims({ scale, offsetX, offsetY, viewportW: w, viewportH: h });
    };

    compute();
    window.addEventListener('resize', compute);
    return () => window.removeEventListener('resize', compute);
  }, []);

  const debug = new URLSearchParams(window.location.search).has('debug');

  return (
    <div
      className="fixed inset-0 overflow-hidden"
      style={{ backgroundColor: 'var(--brand-navy)' }}
    >
      <div
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          width: `${DESIGN_W}px`,
          height: `${DESIGN_H}px`,
          transform: `translate(${dims.offsetX}px, ${dims.offsetY}px) scale(${dims.scale})`,
          transformOrigin: 'top left',
        }}
      >
        {children}
      </div>
      {debug && (
        <div
          style={{
            position: 'fixed',
            top: 4,
            left: 4,
            padding: '4px 8px',
            fontFamily: 'monospace',
            fontSize: '12px',
            color: 'white',
            background: 'rgba(0,0,0,0.6)',
            zIndex: 9999,
          }}
        >
          viewport {dims.viewportW}×{dims.viewportH} · scale {dims.scale.toFixed(3)} ·
          DPR {window.devicePixelRatio}
        </div>
      )}
    </div>
  );
}

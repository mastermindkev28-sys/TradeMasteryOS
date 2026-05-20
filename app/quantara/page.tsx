'use client';

import { useEffect, useRef, useState } from 'react';

// ─── Types ────────────────────────────────────────────────────────────────────
interface Particle {
  x: number; y: number;
  vx: number; vy: number;
  opacity: number;
}

// ─── Canvas Background ───────────────────────────────────────────────────────
function NetworkCanvas() {
  const ref = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = ref.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d')!;
    let raf: number;
    let particles: Particle[] = [];

    function init() {
      const w = canvas!.offsetWidth;
      const h = canvas!.offsetHeight;
      particles = Array.from({ length: 55 }, () => ({
        x: Math.random() * w,
        y: Math.random() * h,
        vx: (Math.random() - 0.5) * 0.28,
        vy: (Math.random() - 0.5) * 0.28,
        opacity: Math.random() * 0.32 + 0.08,
      }));
    }

    function resize() {
      const dpr = window.devicePixelRatio || 1;
      const w = canvas!.offsetWidth;
      const h = canvas!.offsetHeight;
      canvas!.width = w * dpr;
      canvas!.height = h * dpr;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      init();
    }

    function draw() {
      const w = canvas!.offsetWidth;
      const h = canvas!.offsetHeight;
      ctx.clearRect(0, 0, w, h);

      // Subtle grid
      ctx.lineWidth = 1;
      ctx.strokeStyle = 'rgba(255,255,255,0.022)';
      for (let x = 0; x <= w; x += 80) {
        ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, h); ctx.stroke();
      }
      for (let y = 0; y <= h; y += 80) {
        ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke();
      }

      // Move particles
      for (const p of particles) {
        p.x += p.vx; p.y += p.vy;
        if (p.x < 0 || p.x > w) p.vx *= -1;
        if (p.y < 0 || p.y > h) p.vy *= -1;
      }

      // Connections
      for (let i = 0; i < particles.length; i++) {
        for (let j = i + 1; j < particles.length; j++) {
          const dx = particles[i].x - particles[j].x;
          const dy = particles[i].y - particles[j].y;
          const d = Math.hypot(dx, dy);
          if (d < 125) {
            ctx.beginPath();
            ctx.moveTo(particles[i].x, particles[i].y);
            ctx.lineTo(particles[j].x, particles[j].y);
            ctx.strokeStyle = `rgba(163,217,255,${(1 - d / 125) * 0.065})`;
            ctx.lineWidth = 0.5;
            ctx.stroke();
          }
        }
      }

      // Dots
      for (const p of particles) {
        ctx.beginPath();
        ctx.arc(p.x, p.y, 1.5, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(163,217,255,${p.opacity})`;
        ctx.fill();
      }

      raf = requestAnimationFrame(draw);
    }

    const ro = new ResizeObserver(resize);
    ro.observe(canvas);
    resize();
    draw();

    return () => {
      cancelAnimationFrame(raf);
      ro.disconnect();
    };
  }, []);

  return (
    <canvas
      ref={ref}
      style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', display: 'block' }}
    />
  );
}

// ─── SVG Logo Mark ────────────────────────────────────────────────────────────
function QMark({ size = 50 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 200 200" fill="none" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <linearGradient id="qg-a" x1="20" y1="10" x2="180" y2="190" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stopColor="#ECECEC" />
          <stop offset="22%" stopColor="#F8F8F8" />
          <stop offset="45%" stopColor="#B8B8B8" />
          <stop offset="68%" stopColor="#E4E4E4" />
          <stop offset="100%" stopColor="#8C8C8C" />
        </linearGradient>
        <linearGradient id="qg-b" x1="180" y1="20" x2="30" y2="180" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stopColor="#D8D8D8" />
          <stop offset="40%" stopColor="#F2F2F2" />
          <stop offset="100%" stopColor="#9A9A9A" />
        </linearGradient>
        <clipPath id="qg-clip">
          <circle cx="100" cy="97" r="71" />
        </clipPath>
      </defs>

      {/* Outer ring */}
      <circle cx="100" cy="97" r="69" stroke="url(#qg-a)" strokeWidth="13" />

      {/* Q tail — diagonal slash through bottom-right of ring */}
      <line x1="55" y1="156" x2="148" y2="68" stroke="url(#qg-a)" strokeWidth="13" strokeLinecap="round" />
      <line x1="140" y1="64" x2="194" y2="148" stroke="url(#qg-a)" strokeWidth="13" strokeLinecap="round" />

      {/* Inner vertical bar */}
      <line x1="100" y1="30" x2="100" y2="118" stroke="url(#qg-b)" strokeWidth="5.5" strokeLinecap="round" />

      {/* Fine parallel lines — wave/fin in lower-left quadrant, clipped to ring area */}
      {Array.from({ length: 13 }, (_, i) => (
        <line
          key={i}
          x1={40 + i * 4.5}
          y1={172 - i * 1.5}
          x2={78 + i * 3.8}
          y2={113 - i * 7.5}
          stroke="#B8B8B8"
          strokeWidth="1.1"
          strokeLinecap="round"
          opacity={0.12 + i * 0.038}
          clipPath="url(#qg-clip)"
        />
      ))}
    </svg>
  );
}

// ─── Form Styles ──────────────────────────────────────────────────────────────
const S = {
  label: {
    display: 'block' as const,
    color: '#666',
    fontSize: '10px',
    letterSpacing: '0.12em',
    textTransform: 'uppercase' as const,
    marginBottom: '6px',
  },
  input: {
    width: '100%',
    background: 'rgba(255,255,255,0.03)',
    border: '1px solid rgba(255,255,255,0.08)',
    borderRadius: '8px',
    color: '#E0E0E0',
    fontSize: '14px',
    padding: '11px 14px',
    outline: 'none',
    boxSizing: 'border-box' as const,
    fontFamily: 'inherit',
    transition: 'border-color 0.2s',
  },
  cta: {
    background: 'transparent',
    border: '1px solid rgba(163,217,255,0.35)',
    color: '#A3D9FF',
    borderRadius: '8px',
    padding: '14px 32px',
    fontSize: '11px',
    letterSpacing: '0.22em',
    textTransform: 'uppercase' as const,
    cursor: 'pointer',
    fontFamily: 'inherit',
    transition: 'all 0.2s',
  },
};

// ─── Modal ────────────────────────────────────────────────────────────────────
function Modal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const [done, setDone] = useState(false);
  const [f, setF] = useState({ name: '', email: '', phone: '', size: '', note: '', ack: false });

  if (!open) return null;

  const submit = (e: React.FormEvent) => { e.preventDefault(); setDone(true); };

  return (
    <div
      style={{
        position: 'fixed', inset: 0, zIndex: 1000,
        background: 'rgba(0,0,0,0.88)',
        backdropFilter: 'blur(12px)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        padding: '20px',
      }}
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      <div style={{
        background: '#0F0F0F',
        border: '1px solid rgba(255,255,255,0.09)',
        borderRadius: '16px',
        padding: '44px',
        maxWidth: '500px',
        width: '100%',
        position: 'relative',
        maxHeight: '90vh',
        overflowY: 'auto',
      }}>
        <button
          onClick={onClose}
          style={{
            position: 'absolute', top: 18, right: 18,
            background: 'none', border: 'none', color: '#555',
            cursor: 'pointer', fontSize: '22px', lineHeight: 1, fontFamily: 'inherit',
          }}
        >×</button>

        {done ? (
          <div style={{ textAlign: 'center', padding: '32px 0' }}>
            <div style={{ color: '#A3D9FF', fontSize: '10px', letterSpacing: '0.2em', textTransform: 'uppercase', marginBottom: '20px' }}>
              Received
            </div>
            <h3 style={{ color: '#E8E8E8', fontSize: '24px', fontWeight: 200, letterSpacing: '-0.02em', marginBottom: '16px' }}>
              Your request has been received.
            </h3>
            <p style={{ color: '#555', fontSize: '14px', lineHeight: 1.9 }}>
              Qualified inquiries are reviewed in the order received. We will be in touch if your profile aligns with current program parameters.
            </p>
          </div>
        ) : (
          <>
            <div style={{ color: '#A3D9FF', fontSize: '10px', letterSpacing: '0.22em', textTransform: 'uppercase', marginBottom: '10px' }}>
              Private Program
            </div>
            <h3 style={{ color: '#E8E8E8', fontSize: '22px', fontWeight: 200, letterSpacing: '-0.02em', marginBottom: '6px' }}>
              Request Consideration
            </h3>
            <p style={{ color: '#444', fontSize: '13px', marginBottom: '32px', lineHeight: 1.7 }}>
              Quantara System One — Institutional Gold Algorithmic Program
            </p>

            <form onSubmit={submit} style={{ display: 'flex', flexDirection: 'column', gap: '18px' }}>
              <div>
                <label style={S.label}>Full Name *</label>
                <input required value={f.name} onChange={e => setF(p => ({ ...p, name: e.target.value }))} style={S.input} placeholder="Your full name" />
              </div>
              <div>
                <label style={S.label}>Email Address *</label>
                <input required type="email" value={f.email} onChange={e => setF(p => ({ ...p, email: e.target.value }))} style={S.input} placeholder="your@email.com" />
              </div>
              <div>
                <label style={S.label}>Phone <span style={{ color: '#3A3A3A' }}>Optional</span></label>
                <input value={f.phone} onChange={e => setF(p => ({ ...p, phone: e.target.value }))} style={S.input} placeholder="+1 (000) 000-0000" />
              </div>
              <div>
                <label style={S.label}>Account Size Interest *</label>
                <select
                  required
                  value={f.size}
                  onChange={e => setF(p => ({ ...p, size: e.target.value }))}
                  style={{ ...S.input, appearance: 'none' as const, WebkitAppearance: 'none' as const }}
                >
                  <option value="">Select size...</option>
                  <option value="50k">$50,000</option>
                  <option value="100k">$100,000</option>
                  <option value="150k">$150,000</option>
                  <option value="other">Other</option>
                </select>
              </div>
              <div>
                <label style={S.label}>Why are you exploring systematic approaches?</label>
                <textarea
                  value={f.note}
                  onChange={e => setF(p => ({ ...p, note: e.target.value }))}
                  style={{ ...S.input, height: '88px', resize: 'none' as const }}
                  placeholder="Brief note..."
                />
              </div>
              <div style={{ display: 'flex', gap: '12px', alignItems: 'flex-start' }}>
                <input
                  required
                  type="checkbox"
                  id="qs-ack"
                  checked={f.ack}
                  onChange={e => setF(p => ({ ...p, ack: e.target.checked }))}
                  style={{ marginTop: '3px', flexShrink: 0, accentColor: '#A3D9FF', cursor: 'pointer' }}
                />
                <label htmlFor="qs-ack" style={{ color: '#555', fontSize: '12px', lineHeight: 1.7, cursor: 'pointer' }}>
                  I acknowledge this is a private program for qualified participants only and understand all trading involves substantial risk of loss.
                </label>
              </div>
              <button type="submit" style={{
                ...S.cta,
                padding: '15px',
                width: '100%',
                marginTop: '4px',
                fontSize: '11px',
              }}>
                Request Consideration
              </button>
            </form>
          </>
        )}
      </div>
    </div>
  );
}

// ─── Main Page ─────────────────────────────────────────────────────────────────
export default function QuantaraPage() {
  const [modal, setModal] = useState(false);
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    // Load Inter font
    const link = document.createElement('link');
    link.href = 'https://fonts.googleapis.com/css2?family=Inter:wght@200;300;400;500;600&display=swap';
    link.rel = 'stylesheet';
    document.head.appendChild(link);

    const onScroll = () => setScrolled(window.scrollY > 50);
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => {
      window.removeEventListener('scroll', onScroll);
      document.head.removeChild(link);
    };
  }, []);

  const go = (id: string) => document.getElementById(id)?.scrollIntoView({ behavior: 'smooth' });
  const openModal = () => setModal(true);

  const navLinks = [
    ['Systems', 'qs-systems'],
    ['Approach', 'qs-approach'],
    ['Infrastructure', 'qs-infrastructure'],
    ['Considerations', 'qs-considerations'],
    ['Access', 'qs-access'],
  ];

  return (
    <>
      {/* ── Global overrides for this route ── */}
      <style>{`
        *, *::before, *::after { box-sizing: border-box; }
        .qs-wrap {
          font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
          background: #0A0A0A;
          color: #F0F0F0;
          min-height: 100vh;
          width: 100%;
          -webkit-font-smoothing: antialiased;
          -moz-osx-font-smoothing: grayscale;
        }
        .qs-wrap * { font-family: inherit; }
        .qs-nav-link { background: none; border: none; color: #4A4A4A; font-size: 11px; letter-spacing: 0.14em; text-transform: uppercase; cursor: pointer; transition: color 0.2s; padding: 4px 0; }
        .qs-nav-link:hover { color: #B0B0B0; }
        .qs-cta:hover { background: rgba(163,217,255,0.1) !important; border-color: rgba(163,217,255,0.65) !important; }
        .qs-card { transition: background 0.2s, border-color 0.2s; }
        .qs-card:hover { background: rgba(255,255,255,0.035) !important; border-color: rgba(255,255,255,0.1) !important; }
        .qs-quote-card { transition: border-color 0.25s; }
        .qs-quote-card:hover { border-color: rgba(255,255,255,0.1) !important; }
        .qs-input:focus { border-color: rgba(163,217,255,0.4) !important; }
        @keyframes qs-up { from { opacity: 0; transform: translateY(22px); } to { opacity: 1; transform: none; } }
        .qs-a0 { animation: qs-up 0.9s ease both; }
        .qs-a1 { animation: qs-up 0.9s ease 0.18s both; }
        .qs-a2 { animation: qs-up 0.9s ease 0.34s both; }
        .qs-a3 { animation: qs-up 0.9s ease 0.5s both; }
        @keyframes qs-pulse { 0%,100% { opacity: 0.3; } 50% { opacity: 0.7; } }
        .qs-dot { animation: qs-pulse 2.8s ease-in-out infinite; }
        @media (max-width: 800px) {
          .qs-nav-links { display: none !important; }
          .qs-hero-h1 { font-size: 34px !important; }
          .qs-grid-2 { grid-template-columns: 1fr !important; gap: 48px !important; }
          .qs-grid-3 { grid-template-columns: 1fr !important; }
          .qs-section { padding: 80px 24px !important; }
          .qs-hero-inner { padding: 0 20px !important; }
          .qs-footer-inner { grid-template-columns: 1fr !important; text-align: left !important; }
          .qs-footer-right { text-align: left !important; }
        }
      `}</style>

      <div className="qs-wrap">

        {/* ── NAVIGATION ── */}
        <nav style={{
          position: 'fixed', top: 0, left: 0, right: 0, zIndex: 200,
          height: 64,
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          padding: '0 48px',
          background: scrolled ? 'rgba(10,10,10,0.94)' : 'transparent',
          backdropFilter: scrolled ? 'blur(20px)' : 'none',
          borderBottom: scrolled ? '1px solid rgba(255,255,255,0.05)' : 'none',
          transition: 'background 0.35s, backdrop-filter 0.35s, border-color 0.35s',
        }}>
          {/* Logo */}
          <div
            style={{ display: 'flex', alignItems: 'center', gap: 10, cursor: 'pointer' }}
            onClick={() => go('qs-hero')}
          >
            <QMark size={34} />
            <div>
              <div style={{ fontSize: 13, fontWeight: 300, letterSpacing: '0.28em', textTransform: 'uppercase', color: '#D8D8D8', lineHeight: 1.2 }}>
                Quantara
              </div>
              <div style={{ fontSize: 8, letterSpacing: '0.18em', textTransform: 'uppercase', color: '#3A3A3A', marginTop: 1 }}>
                Systems
              </div>
            </div>
          </div>

          {/* Nav links */}
          <div className="qs-nav-links" style={{ display: 'flex', alignItems: 'center', gap: 36 }}>
            {navLinks.map(([label, id]) => (
              <button key={id} className="qs-nav-link" onClick={() => go(id)}>{label}</button>
            ))}
            <button
              className="qs-cta"
              onClick={openModal}
              style={{
                ...S.cta,
                padding: '8px 18px',
                marginLeft: 8,
              }}
            >
              Request Consideration
            </button>
          </div>
        </nav>

        {/* ── HERO ── */}
        <section id="qs-hero" style={{ position: 'relative', height: '100vh', minHeight: 720, overflow: 'hidden', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <NetworkCanvas />

          {/* Radial glow */}
          <div style={{
            position: 'absolute', inset: 0, pointerEvents: 'none', zIndex: 0,
            background: 'radial-gradient(ellipse 70% 55% at 50% 52%, rgba(163,217,255,0.042) 0%, transparent 70%)',
          }} />

          {/* Top/bottom fades */}
          <div style={{ position: 'absolute', top: 0, left: 0, right: 0, height: 180, background: 'linear-gradient(to bottom, #0A0A0A, transparent)', pointerEvents: 'none', zIndex: 1 }} />
          <div style={{ position: 'absolute', bottom: 0, left: 0, right: 0, height: 220, background: 'linear-gradient(to top, #0A0A0A, transparent)', pointerEvents: 'none', zIndex: 1 }} />

          {/* Hero content */}
          <div className="qs-hero-inner" style={{ position: 'relative', zIndex: 2, textAlign: 'center', padding: '0 28px', maxWidth: 920 }}>
            <div className="qs-a0" style={{ display: 'flex', justifyContent: 'center', marginBottom: 44 }}>
              <QMark size={104} />
            </div>

            <div className="qs-a1" style={{ fontSize: 9, letterSpacing: '0.32em', textTransform: 'uppercase', color: '#3C3C3C', marginBottom: 28 }}>
              Quantitative Market Systems
            </div>

            <h1 className="qs-a2 qs-hero-h1" style={{
              fontSize: 54, fontWeight: 200, letterSpacing: '-0.035em',
              lineHeight: 1.08, color: '#EDEDED', marginBottom: 10,
            }}>
              Quantara System One
            </h1>
            <div className="qs-a2" style={{ fontSize: 13, letterSpacing: '0.22em', textTransform: 'uppercase', color: '#3E3E3E', marginBottom: 28, fontWeight: 300 }}>
              QS1 &nbsp;·&nbsp; Institutional Gold Algorithmic Program
            </div>

            <p className="qs-a3" style={{ color: '#505050', fontSize: 16, lineHeight: 1.85, maxWidth: 620, margin: '0 auto 44px', fontWeight: 300 }}>
              A proprietary quantitative framework for algorithmic execution in Gold futures markets. Structured systems that interpret market behavior through machine learning models, statistical frameworks, and institutional risk architecture.
            </p>

            <div className="qs-a3" style={{ display: 'flex', gap: 16, justifyContent: 'center', flexWrap: 'wrap' }}>
              <button className="qs-cta" onClick={openModal} style={{ ...S.cta, padding: '15px 36px', fontSize: 11 }}>
                Request Consideration
              </button>
              <button
                onClick={() => go('qs-systems')}
                style={{
                  ...S.cta,
                  padding: '15px 36px',
                  fontSize: 11,
                  borderColor: 'rgba(255,255,255,0.08)',
                  color: '#4A4A4A',
                }}
              >
                Explore the System
              </button>
            </div>
          </div>

          {/* Scroll indicator */}
          <div style={{ position: 'absolute', bottom: 36, left: '50%', transform: 'translateX(-50%)', zIndex: 2, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 8 }}>
            <div style={{ width: 1, height: 52, background: 'linear-gradient(to bottom, transparent, rgba(255,255,255,0.16))' }} />
            <div className="qs-dot" style={{ width: 4, height: 4, borderRadius: '50%', background: 'rgba(163,217,255,0.5)' }} />
          </div>
        </section>

        {/* ── THE SYSTEM ── */}
        <section id="qs-systems" className="qs-section" style={{ padding: '130px 48px' }}>
          <div style={{ maxWidth: 1160, margin: '0 auto' }}>

            {/* Section header */}
            <div style={{ marginBottom: 68 }}>
              <div style={{ fontSize: 9, letterSpacing: '0.28em', textTransform: 'uppercase', color: '#A3D9FF', marginBottom: 18, opacity: 0.8 }}>
                The System
              </div>
              <h2 style={{ fontSize: 42, fontWeight: 200, letterSpacing: '-0.025em', color: '#EDEDED', marginBottom: 22, maxWidth: 560 }}>
                Structured Quantitative Execution
              </h2>
              <p style={{ color: '#484848', fontSize: 16, lineHeight: 1.92, maxWidth: 660, fontWeight: 300 }}>
                Quantara System One (QS1) is an institutional-grade algorithmic trading infrastructure focused on Gold futures (GC/MGC). The system integrates multi-year quantitative research with machine learning models for consistent, non-discretionary execution.
              </p>
            </div>

            {/* Feature grid */}
            <div className="qs-grid-3" style={{
              display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)',
              gap: 1,
              background: 'rgba(255,255,255,0.04)',
              border: '1px solid rgba(255,255,255,0.04)',
              borderRadius: 16,
              overflow: 'hidden',
              marginBottom: 56,
            }}>
              {[
                { n: '01', title: 'Market Microstructure Evaluation', body: 'Session-aware analysis of order flow dynamics, liquidity zones, and structural inflection points in Gold futures markets.' },
                { n: '02', title: 'Statistical Pattern Recognition', body: 'Neural architectures trained on tick-level historical data to identify environments with statistically observable characteristics.' },
                { n: '03', title: 'Volatility Regime Filtering', body: 'Multi-regime detection framework that adapts execution parameters based on prevailing volatility and correlation states.' },
                { n: '04', title: 'Dynamic Risk Architecture', body: 'Proprietary risk allocation with adaptive position sizing, drawdown controls, and consistency rule compliance.' },
                { n: '05', title: 'Automated Execution Engine', body: 'Fully automated trade identification, entry, and management. Zero manual intervention required during operation.' },
                { n: '06', title: 'Platform Integration', body: 'Native connectivity to Tradovate, TradingView, and Lucid Trading proprietary capital program infrastructure.' },
              ].map(item => (
                <div
                  key={item.n}
                  className="qs-card"
                  style={{ padding: 32, background: '#0D0D0D', borderRight: '1px solid rgba(255,255,255,0.04)', borderBottom: '1px solid rgba(255,255,255,0.04)' }}
                >
                  <div style={{ fontSize: 10, color: '#2A2A2A', letterSpacing: '0.1em', marginBottom: 18, fontVariantNumeric: 'tabular-nums' }}>
                    {item.n}
                  </div>
                  <h3 style={{ fontSize: 14, fontWeight: 400, color: '#C8C8C8', marginBottom: 12, letterSpacing: '-0.01em', lineHeight: 1.4 }}>
                    {item.title}
                  </h3>
                  <p style={{ color: '#484848', fontSize: 13, lineHeight: 1.85 }}>
                    {item.body}
                  </p>
                </div>
              ))}
            </div>

            {/* Risk notice */}
            <div style={{ border: '1px solid rgba(255,255,255,0.05)', borderRadius: 8, padding: '18px 24px', background: 'rgba(255,255,255,0.015)' }}>
              <p style={{ color: '#383838', fontSize: 12, lineHeight: 1.85 }}>
                <span style={{ color: '#484848', fontWeight: 500 }}>Risk Disclosure —</span> All trading involves substantial risk of loss. Past performance does not indicate future results. QS1 does not predict markets or guarantee specific outcomes. Participation is restricted to qualified individuals only.
              </p>
            </div>
          </div>
        </section>

        {/* ── APPROACH ── */}
        <section id="qs-approach" className="qs-section" style={{ padding: '130px 48px', background: 'linear-gradient(180deg, #0A0A0A 0%, #0C1018 60%, #0A0A0A 100%)' }}>
          <div style={{ maxWidth: 1160, margin: '0 auto' }}>
            <div style={{ marginBottom: 68 }}>
              <div style={{ fontSize: 9, letterSpacing: '0.28em', textTransform: 'uppercase', color: '#A3D9FF', marginBottom: 18, opacity: 0.8 }}>
                Development
              </div>
              <h2 style={{ fontSize: 42, fontWeight: 200, letterSpacing: '-0.025em', color: '#EDEDED', maxWidth: 480 }}>
                Research-Driven Development
              </h2>
            </div>

            <div className="qs-grid-2" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 88, alignItems: 'start' }}>
              <div>
                <p style={{ color: '#4A4A4A', fontSize: 15, lineHeight: 1.95, marginBottom: 28, fontWeight: 300 }}>
                  QS1 originated as a quantitative research initiative examining whether structured AI frameworks could provide consistent execution in Gold futures while prioritizing capital preservation and statistical discipline.
                </p>
                <p style={{ color: '#3A3A3A', fontSize: 14, lineHeight: 1.95, fontWeight: 300 }}>
                  The system does not predict markets. It identifies environments with historically observable statistical characteristics and applies predefined execution rules without discretionary override.
                </p>

                {/* Metrics row */}
                <div style={{ display: 'flex', gap: 40, marginTop: 48 }}>
                  {[
                    { val: 'GC/MGC', label: 'Focus Markets' },
                    { val: 'ML/RL', label: 'Model Architecture' },
                    { val: '100%', label: 'Automated' },
                  ].map(m => (
                    <div key={m.label}>
                      <div style={{ fontSize: 20, fontWeight: 200, color: '#C0C0C0', letterSpacing: '-0.02em', marginBottom: 4 }}>{m.val}</div>
                      <div style={{ fontSize: 10, color: '#383838', letterSpacing: '0.12em', textTransform: 'uppercase' }}>{m.label}</div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Timeline */}
              <div style={{ display: 'flex', flexDirection: 'column' }}>
                {[
                  { phase: 'Phase I', title: 'Historical Analysis', body: 'Extensive tick-level historical analysis of Gold futures spanning multiple market cycles and volatility regimes.' },
                  { phase: 'Phase II', title: 'Model Development', body: 'Neural pattern recognition and reinforcement learning optimization across defined objective functions.' },
                  { phase: 'Phase III', title: 'Forward Testing', body: 'Multi-year forward testing in live market conditions with structured performance monitoring and parameter refinement.' },
                  { phase: 'Phase IV', title: 'Infrastructure Integration', body: 'Integration with proprietary capital frameworks and establishment of execution monitoring protocols.' },
                ].map((item, i, arr) => (
                  <div key={i} style={{ display: 'flex', gap: 24, paddingBottom: i < arr.length - 1 ? 36 : 0 }}>
                    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                      <div style={{
                        width: 30, height: 30, borderRadius: '50%',
                        border: '1px solid rgba(163,217,255,0.18)',
                        display: 'flex', alignItems: 'center', justifyContent: 'center',
                        flexShrink: 0,
                      }}>
                        <div style={{ width: 6, height: 6, borderRadius: '50%', background: 'rgba(163,217,255,0.55)' }} />
                      </div>
                      {i < arr.length - 1 && (
                        <div style={{ width: 1, flex: 1, background: 'rgba(163,217,255,0.07)', marginTop: 8 }} />
                      )}
                    </div>
                    <div style={{ paddingTop: 5 }}>
                      <div style={{ fontSize: 9, letterSpacing: '0.18em', textTransform: 'uppercase', color: 'rgba(163,217,255,0.45)', marginBottom: 4 }}>
                        {item.phase}
                      </div>
                      <div style={{ fontSize: 14, fontWeight: 400, color: '#B0B0B0', marginBottom: 8 }}>
                        {item.title}
                      </div>
                      <p style={{ color: '#484848', fontSize: 13, lineHeight: 1.85 }}>
                        {item.body}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </section>

        {/* ── TESTIMONIALS ── */}
        <section id="qs-infrastructure" className="qs-section" style={{ padding: '130px 48px' }}>
          <div style={{ maxWidth: 1160, margin: '0 auto' }}>
            <div style={{ marginBottom: 68 }}>
              <div style={{ fontSize: 9, letterSpacing: '0.28em', textTransform: 'uppercase', color: '#A3D9FF', marginBottom: 18, opacity: 0.8 }}>
                Perspectives
              </div>
              <h2 style={{ fontSize: 42, fontWeight: 200, letterSpacing: '-0.025em', color: '#EDEDED' }}>
                Participant Perspectives
              </h2>
            </div>

            <div className="qs-grid-2" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20, marginBottom: 60 }}>
              {[
                { q: 'The systematic nature of QS1 removed the emotional variables I struggled with in discretionary trading. The infrastructure simply executes.', name: 'M.R.', role: 'Family Office Allocator' },
                { q: 'Having a research-grade framework manage execution allows me to allocate attention elsewhere while maintaining alignment with prop firm requirements.', name: 'D.K.', role: 'Accredited Participant' },
                { q: "The infrastructure's focus on structure and consistency has been evident in the account behavior from the first month of operation.", name: 'S.L.', role: 'QS1 Participant since 2024' },
                { q: 'I was looking for a systematic approach that did not require constant monitoring. QS1 operates within clearly defined parameters without intervention.', name: 'T.M.', role: 'Independent Allocator' },
              ].map((t, i) => (
                <div
                  key={i}
                  className="qs-quote-card"
                  style={{ border: '1px solid rgba(255,255,255,0.055)', borderRadius: 12, padding: 32, background: '#0D0D0D' }}
                >
                  <div style={{ color: '#3A3A3A', fontSize: 28, lineHeight: 1, marginBottom: 20, fontWeight: 200 }}>&ldquo;</div>
                  <p style={{ color: '#6A6A6A', fontSize: 15, lineHeight: 1.92, fontWeight: 300, marginBottom: 28, fontStyle: 'italic' }}>
                    {t.q}
                  </p>
                  <div style={{ borderTop: '1px solid rgba(255,255,255,0.04)', paddingTop: 18 }}>
                    <div style={{ fontSize: 13, color: '#B8B8B8', fontWeight: 400 }}>{t.name}</div>
                    <div style={{ fontSize: 11, color: '#3A3A3A', letterSpacing: '0.06em', marginTop: 3 }}>{t.role}</div>
                  </div>
                </div>
              ))}
            </div>

            <div style={{ textAlign: 'center' }}>
              <button className="qs-cta" onClick={openModal} style={S.cta}>
                Request Consideration
              </button>
            </div>
          </div>
        </section>

        {/* ── PROGRAM CONSIDERATIONS ── */}
        <section id="qs-considerations" className="qs-section" style={{ padding: '130px 48px', background: 'linear-gradient(180deg, #0A0A0A 0%, #0C1018 100%)' }}>
          <div style={{ maxWidth: 1160, margin: '0 auto' }}>
            <div style={{ marginBottom: 68 }}>
              <div style={{ fontSize: 9, letterSpacing: '0.28em', textTransform: 'uppercase', color: '#A3D9FF', marginBottom: 18, opacity: 0.8 }}>
                Parameters
              </div>
              <h2 style={{ fontSize: 42, fontWeight: 200, letterSpacing: '-0.025em', color: '#EDEDED' }}>
                Program Considerations
              </h2>
            </div>

            <div className="qs-grid-2" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 72, marginBottom: 60 }}>

              {/* Program structure */}
              <div>
                <div style={{ fontSize: 10, letterSpacing: '0.14em', textTransform: 'uppercase', color: '#333', marginBottom: 28 }}>
                  Program Structure
                </div>
                {[
                  ['Structure', 'Private, invite-only initiative'],
                  ['Focus', 'Gold futures — GC/MGC'],
                  ['Integration', 'Lucid Trading proprietary frameworks'],
                  ['Fee Model', '20% on successful payouts only'],
                  ['Access', 'Qualified participants only'],
                  ['Operation', 'Fully automated — no manual input'],
                ].map(([k, v]) => (
                  <div key={k} style={{ display: 'flex', justifyContent: 'space-between', padding: '13px 0', borderBottom: '1px solid rgba(255,255,255,0.035)', gap: 16 }}>
                    <span style={{ color: '#383838', fontSize: 13 }}>{k}</span>
                    <span style={{ color: '#7A7A7A', fontSize: 13, textAlign: 'right' }}>{v}</span>
                  </div>
                ))}
              </div>

              {/* Account table */}
              <div>
                <div style={{ fontSize: 10, letterSpacing: '0.14em', textTransform: 'uppercase', color: '#333', marginBottom: 28 }}>
                  Account Parameters
                </div>
                <div style={{ border: '1px solid rgba(255,255,255,0.055)', borderRadius: 10, overflow: 'hidden', marginBottom: 20 }}>
                  <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
                    <thead>
                      <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                        {['Account Size', 'Setup', 'Payout Split'].map(h => (
                          <th key={h} style={{ padding: '12px 16px', textAlign: 'left', color: '#333', fontWeight: 500, fontSize: 10, letterSpacing: '0.1em', textTransform: 'uppercase' }}>
                            {h}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {[
                        ['$50,000', 'One-time fee', '80 / 20'],
                        ['$100,000', 'One-time fee', '80 / 20'],
                        ['$150,000', 'One-time fee', '80 / 20'],
                      ].map(([sz, st, sp]) => (
                        <tr key={sz} style={{ borderBottom: '1px solid rgba(255,255,255,0.028)' }}>
                          <td style={{ padding: '13px 16px', color: '#B8B8B8' }}>{sz}</td>
                          <td style={{ padding: '13px 16px', color: '#555' }}>{st}</td>
                          <td style={{ padding: '13px 16px', color: '#6A6A6A' }}>{sp}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                {/* Prominent risk block */}
                <div style={{
                  padding: '18px 20px',
                  border: '1px solid rgba(220,80,80,0.1)',
                  borderRadius: 8,
                  background: 'rgba(200,60,60,0.03)',
                }}>
                  <div style={{ fontSize: 9, letterSpacing: '0.2em', textTransform: 'uppercase', color: '#5A3030', marginBottom: 8 }}>
                    Important Disclaimer
                  </div>
                  <p style={{ color: '#4A3232', fontSize: 12, lineHeight: 1.85 }}>
                    All trading involves substantial risk of loss. Past performance does not indicate future results. Participation is restricted to qualified individuals. Quantara Systems does not guarantee any specific outcomes.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* ── ACCESS / LEAD CAPTURE ── */}
        <section id="qs-access" className="qs-section" style={{ padding: '130px 48px' }}>
          <div style={{ maxWidth: 700, margin: '0 auto', textAlign: 'center' }}>
            <div style={{ fontSize: 9, letterSpacing: '0.28em', textTransform: 'uppercase', color: '#A3D9FF', marginBottom: 18, opacity: 0.8 }}>
              Private Program
            </div>
            <h2 style={{ fontSize: 42, fontWeight: 200, letterSpacing: '-0.025em', color: '#EDEDED', marginBottom: 22 }}>
              Request Consideration
            </h2>
            <p style={{ color: '#484848', fontSize: 16, lineHeight: 1.9, marginBottom: 44, fontWeight: 300 }}>
              Quantara System One operates as a private, invite-only initiative. Qualified inquiries are reviewed in the order received. All information submitted is confidential.
            </p>

            <button
              className="qs-cta"
              onClick={openModal}
              style={{ ...S.cta, padding: '18px 52px', fontSize: 12 }}
            >
              Request Consideration
            </button>

            <p style={{ color: '#2A2A2A', fontSize: 11, marginTop: 28, letterSpacing: '0.04em' }}>
              Qualified applicants only · Private & Confidential · No solicitation
            </p>
          </div>
        </section>

        {/* ── FOOTER ── */}
        <footer style={{ borderTop: '1px solid rgba(255,255,255,0.04)', background: '#060606', padding: '56px 48px 40px' }}>
          <div style={{ maxWidth: 1160, margin: '0 auto' }}>
            <div
              className="qs-footer-inner"
              style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 48, marginBottom: 48 }}
            >
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 20 }}>
                  <QMark size={26} />
                  <span style={{ fontSize: 12, fontWeight: 300, letterSpacing: '0.24em', textTransform: 'uppercase', color: '#5A5A5A' }}>
                    Quantara Systems
                  </span>
                </div>
                <p style={{ color: '#2E2E2E', fontSize: 12, lineHeight: 1.9, maxWidth: 380 }}>
                  Quantitative market systems. Structured approaches to market data for qualified participants seeking systematic exposure to modeled market dynamics.
                </p>
              </div>
              <div className="qs-footer-right" style={{ textAlign: 'right' }}>
                <div style={{ fontSize: 9, letterSpacing: '0.16em', textTransform: 'uppercase', color: '#2A2A2A', marginBottom: 14 }}>
                  Private Program
                </div>
                <p style={{ color: '#333', fontSize: 12, lineHeight: 2 }}>
                  Qualified inquiries only.<br />
                  All communications are confidential.<br />
                  <span style={{ color: '#282828' }}>quantarasystems.com</span>
                </p>
              </div>
            </div>

            <div style={{ borderTop: '1px solid rgba(255,255,255,0.025)', paddingTop: 28 }}>
              <p style={{ color: '#242424', fontSize: 11, lineHeight: 1.95, marginBottom: 18 }}>
                <strong style={{ color: '#2E2E2E' }}>RISK DISCLOSURE:</strong> Trading futures contracts involves substantial risk of loss and is not appropriate for all investors. Past performance is not indicative of future results. Quantara Systems does not guarantee profits or freedom from loss. The content on this site is for informational purposes only and does not constitute financial advice, a solicitation, or an offer to buy or sell any financial instrument. Participation in Quantara System One is restricted to qualified, accredited individuals only. All performance data, if presented, reflects historical system behavior and should not be interpreted as a projection or guarantee of future performance. This is a private, confidential program. Unauthorized distribution of any materials is prohibited.
              </p>
              <div style={{ display: 'flex', justifyContent: 'space-between', flexWrap: 'wrap', gap: 8 }}>
                <span style={{ color: '#222', fontSize: 11 }}>© 2026 Quantara Systems. All rights reserved. Confidential.</span>
                <span style={{ color: '#1E1E1E', fontSize: 11 }}>Private Program · Qualified Participants Only</span>
              </div>
            </div>
          </div>
        </footer>

        {/* ── FLOATING CTA ── */}
        <div style={{ position: 'fixed', bottom: 32, right: 32, zIndex: 100 }}>
          <button
            className="qs-cta"
            onClick={openModal}
            style={{
              ...S.cta,
              padding: '12px 22px',
              background: 'rgba(10,10,10,0.95)',
              backdropFilter: 'blur(16px)',
              boxShadow: '0 8px 40px rgba(0,0,0,0.5), 0 0 0 1px rgba(163,217,255,0.08)',
            }}
          >
            Request Consideration
          </button>
        </div>

      </div>

      <Modal open={modal} onClose={() => setModal(false)} />
    </>
  );
}

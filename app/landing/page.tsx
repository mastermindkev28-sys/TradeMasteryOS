import Link from 'next/link';
import Sidebar from '@/components/Sidebar';

export default function LandingPage() {
  return (
    <>
      <Sidebar />
      <main className="main">
        <div className="page active">
          <div className="ph">
            <div className="ph-left">
              <div className="ph-title">🚀 TradingOS Journal</div>
              <div className="ph-sub">A private trading journal and performance dashboard built for traders who want consistency, clarity, and growth.</div>
            </div>
            <div className="ph-actions">
              <Link href="/pricing" className="btn btn-g">View Pricing</Link>
              <Link href="/signup" className="btn btn-b">Start Free Trial</Link>
            </div>
          </div>

          <div className="hero">
            <div className="badge-pill">Paddle-secured checkout</div>
            <h1>Keep every trade, trend, and lesson in one premium trading system.</h1>
            <p>TradingOS gives you a private, polished trading journal with built-in analytics, psychology tracking, and trade review tools — all tied to your Supabase account.</p>
            <div className="hero-actions">
              <Link href="/dashboard" className="btn btn-b">
                <i className="fa-solid fa-arrow-right"></i> Go to Journal
              </Link>
              <Link href="/pricing" className="btn btn-g">View Pricing</Link>
              <Link href="/signup" className="btn">Start Free Trial</Link>
            </div>
            <div className="cta-note">Secure Paddle checkout · 30-day refund policy · Private account data · Built for disciplined traders</div>
          </div>

          <div className="feat-grid">
            <div className="feat-card"><i className="fa-solid fa-chart-line"></i><h3>Live Performance Metrics</h3><p>See your equity curve, win rate, monthly P&L, and R-multiple analytics instantly as you log trades.</p></div>
            <div className="feat-card"><i className="fa-solid fa-brain"></i><h3>Trade Psychology Tracking</h3><p>Capture emotion, risk state, and review execution so you stop repeating the same mistakes.</p></div>
            <div className="feat-card"><i className="fa-solid fa-database"></i><h3>Master Trade Database</h3><p>Log each trade with all details, filter every field, and build a single source of truth for your edge.</p></div>
            <div className="feat-card"><i className="fa-solid fa-sun"></i><h3>Daily Routine</h3><p>Journal your pre-market plan, trade execution, and post-market review in one structured workflow.</p></div>
          </div>

          <div className="plan-grid">
            <div className="plan-card featured">
              <div className="plan-label">Most popular</div>
              <div className="plan-price">$29<span className="plan-period">/month</span></div>
              <p className="plan-detail">Best for active traders who want the full TradingOS experience with analytics, psychology tracking, and unlimited trades.</p>
              <div className="plan-list">
                <div className="plan-list-item"><i className="fa-solid fa-check"></i><span>Unlimited trades</span></div>
                <div className="plan-list-item"><i className="fa-solid fa-check"></i><span>Equity curve & analytics</span></div>
                <div className="plan-list-item"><i className="fa-solid fa-check"></i><span>Psychology journaling</span></div>
                <div className="plan-list-item"><i className="fa-solid fa-check"></i><span>Priority product updates</span></div>
              </div>
              <Link href="/pricing" className="btn btn-g">See Pricing</Link>
            </div>

            <div className="card">
              <div className="card-title"><i className="fa-solid fa-quote-left"></i> Why traders choose TradingOS</div>
              <div className="quote" style={{ margin: 0 }}>
                “The single best thing I’ve done for my trading — finally a system where every decision is tracked and reviewed.”
                <cite>— Maria, swing trader</cite>
              </div>
            </div>
          </div>

          <div className="footer-links" style={{ display: 'flex', flexWrap: 'wrap', gap: '10px', marginTop: '24px' }}>
            <Link href="/terms" className="btn">Terms & Conditions</Link>
            <Link href="/refund-policy" className="btn">Refund Policy</Link>
            <Link href="/pricing" className="btn btn-b">Pricing</Link>
          </div>
        </div>
      </main>
    </>
  );
}

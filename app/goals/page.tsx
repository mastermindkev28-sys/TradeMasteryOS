import Sidebar from '@/components/Sidebar';

export default function GoalsPage() {
  return (
    <>
      <Sidebar />
      <main className="main">
        <div className="page active">
          <div className="ph">
            <div className="ph-left">
              <div className="ph-title">🎯 Goals & Progress Tracker</div>
              <div className="ph-sub">Q2 2025 · 3 active goals · 1 completed</div>
            </div>
            <div className="ph-actions">
              <button className="btn btn-g"><i className="fa-solid fa-plus"></i> Add Goal</button>
            </div>
          </div>

          <div className="goal-card">
            <div className="goal-head">
              <div className="goal-icon" style={{ background: 'var(--gbg)' }}>💰</div>
              <div>
                <div className="goal-title">Achieve $10,000 Net P&L by June 30</div>
                <div className="goal-due">Due: Jun 30, 2025 · SMART Financial Goal</div>
              </div>
              <span className="tag ta" style={{ marginLeft: 'auto' }}>In Progress</span>
            </div>
            <div className="goal-prog-txt"><span style={{ color: 'var(--t2)' }}>$8,420 / $10,000</span><span style={{ color: 'var(--green)' }}>84%</span></div>
            <div className="prog-bg"><div className="prog-fill" style={{ width: '84%', background: 'var(--green)' }}></div></div>
            <div className="goal-note">$1,580 remaining · ~11 trading days · Need avg +$143/day</div>
          </div>

          <div className="goal-card">
            <div className="goal-head">
              <div className="goal-icon" style={{ background: 'var(--bbg)' }}>📈</div>
              <div>
                <div className="goal-title">Maintain 60%+ Win Rate for Full Quarter</div>
                <div className="goal-due">Due: Jun 30, 2025 · Performance Consistency Goal</div>
              </div>
              <span className="tag tg" style={{ marginLeft: 'auto' }}>On Track</span>
            </div>
            <div className="goal-prog-txt"><span style={{ color: 'var(--t2)' }}>Current: 64.2% · Target: 60%+</span><span style={{ color: 'var(--blue)' }}>Exceeding ✓</span></div>
            <div className="prog-bg"><div className="prog-fill" style={{ width: '100%', background: 'var(--blue)' }}></div></div>
            <div className="goal-note">Exceeding target by 4.2% — don&apos;t change what&apos;s working</div>
          </div>

          <div className="goal-card">
            <div className="goal-head">
              <div className="goal-icon" style={{ background: 'var(--pbg)' }}>🧠</div>
              <div>
                <div className="goal-title">Log Every Trade for 60 Consecutive Days</div>
                <div className="goal-due">Started: Apr 19, 2025 · Discipline & Habit Goal</div>
              </div>
              <span className="tag tg" style={{ marginLeft: 'auto' }}>✓ COMPLETED</span>
            </div>
            <div className="goal-prog-txt"><span style={{ color: 'var(--t2)' }}>60/60 days · 100% streak</span><span style={{ color: 'var(--purple)' }}>100%</span></div>
            <div className="prog-bg"><div className="prog-fill" style={{ width: '100%', background: 'var(--purple)' }}></div></div>
            <div style={{ fontSize: '11px', color: 'var(--green)', marginTop: '7px' }}>🏆 MILESTONE ACHIEVED Jun 18. Now targeting 90-day streak.</div>
          </div>

          <div className="card">
            <div className="card-title"><i className="fa-solid fa-graduation-cap"></i> Skill Development Log</div>
            <div className="g2" style={{ marginBottom: 0 }}>
              <div>
                <div style={{ fontSize: '10px', color: 'var(--t3)', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '.08em', marginBottom: '10px' }}>Technical Skills</div>
                <div className="prog-row"><div className="prog-labels"><span>Reading Price Action</span><span style={{ color: 'var(--green)' }}>Advanced</span></div><div className="prog-bg"><div className="prog-fill" style={{ width: '85%', background: 'var(--green)' }}></div></div></div>
                <div className="prog-row"><div className="prog-labels"><span>Volume Analysis</span><span style={{ color: 'var(--blue)' }}>Proficient</span></div><div className="prog-bg"><div className="prog-fill" style={{ width: '70%', background: 'var(--blue)' }}></div></div></div>
                <div className="prog-row"><div className="prog-labels"><span>Options Basics</span><span style={{ color: 'var(--amber)' }}>Learning</span></div><div className="prog-bg"><div className="prog-fill" style={{ width: '35%', background: 'var(--amber)' }}></div></div></div>
                <div className="prog-row"><div className="prog-labels"><span>Futures / /ES</span><span style={{ color: 'var(--t3)' }}>Beginner</span></div><div className="prog-bg"><div className="prog-fill" style={{ width: '15%', background: 'var(--t3)' }}></div></div></div>
              </div>
              <div>
                <div style={{ fontSize: '10px', color: 'var(--t3)', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '.08em', marginBottom: '10px' }}>Psychology Skills</div>
                <div className="prog-row"><div className="prog-labels"><span>Emotional Control</span><span style={{ color: 'var(--green)' }}>Strong</span></div><div className="prog-bg"><div className="prog-fill" style={{ width: '80%', background: 'var(--green)' }}></div></div></div>
                <div className="prog-row"><div className="prog-labels"><span>Patience / Selectivity</span><span style={{ color: 'var(--blue)' }}>Good</span></div><div className="prog-bg"><div className="prog-fill" style={{ width: '72%', background: 'var(--blue)' }}></div></div></div>
                <div className="prog-row"><div className="prog-labels"><span>Letting Winners Run</span><span style={{ color: 'var(--amber)' }}>Developing</span></div><div className="prog-bg"><div className="prog-fill" style={{ width: '45%', background: 'var(--amber)' }}></div></div></div>
                <div className="prog-row"><div className="prog-labels"><span>Position Sizing Discipline</span><span style={{ color: 'var(--green)' }}>Strong</span></div><div className="prog-bg"><div className="prog-fill" style={{ width: '82%', background: 'var(--green)' }}></div></div></div>
              </div>
            </div>
          </div>
        </div>
      </main>
    </>
  );
}

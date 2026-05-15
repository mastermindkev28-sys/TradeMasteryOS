'use client';

import { useEffect, useState } from 'react';
import Sidebar from '@/components/Sidebar';
import TradeForm from '@/components/TradeForm';
import TradeTable from '@/components/TradeTable';
import AuthGuard from '@/components/AuthGuard';
import { useSupabaseAuth } from '@/components/useSupabaseAuth';
import { Trade } from '@/types/trade';
import { supabase } from '@/lib/supabaseClient';

export default function DatabasePage() {
  const { session, loading: authLoading } = useSupabaseAuth();
  const [trades, setTrades] = useState<Trade[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchTrades = async () => {
    if (!session?.user?.id) return;
    setLoading(true);
    const { data, error: fetchError } = await supabase
      .from('trades')
      .select('*')
      .eq('user_id', session.user.id)
      .order('date', { ascending: false });

    if (fetchError) {
      console.error(fetchError);
      setError(fetchError.message);
    } else if (data) {
      setTrades(data);
      setError(null);
    }
    setLoading(false);
  };

  useEffect(() => {
    if (session?.user?.id) {
      fetchTrades();
    }
  }, [session]);

  return (
    <AuthGuard>
      <Sidebar />
      <main className="main">
        <div className="page active">
          <div className="ph">
            <div className="ph-left">
              <div className="ph-title">🗃️ Master Trade Database</div>
              <div className="ph-sub">Live trade storage with Supabase · {trades.length} saved trades</div>
            </div>
            <div className="ph-actions">
              <button className="btn"><i className="fa-solid fa-filter"></i> Filter</button>
              <button className="btn btn-g" onClick={() => document.getElementById('trade-form')?.scrollIntoView({ behavior: 'smooth' })}>
                <i className="fa-solid fa-plus"></i> Add Trade
              </button>
            </div>
          </div>

          {error && (
            <div className="callout co-r">
              <i className="fa-solid fa-circle-exclamation"></i>
              <div>
                <div className="co-title">Unable to load trades</div>
                <div className="co-body">{error}</div>
              </div>
            </div>
          )}

          {session?.user?.id && <TradeForm userId={session.user.id} onCreated={fetchTrades} />}

          <div className="card" style={{ padding: '16px 16px 4px', overflowX: 'auto' }}>
            <TradeTable trades={trades} loading={loading} />
          </div>
        </div>
      </main>
    </AuthGuard>
  );
}

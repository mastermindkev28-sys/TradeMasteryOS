'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useSupabaseAuth } from '@/components/useSupabaseAuth';
import { supabase } from '@/lib/supabaseClient';

interface SubscriptionData {
  status: string;
  current_period_end: string | null;
}

export default function SubscriptionGuard({ children }: { children: React.ReactNode }) {
  const { session, loading: authLoading } = useSupabaseAuth();
  const router = useRouter();
  const [subscription, setSubscription] = useState<SubscriptionData | null>(null);
  const [subLoading, setSubLoading] = useState(true);

  useEffect(() => {
    if (authLoading) return;

    if (!session) {
      setSubLoading(false);
      return;
    }

    const fetchSubscription = async () => {
      const { data, error } = await supabase
        .from('subscriptions')
        .select('status, current_period_end')
        .eq('user_id', session.user.id)
        .single();

      if (!error && data) {
        setSubscription(data as SubscriptionData);
      } else {
        setSubscription(null);
      }
      setSubLoading(false);
    };

    fetchSubscription();
  }, [session, authLoading]);

  useEffect(() => {
    if (!authLoading && !subLoading) {
      const isActive = subscription?.status === 'active';
      if (!isActive) {
        router.replace('/pricing');
      }
    }
  }, [authLoading, subLoading, subscription, router]);

  if (authLoading || subLoading) {
    return (
      <div style={{ minHeight: '100vh', display: 'grid', placeItems: 'center', color: 'var(--t2)' }}>
        Checking subscription…
      </div>
    );
  }

  if (subscription?.status !== 'active') {
    return null;
  }

  return <>{children}</>;
}

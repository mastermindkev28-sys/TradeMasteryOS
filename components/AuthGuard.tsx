'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useSupabaseAuth } from '@/components/useSupabaseAuth';

export default function AuthGuard({ children }: { children: React.ReactNode }) {
  const { session, loading } = useSupabaseAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !session) {
      router.replace('/login');
    }
  }, [loading, session, router]);

  if (loading) {
    return (
      <main className="main" style={{ minHeight: '100vh', display: 'grid', placeItems: 'center', color: 'var(--t2)' }}>
        <div>Checking authentication…</div>
      </main>
    );
  }

  return <>{session ? children : null}</>;
}

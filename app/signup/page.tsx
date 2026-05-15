'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { supabase } from '@/lib/supabaseClient';
import { useSupabaseAuth } from '@/components/useSupabaseAuth';

export default function SignupPage() {
  const { session, loading } = useSupabaseAuth();
  const router = useRouter();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loadingSubmit, setLoadingSubmit] = useState(false);
  const [message, setMessage] = useState('');

  useEffect(() => {
    if (!loading && session) {
      router.replace('/dashboard');
    }
  }, [loading, session, router]);

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError('');
    setMessage('');
    setLoadingSubmit(true);

    const { error } = await supabase.auth.signUp({
      email,
      password,
    });

    setLoadingSubmit(false);

    if (error) {
      setError(error.message);
      return;
    }

    setMessage('Account created. Check your email to confirm, then sign in.');
    setEmail('');
    setPassword('');
  };

  return (
    <main className="main" style={{ minHeight: '100vh', display: 'grid', placeItems: 'center' }}>
      <div className="card" style={{ maxWidth: '420px', width: '100%' }}>
        <div className="card-title"><i className="fa-solid fa-user-plus"></i> Create Account</div>
        <p style={{ color: 'var(--t2)', marginBottom: '18px' }}>
          Create your private trading journal and keep your trades secure.
        </p>
        <form onSubmit={handleSubmit} style={{ display: 'grid', gap: '14px' }}>
          <label>
            <div className="stat-label">Email</div>
            <input
              className="trade-input"
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              required
            />
          </label>
          <label>
            <div className="stat-label">Password</div>
            <input
              className="trade-input"
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              required
            />
          </label>
          <button type="submit" className="btn btn-g" disabled={loadingSubmit}>
            {loadingSubmit ? 'Creating account…' : 'Create Account'}
          </button>
          {error && <div className="callout co-r" style={{ margin: 0 }}>{error}</div>}
          {message && <div className="callout co-b" style={{ margin: 0 }}>{message}</div>}
        </form>
        <div style={{ marginTop: '18px', color: 'var(--t2)' }}>
          Already a member? <Link href="/login">Sign in</Link>.
        </div>
      </div>
    </main>
  );
}

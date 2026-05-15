'use client';

import { useRouter } from 'next/navigation';
import { supabase } from '@/lib/supabaseClient';

export default function SignOutButton() {
  const router = useRouter();

  const handleSignOut = async () => {
    await supabase.auth.signOut();
    router.replace('/login');
  };

  return (
    <button className="nav-btn" type="button" onClick={handleSignOut}>
      <i className="fa-solid fa-right-from-bracket"></i> Sign Out
    </button>
  );
}

import { createClient } from '@supabase/supabase-js';

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

const nullResponse = {
  data: null,
  error: { message: 'Missing NEXT_PUBLIC_SUPABASE_URL or NEXT_PUBLIC_SUPABASE_ANON_KEY' },
};

const createMock = () => {
  const chain: any = {
    select: async () => nullResponse,
    insert: async () => nullResponse,
    order: () => chain,
    limit: () => chain,
  };
  return chain;
};

const mockAuth = {
  getSession: async () => ({ data: { session: null }, error: null }),
  onAuthStateChange: (_event: unknown, _cb: unknown) => ({
    data: { subscription: { unsubscribe: () => {} } },
  }),
  signInWithPassword: async () => nullResponse,
  signUp: async () => nullResponse,
  signOut: async () => ({ error: null }),
};

export const supabase =
  supabaseUrl && supabaseAnonKey
    ? createClient(supabaseUrl, supabaseAnonKey)
    : ({ from: () => createMock(), auth: mockAuth } as any);

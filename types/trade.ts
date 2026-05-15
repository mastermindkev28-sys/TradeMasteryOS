export type Trade = {
  id: string;
  created_at: string | null;
  user_id?: string;
  date: string;
  symbol: string;
  direction: 'LONG' | 'SHORT';
  setup: string;
  entry_price: number;
  exit_price: number;
  stop_price: number;
  profit_loss: number;
  r_multiple: number;
  outcome: 'W' | 'L';
  emotion: string;
  notes: string;
};

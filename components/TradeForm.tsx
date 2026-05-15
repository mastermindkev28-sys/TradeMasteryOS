'use client';

import { useState } from 'react';
import { supabase } from '@/lib/supabaseClient';

type TradeFormProps = {
  userId: string;
  onCreated: () => void;
};

const initialData = {
  date: new Date().toISOString().slice(0, 10),
  symbol: '',
  direction: 'LONG',
  setup: '',
  entry_price: '',
  exit_price: '',
  stop_price: '',
  outcome: 'W',
  emotion: '',
  notes: '',
};

export default function TradeForm({ userId, onCreated }: TradeFormProps) {
  const [data, setData] = useState(initialData);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const handleChange = (field: string, value: string) => {
    setData((prev) => ({ ...prev, [field]: value }));
  };

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSaving(true);
    setMessage(null);

    const entryPrice = Number(data.entry_price);
    const exitPrice = Number(data.exit_price);
    const stopPrice = Number(data.stop_price);
    const profitLoss = data.direction === 'LONG' ? exitPrice - entryPrice : entryPrice - exitPrice;
    const risk = data.direction === 'LONG' ? entryPrice - stopPrice : stopPrice - entryPrice;
    const rMultiple = risk !== 0 ? profitLoss / risk : 0;

    const { error } = await supabase.from('trades').insert([{
      user_id: userId,
      date: data.date,
      symbol: data.symbol.trim().toUpperCase(),
      direction: data.direction,
      setup: data.setup.trim(),
      entry_price: entryPrice,
      exit_price: exitPrice,
      stop_price: stopPrice,
      profit_loss: profitLoss,
      r_multiple: Number(rMultiple.toFixed(2)),
      outcome: data.outcome,
      emotion: data.emotion.trim(),
      notes: data.notes.trim(),
    }]);

    setSaving(false);

    if (error) {
      setMessage(error.message);
      console.error(error);
      return;
    }

    setMessage('Trade saved successfully.');
    setData(initialData);
    onCreated();
  };

  return (
    <div className="card" id="trade-form" style={{ marginBottom: '18px' }}>
      <div className="card-title"><i className="fa-solid fa-plus"></i> Add Trade</div>
      <form onSubmit={handleSubmit} style={{ display: 'grid', gap: '14px' }}>
        <div className="g3">
          <label>
            <div className="stat-label">Date</div>
            <input
              className="trade-input"
              type="date"
              value={data.date}
              onChange={(event) => handleChange('date', event.target.value)}
              required
            />
          </label>
          <label>
            <div className="stat-label">Symbol</div>
            <input
              className="trade-input"
              type="text"
              value={data.symbol}
              onChange={(event) => handleChange('symbol', event.target.value)}
              placeholder="NVDA"
              required
            />
          </label>
          <label>
            <div className="stat-label">Direction</div>
            <select className="trade-input" value={data.direction} onChange={(event) => handleChange('direction', event.target.value)}>
              <option value="LONG">LONG</option>
              <option value="SHORT">SHORT</option>
            </select>
          </label>
        </div>

        <div className="g3">
          <label>
            <div className="stat-label">Setup</div>
            <input
              className="trade-input"
              type="text"
              value={data.setup}
              onChange={(event) => handleChange('setup', event.target.value)}
              placeholder="Bull Flag"
              required
            />
          </label>
          <label>
            <div className="stat-label">Entry Price</div>
            <input
              className="trade-input"
              type="number"
              step="0.01"
              value={data.entry_price}
              onChange={(event) => handleChange('entry_price', event.target.value)}
              required
            />
          </label>
          <label>
            <div className="stat-label">Exit Price</div>
            <input
              className="trade-input"
              type="number"
              step="0.01"
              value={data.exit_price}
              onChange={(event) => handleChange('exit_price', event.target.value)}
              required
            />
          </label>
        </div>

        <div className="g3">
          <label>
            <div className="stat-label">Stop Price</div>
            <input
              className="trade-input"
              type="number"
              step="0.01"
              value={data.stop_price}
              onChange={(event) => handleChange('stop_price', event.target.value)}
              required
            />
          </label>
          <label>
            <div className="stat-label">Outcome</div>
            <select className="trade-input" value={data.outcome} onChange={(event) => handleChange('outcome', event.target.value)}>
              <option value="W">W</option>
              <option value="L">L</option>
            </select>
          </label>
          <label>
            <div className="stat-label">Emotion</div>
            <input
              className="trade-input"
              type="text"
              value={data.emotion}
              onChange={(event) => handleChange('emotion', event.target.value)}
              placeholder="Calm"
            />
          </label>
        </div>

        <label>
          <div className="stat-label">Notes</div>
          <textarea
            className="trade-input"
            rows={4}
            value={data.notes}
            onChange={(event) => handleChange('notes', event.target.value)}
            placeholder="Entry thesis, plan adherence, follow-up notes"
          />
        </label>

        <div style={{ display: 'flex', justifyContent: 'space-between', gap: '10px', flexWrap: 'wrap' }}>
          <button type="submit" className="btn btn-g" disabled={saving}>
            {saving ? 'Saving...' : 'Save Trade'}
          </button>
          {message && <span style={{ color: 'var(--t2)', fontSize: '12px', alignSelf: 'center' }}>{message}</span>}
        </div>
      </form>
    </div>
  );
}

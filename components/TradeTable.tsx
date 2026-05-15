'use client';

import { Trade } from '@/types/trade';

type TradeTableProps = {
  trades: Trade[];
  loading: boolean;
};

function formatDollar(value: number) {
  return value >= 0 ? `+$${value.toFixed(0)}` : `-$${Math.abs(value).toFixed(0)}`;
}

export default function TradeTable({ trades, loading }: TradeTableProps) {
  return (
    <table className="trade-table" style={{ minWidth: '620px' }}>
      <thead>
        <tr>
          <th>Date</th>
          <th>Symbol</th>
          <th>Direction</th>
          <th>Setup</th>
          <th>Entry / Exit</th>
          <th>P&L $</th>
          <th>R-Multiple</th>
          <th>W/L</th>
          <th>Emotion</th>
        </tr>
      </thead>
      <tbody>
        {trades.map((trade) => (
          <tr key={trade.id}>
            <td className="mono" style={{ color: 'var(--t3)' }}>
              {new Date(trade.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
            </td>
            <td><strong>{trade.symbol}</strong></td>
            <td>
              <span className={`tag ${trade.direction === 'LONG' ? 'tg' : 'tr'}`} style={{ fontSize: '9px' }}>
                {trade.direction}
              </span>
            </td>
            <td style={{ fontSize: '11px', color: 'var(--t2)' }}>{trade.setup}</td>
            <td className="mono">{trade.entry_price.toFixed(2)} / {trade.exit_price.toFixed(2)}</td>
            <td className="mono" style={{ color: trade.profit_loss >= 0 ? 'var(--green)' : 'var(--red)', fontWeight: 700 }}>
              {formatDollar(trade.profit_loss)}
            </td>
            <td className="mono" style={{ color: trade.r_multiple >= 0 ? 'var(--green)' : 'var(--red)' }}>
              {trade.r_multiple.toFixed(2)}R
            </td>
            <td>
              <span className={`tag ${trade.outcome === 'W' ? 'tg' : 'tr'}`} style={{ fontSize: '9px' }}>
                {trade.outcome}
              </span>
            </td>
            <td style={{ fontSize: '11px' }}>{trade.emotion}</td>
          </tr>
        ))}
        {!trades.length && !loading && (
          <tr>
            <td colSpan={9} style={{ padding: '14px 0', color: 'var(--t2)' }}>
              No trades found. Add your first trade using the form above.
            </td>
          </tr>
        )}
        {loading && (
          <tr>
            <td colSpan={9} style={{ padding: '14px 0', color: 'var(--t2)' }}>
              Loading trades...
            </td>
          </tr>
        )}
      </tbody>
    </table>
  );
}

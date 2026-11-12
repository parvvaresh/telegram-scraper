import { createContext, useCallback, useContext, useState } from 'react';
import { STATUS, fa } from '../lib';

export function Pill({ status, children }) {
  return <span className={`pill ${status || ''}`}>{children ?? STATUS[status] ?? status ?? '—'}</span>;
}

export function Kpi({ value, label, tone = '', small = false }) {
  return (
    <div className={`kpi ${tone}`}>
      <div className={`v ${small ? 'sm' : ''}`}>{value}</div>
      <div className="l">{label}</div>
    </div>
  );
}

export function Progress({ done, total, finished, label, right }) {
  const pct = total ? Math.min(100, (done / total) * 100) : 0;
  return (
    <div>
      {(label || right !== undefined) && (
        <div className="progress-label">
          <span>{label}</span>
          <span>{right ?? (total ? `${pct.toFixed(1)}٪` : '')}</span>
        </div>
      )}
      <div className={`progress ${finished ? 'done' : ''}`}>
        <div style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

export function Banner({ tone = 'info', children }) {
  return <div className={`banner ${tone}`}>{children}</div>;
}

export function Empty({ children }) {
  return <div className="empty">{children}</div>;
}

/** Single-series bar chart (posts per day) with hover tooltip and a table fallback. */
export function DailyChart({ rows, days = 14 }) {
  const [tip, setTip] = useState(null);
  const map = Object.fromEntries((rows || []).map(r => [r.day, Number(r.posts)]));
  const list = [];
  for (let i = days - 1; i >= 0; i--) {
    const d = new Date();
    d.setDate(d.getDate() - i);
    list.push(d.toISOString().slice(0, 10));
  }
  const max = Math.max(1, ...list.map(d => map[d] || 0));
  return (
    <div>
      <div className="chart" onMouseLeave={() => setTip(null)}>
        {list.map(d => (
          <div
            key={d}
            className="col"
            onMouseMove={e => setTip({ x: e.clientX, y: e.clientY, text: `${d}: ${fa(map[d] || 0)} پست` })}
          >
            <div className="b" style={{ height: `${((map[d] || 0) / max) * 100}%` }} />
          </div>
        ))}
      </div>
      <div className="chart-x">
        {list.map((d, i) => <span key={d}>{i % 2 ? '' : d.slice(5)}</span>)}
      </div>
      {tip && <div className="tip" style={{ left: tip.x + 12, top: tip.y - 34 }}>{tip.text}</div>}
      <details style={{ marginTop: 8 }}>
        <summary>جدول</summary>
        <table>
          <thead><tr><th>روز</th><th className="num">پست</th></tr></thead>
          <tbody>{list.map(d => <tr key={d}><td className="ltr">{d}</td><td className="num">{fa(map[d] || 0)}</td></tr>)}</tbody>
        </table>
      </details>
    </div>
  );
}

const ToastCtx = createContext(() => {});
export const useToast = () => useContext(ToastCtx);

export function ToastProvider({ children }) {
  const [toast, setToast] = useState(null);
  const show = useCallback((msg, err = false) => {
    const id = Date.now();
    setToast({ msg, err, id });
    setTimeout(() => setToast(t => (t && t.id === id ? null : t)), 3500);
  }, []);
  return (
    <ToastCtx.Provider value={show}>
      {children}
      {toast && <div className={`toast ${toast.err ? 'err' : ''}`}>{toast.msg}</div>}
    </ToastCtx.Provider>
  );
}

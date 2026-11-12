import { useEffect, useMemo, useState } from 'react';
import { api, fa, go, normalizeChannel } from '../lib';
import { useToast } from '../components/ui';

export default function Channels() {
  const toast = useToast();
  const [text, setText] = useState('');
  const [saved, setSaved] = useState('');

  async function load() {
    try {
      const d = await api('/api/channels');
      const t = d.channels.join('\n');
      setText(t);
      setSaved(t);
    } catch (e) {
      toast(e.message, true);
    }
  }
  useEffect(() => { load(); }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const { names, dup } = useMemo(() => {
    const seen = new Set();
    const out = [];
    let d = 0;
    for (const line of text.split('\n')) {
      const n = normalizeChannel(line);
      if (!n) continue;
      if (seen.has(n.toLowerCase())) { d++; continue; }
      seen.add(n.toLowerCase());
      out.push(n);
    }
    return { names: out, dup: d };
  }, [text]);

  async function save() {
    try {
      const d = await api('/api/channels', { method: 'PUT', body: { channels: text.split('\n') } });
      const t = d.channels.join('\n');
      setText(t);
      setSaved(t);
      toast(`${fa(d.channels.length)} کانال ذخیره شد`);
    } catch (e) {
      toast(e.message, true);
    }
  }

  return (
    <div>
      <div className="page-title"><h2>کانال‌ها</h2></div>
      <div className="grid g2">
        <div className="card">
          <h2>لیست کانال‌ها <span className="muted small">(input/channels.json)</span></h2>
          <p className="small muted" style={{ marginTop: 0 }}>
            هر خط یک کانال: لینک <code>https://t.me/name</code>، <code>@name</code> یا فقط <code>name</code>. تکراری‌ها و خطوط خالی هنگام ذخیره حذف می‌شوند.
          </p>
          <textarea rows={18} className="ltr mono" value={text} onChange={e => setText(e.target.value)} />
          <div className="row" style={{ marginTop: 10 }}>
            <button className="btn primary" onClick={save} disabled={text === saved}>ذخیره</button>
            <button className="btn" onClick={load}>بازخوانی</button>
            {text !== saved && <span className="small" style={{ color: 'var(--warn)' }}>تغییرات ذخیره نشده</span>}
            <div className="spacer" />
            <span className="small muted">{fa(names.length)} کانال{dup ? ` · ${fa(dup)} تکراری` : ''}</span>
          </div>
        </div>
        <div className="card">
          <h2>نام‌های نرمال‌شده</h2>
          <p className="small muted" style={{ marginTop: 0 }}>
            این همان نامی است که اسکرپر استفاده می‌کند. با «پیش‌نمایش» صفحهٔ اول کانال را همان‌طور که اسکرپر می‌بیند ببینید.
          </p>
          <div className="table-wrap scroll">
            <table>
              <thead><tr><th>#</th><th>کانال</th><th /></tr></thead>
              <tbody>
                {names.map((n, i) => (
                  <tr key={n}>
                    <td className="muted">{fa(i + 1)}</td>
                    <td className="ltr">@{n}</td>
                    <td style={{ textAlign: 'end' }}>
                      <button className="link small" onClick={() => go(`preview/${encodeURIComponent(n)}`)}>پیش‌نمایش</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}

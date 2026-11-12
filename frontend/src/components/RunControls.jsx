import { useEffect, useState } from 'react';
import { api, go } from '../lib';
import { useToast } from './ui';

/** Start / stop a run. `running` comes from the parent's polling. */
export default function RunControls({ running, onChange, compact = false }) {
  const toast = useToast();
  const [mode, setMode] = useState('all');
  const [days, setDays] = useState('');
  const [limit, setLimit] = useState('');
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api('/api/settings')
      .then(d => { setDays(d.settings.posts.days); setLimit(d.settings.comments.limit); })
      .catch(() => {});
  }, []);

  async function start() {
    setBusy(true);
    try {
      if (mode !== 'comments') {
        const ch = await api('/api/channels');
        if (!ch.channels.length) throw new Error('لیست کانال‌ها خالی است');
      }
      await api('/api/run', { method: 'POST', body: { mode, days: Number(days) || null, limit: Number(limit) || null } });
      toast('اجرا شروع شد');
      onChange?.();
      go('run');
    } catch (e) {
      toast(e.message, true);
    } finally {
      setBusy(false);
    }
  }

  async function stop() {
    setBusy(true);
    try {
      await api('/api/stop', { method: 'POST' });
      toast('درخواست توقف ارسال شد');
      onChange?.();
    } catch (e) {
      toast(e.message, true);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="card">
      {!compact && <h2>اجرای جدید</h2>}
      <div className="row" style={{ alignItems: 'flex-end' }}>
        <label className="field" style={{ width: 230 }}>حالت اجرا
          <select value={mode} onChange={e => setMode(e.target.value)} disabled={running}>
            <option value="all">کامل: پست‌ها ← کامنت و ری‌اکشن</option>
            <option value="posts">فقط پست‌ها (HTTP)</option>
            <option value="comments">فقط کامنت و ری‌اکشن (Telethon)</option>
          </select>
        </label>
        <label className="field" style={{ width: 110 }}>چند روز اخیر
          <input type="number" min="1" value={days} onChange={e => setDays(e.target.value)} disabled={running || mode === 'comments'} />
        </label>
        <label className="field" style={{ width: 130 }}>سقف کامنت هر پست
          <input type="number" min="1" value={limit} onChange={e => setLimit(e.target.value)} disabled={running || mode === 'posts'} />
        </label>
        <button className="btn primary" onClick={start} disabled={running || busy}>▶ شروع اجرا</button>
        <button className="btn danger" onClick={stop} disabled={!running || busy}>■ توقف</button>
      </div>
      {!compact && (
        <div className="small muted" style={{ marginTop: 8 }}>
          با شروع فاز پست‌ها، فایل‌های قدیمی <code>output/batches/batch_*.json</code> پاک می‌شوند تا فاز کامنت فقط پست‌های همین اجرا را پردازش کند.
        </div>
      )}
    </div>
  );
}

import { useMemo, useState } from 'react';
import { MODE, STATUS, api, duration, fa, fmtTime, go, usePoll } from '../lib';
import { Empty, Kpi, Pill } from '../components/ui';

export default function History() {
  const { data: runs } = usePoll(() => api('/api/runs?limit=200'), 5000);
  const [status, setStatus] = useState('');
  const [mode, setMode] = useState('');

  const list = useMemo(
    () => (runs || []).filter(r => (!status || r.status === status) && (!mode || r.mode === mode)),
    [runs, status, mode],
  );

  const totals = useMemo(() => {
    const t = { runs: list.length, done: 0, failed: 0, posts: 0, comments: 0, secs: 0, finished: 0 };
    for (const r of list) {
      if (r.status === 'done') t.done++;
      if (['failed', 'interrupted'].includes(r.status)) t.failed++;
      t.posts += r.summary?.posts_fetched || 0;
      t.comments += r.summary?.inserted?.telegram_comments || 0;
      if (r.finished_at) { t.secs += (new Date(r.finished_at) - new Date(r.started_at)) / 1000; t.finished++; }
    }
    return t;
  }, [list]);

  return (
    <div>
      <div className="page-title">
        <h2>تاریخچهٔ اجراها</h2>
        <div className="spacer" />
        <select style={{ width: 'auto' }} value={status} onChange={e => setStatus(e.target.value)}>
          <option value="">همهٔ وضعیت‌ها</option>
          {['running', 'done', 'failed', 'stopped', 'interrupted'].map(s => <option key={s} value={s}>{STATUS[s]}</option>)}
        </select>
        <select style={{ width: 'auto' }} value={mode} onChange={e => setMode(e.target.value)}>
          <option value="">همهٔ حالت‌ها</option>
          {Object.entries(MODE).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
        </select>
      </div>

      <div className="card">
        <div className="kpis">
          <Kpi value={fa(totals.runs)} label="اجرا" />
          <Kpi value={fa(totals.done)} label="موفق" tone="good" />
          <Kpi value={fa(totals.failed)} label="ناموفق / قطع‌شده" tone={totals.failed ? 'bad' : ''} />
          <Kpi value={fa(totals.posts)} label="مجموع پست پیدا شده" />
          <Kpi value={fa(totals.comments)} label="مجموع کامنت درج‌شده" />
          <Kpi value={totals.finished ? duration('1970-01-01T00:00:00Z', new Date(totals.secs * 1000 / totals.finished)) : '—'} label="میانگین مدت" />
        </div>
      </div>

      <div className="card">
        {!runs ? <Empty>…</Empty> : !list.length ? <Empty>اجرایی پیدا نشد</Empty> : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>شناسه</th><th>شروع</th><th>حالت</th><th>وضعیت</th><th>مدت</th><th>پارامترها</th>
                  <th className="num">کانال ✓/✗</th><th className="num">پست</th><th className="num">کامنت</th>
                  <th className="num">ری‌اکشن</th><th className="num">خطا</th>
                </tr>
              </thead>
              <tbody>
                {list.map(r => {
                  const s = r.summary || {};
                  return (
                    <tr key={r.id} className="clickable" onClick={() => go(`run/${r.id}`)}>
                      <td className="ltr mono small">{r.id}</td>
                      <td className="small">{fmtTime(r.started_at)}</td>
                      <td className="small">{MODE[r.mode] || r.mode}</td>
                      <td><Pill status={r.status} /></td>
                      <td className="ltr small">{duration(r.started_at, r.finished_at)}</td>
                      <td className="small muted">
                        {r.mode !== 'comments' && `${fa(r.params.days)} روز`}
                        {r.mode === 'all' && ' · '}
                        {r.mode !== 'posts' && `${fa(r.params.limit)} کامنت`}
                      </td>
                      <td className="num">{s.channels_done != null ? `${fa(s.channels_done)} / ${fa(s.channels_failed)}` : '—'}</td>
                      <td className="num">{s.posts_fetched != null ? fa(s.posts_fetched) : '—'}</td>
                      <td className="num">{s.inserted ? fa(s.inserted.telegram_comments || 0) : '—'}</td>
                      <td className="num">{s.inserted ? fa(s.inserted.telegram_reactions || 0) : '—'}</td>
                      <td className="num" style={{ color: s.errors ? 'var(--bad)' : undefined }}>{s.errors != null ? fa(s.errors) : '—'}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
        <div className="small muted" style={{ marginTop: 10 }}>
          لاگ هر اجرا در <code>logs/runs/&lt;شناسه&gt;/</code> ذخیره می‌شود. آمار ستون‌ها هنگام پایان اجرا ثبت می‌شود.
        </div>
      </div>
    </div>
  );
}

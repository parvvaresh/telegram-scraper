import { MODE, PHASE, api, duration, fa, fmtTime, go, usePoll } from '../lib';
import { Banner, DailyChart, Empty, Kpi, Pill, Progress } from '../components/ui';
import RunControls from '../components/RunControls';

function Check({ ok, optional, children, to }) {
  const cls = ok ? 'ok' : optional ? 'opt' : 'bad';
  return (
    <li>
      <span className={`icon ${cls}`}>{ok ? '✓' : optional ? '–' : '✗'}</span>
      <span className="grow">{children}</span>
      {!ok && to && <a className="small" href={`#/${to}`}>تنظیم</a>}
    </li>
  );
}

function CurrentRun({ summary }) {
  const { data: st } = usePoll(() => api('/api/status'), 3000);
  if (!st?.run) return <div className="card"><h2>آخرین اجرا</h2><Empty>هنوز اجرایی ثبت نشده.</Empty></div>;
  const r = st.run;
  const P = st.progress.posts, C = st.progress.comments;
  const cTotal = C ? C.total_pairs || C.workers.reduce((a, w) => a + w.total, 0) : 0;
  return (
    <div className="card">
      <div className="row" style={{ marginBottom: 12 }}>
        <h2 style={{ margin: 0 }}>{st.running ? 'اجرای فعلی' : 'آخرین اجرا'}</h2>
        <Pill status={r.status} />
        <span className="small muted ltr mono">{r.id}</span>
        <div className="spacer" />
        <a className="btn sm" href={`#/run/${r.id}`}>جزئیات و لاگ ←</a>
      </div>
      <div className="small muted" style={{ marginBottom: 12 }}>
        {MODE[r.mode]} · شروع {fmtTime(r.started_at)} · مدت <bdi className="ltr">{duration(r.started_at, r.finished_at)}</bdi>
      </div>
      <div className="stack">
        {P && (
          <Progress
            done={P.channels_done + P.channels_failed}
            total={P.total_channels}
            finished={r.phases[0].status === 'done'}
            label={`${PHASE.posts}: ${fa(P.channels_done + P.channels_failed)} / ${fa(P.total_channels)} کانال · ${fa(P.posts_fetched)} پست`}
          />
        )}
        {C && (
          <Progress
            done={C.done}
            total={cTotal}
            finished={r.phases.find(p => p.name === 'comments').status === 'done'}
            label={`${PHASE.comments}: ${fa(C.done)} / ${fa(cTotal)} پیام · ${fa(C.inserted.telegram_comments || 0)} کامنت`}
          />
        )}
      </div>
      {summary && !summary.running && r.summary?.errors > 0 && (
        <div className="small" style={{ marginTop: 10, color: 'var(--bad)' }}>{fa(r.summary.errors)} خطا در این اجرا ثبت شد.</div>
      )}
    </div>
  );
}

export default function Dashboard() {
  const { data: s, reload } = usePoll(() => api('/api/summary'), 3000);
  const { data: db, error: dbErr } = usePoll(() => api('/api/db/overview'), 15000);

  const t = db?.totals;
  return (
    <div>
      <div className="page-title"><h2>داشبورد</h2></div>

      <div className="card">
        <div className="kpis">
          <Kpi value={t ? fa(+t.posts) : '—'} label="پست در دیتابیس" />
          <Kpi value={t ? fa(+t.channels) : '—'} label="کانال دارای پست" />
          <Kpi value={t ? fa(+t.comments) : '—'} label="کامنت" />
          <Kpi value={t ? fa(+t.reaction_rows) : '—'} label="ردیف ری‌اکشن" />
          <Kpi value={s ? fa(s.channels) : '—'} label="کانال در لیست ورودی" />
          <Kpi value={s ? fa(s.sessions) : '—'} label="سشن تلگرام" tone={s && !s.sessions ? 'warn' : ''} />
        </div>
        {dbErr && (
          <div className="small" style={{ marginTop: 10, color: 'var(--bad)' }}>
            ClickHouse در دسترس نیست — <a href="#/settings">تنظیمات</a> را بررسی کنید.
          </div>
        )}
      </div>

      <RunControls running={!!s?.running} onChange={reload} compact />

      <div className="grid g2" style={{ marginBottom: 16 }}>
        <CurrentRun summary={s} />
        <div className="card">
          <h2>آمادگی</h2>
          {s ? (
            <ul className="checklist">
              <Check ok={s.channels > 0} to="channels">لیست کانال‌ها ({fa(s.channels)} کانال)</Check>
              <Check ok={!dbErr && !!db} to="settings">اتصال به ClickHouse</Check>
              <Check ok={s.telegram_configured} to="settings">api_id و api_hash تلگرام (برای فاز کامنت)</Check>
              <Check ok={s.sessions > 0} to="settings">فایل سشن تلگرام ({fa(s.sessions)})</Check>
              <Check ok={s.http_proxy} optional>پراکسی HTTP (اختیاری)</Check>
              <Check ok={s.mtproto_proxy} optional>پراکسی MTProto (اختیاری)</Check>
            </ul>
          ) : <Empty>…</Empty>}
        </div>
      </div>

      <div className="grid g2" style={{ marginBottom: 16 }}>
        <div className="card">
          <h2>پست‌ها بر اساس تاریخ انتشار <span className="muted small">(۱۴ روز اخیر)</span></h2>
          {db ? <DailyChart rows={db.daily} /> : <Empty>{dbErr ? 'داده‌ای در دسترس نیست' : '…'}</Empty>}
        </div>
        <div className="card">
          <div className="row" style={{ marginBottom: 12 }}>
            <h2 style={{ margin: 0 }}>اجراهای اخیر</h2>
            <div className="spacer" />
            <a className="small" href="#/history">همهٔ تاریخچه ←</a>
          </div>
          {s?.runs?.length ? (
            <div className="table-wrap">
              <table>
                <thead><tr><th>شروع</th><th>حالت</th><th>وضعیت</th><th>مدت</th><th className="num">پست</th></tr></thead>
                <tbody>
                  {s.runs.slice(0, 6).map(r => (
                    <tr key={r.id} className="clickable" onClick={() => go(`run/${r.id}`)}>
                      <td className="small">{fmtTime(r.started_at)}</td>
                      <td className="small">{MODE[r.mode]}</td>
                      <td><Pill status={r.status} /></td>
                      <td className="ltr small">{duration(r.started_at, r.finished_at)}</td>
                      <td className="num">{r.summary?.posts_fetched != null ? fa(r.summary.posts_fetched) : '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : <Empty>هنوز اجرایی نیست</Empty>}
        </div>
      </div>

      {!s?.settings_saved && s && (
        <Banner>تنظیمات هنوز ذخیره نشده و مقادیر پیش‌فرض استفاده می‌شوند. از صفحهٔ <a href="#/settings">تنظیمات</a> شروع کنید.</Banner>
      )}
    </div>
  );
}

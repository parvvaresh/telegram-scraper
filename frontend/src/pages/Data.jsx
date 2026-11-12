import { useEffect, useState } from 'react';
import { api, fa, normalizeChannel, usePoll } from '../lib';
import { Banner, DailyChart, Empty, Kpi } from '../components/ui';

export function PostCard({ p }) {
  return (
    <div className="post">
      <div className="meta">
        <b className="ltr">@{p.channel}/{p.msgid}</b>
        {p.shdate && <span>{p.shdate}</span>}
        <span>👁 {fa(+p.views)}</span>
        {p.reactions !== undefined && <span>❤ {fa(+p.reactions)}</span>}
        {p.ptype && <span className="ltr">{p.ptype}</span>}
      </div>
      <div className="text">{p.text || <span className="muted">(بدون متن)</span>}</div>
    </div>
  );
}

export default function Data() {
  const [auto, setAuto] = useState(false);
  const [filter, setFilter] = useState('');
  const [debounced, setDebounced] = useState('');
  useEffect(() => {
    const t = setTimeout(() => setDebounced(normalizeChannel(filter) || ''), 400);
    return () => clearTimeout(t);
  }, [filter]);

  const ov = usePoll(() => api('/api/db/overview'), auto ? 10000 : 0, [auto]);
  const chs = usePoll(() => api('/api/db/channels'), auto ? 10000 : 0, [auto]);
  const posts = usePoll(() => api('/api/db/posts?channel=' + encodeURIComponent(debounced)), auto ? 10000 : 0, [auto, debounced]);
  const comments = usePoll(() => api('/api/db/comments?channel=' + encodeURIComponent(debounced)), auto ? 10000 : 0, [auto, debounced]);
  const reloadAll = () => { ov.reload(); chs.reload(); posts.reload(); comments.reload(); };

  const t = ov.data?.totals;
  return (
    <div>
      <div className="page-title">
        <h2>داده‌های ذخیره‌شده در ClickHouse</h2>
        <div className="spacer" />
        <label className="check"><input type="checkbox" checked={auto} onChange={e => setAuto(e.target.checked)} /> بروزرسانی خودکار (۱۰ ثانیه)</label>
        <button className="btn" onClick={reloadAll}>بروزرسانی</button>
      </div>
      {ov.error && (
        <Banner tone="err">
          خواندن از ClickHouse ناموفق بود — <a href="#/settings">تنظیمات ClickHouse</a> را بررسی کنید.
          <div className="ltr small mono" style={{ marginTop: 4 }}>{ov.error.message}</div>
        </Banner>
      )}
      <div className="card">
        <div className="kpis">
          <Kpi value={t ? fa(+t.posts) : '—'} label="پست" />
          <Kpi value={t ? fa(+t.channels) : '—'} label="کانال دارای پست" />
          <Kpi value={t ? fa(+t.comments) : '—'} label="کامنت" />
          <Kpi value={t ? fa(+t.reaction_rows) : '—'} label="ردیف ری‌اکشن" />
          <Kpi value={<span className="ltr">{t?.last_post_insert || '—'}</span>} label="آخرین درج پست" small />
          <Kpi value={<span className="ltr">{t?.last_comment_insert || '—'}</span>} label="آخرین درج کامنت" small />
        </div>
      </div>
      <div className="grid g2" style={{ marginBottom: 16 }}>
        <div className="card">
          <h2>پست‌ها بر اساس تاریخ انتشار <span className="muted small">(۱۴ روز اخیر)</span></h2>
          {ov.data ? <DailyChart rows={ov.data.daily} /> : <Empty>—</Empty>}
        </div>
        <div className="card">
          <h2>پرتکرارترین ری‌اکشن‌ها</h2>
          <div className="chips">
            {ov.data?.top_reactions?.length
              ? ov.data.top_reactions.map(r => <span key={r.reaction} className="chip big">{r.reaction}<b>{fa(+r.count)}</b></span>)
              : <span className="small muted">—</span>}
          </div>
        </div>
      </div>
      <div className="card">
        <h2>کانال‌ها</h2>
        <div className="table-wrap scroll">
          <table>
            <thead><tr><th>کانال</th><th className="num">پست</th><th className="num">بازدید</th><th className="num">ری‌اکشن</th><th className="num">کامنت</th><th>آخرین پست</th></tr></thead>
            <tbody>
              {chs.data?.length ? chs.data.map(c => (
                <tr key={c.channel} className="clickable" onClick={() => setFilter(c.channel)}>
                  <td className="ltr">@{c.channel}</td>
                  <td className="num">{fa(+c.posts)}</td>
                  <td className="num">{fa(+c.views)}</td>
                  <td className="num">{fa(+c.reactions)}</td>
                  <td className="num">{fa(c.comments)}</td>
                  <td className="ltr small">{c.last_post}</td>
                </tr>
              )) : <tr><td colSpan="6"><Empty>داده‌ای نیست</Empty></td></tr>}
            </tbody>
          </table>
        </div>
      </div>
      <div className="grid g2">
        <div className="card">
          <div className="row" style={{ marginBottom: 10 }}>
            <h2 style={{ margin: 0 }}>آخرین پست‌ها</h2>
            <div className="spacer" />
            <input className="ltr" placeholder="فیلتر کانال" style={{ width: 170 }} value={filter} onChange={e => setFilter(e.target.value)} />
          </div>
          <div className="posts">
            {posts.data?.length ? posts.data.map(p => <PostCard key={p.channel + p.msgid} p={p} />) : <Empty>—</Empty>}
          </div>
        </div>
        <div className="card">
          <h2>آخرین کامنت‌ها</h2>
          <div className="posts">
            {comments.data?.length ? comments.data.map(c => (
              <div className="post" key={c.channel + c.msgid + '-' + c.comment_id}>
                <div className="meta">
                  <b className="ltr">@{c.channel}/{c.msgid}</b>
                  <span className="ltr">#{c.comment_id}</span>
                  <span className="ltr">user {c.user_id}</span>
                  <span className="ltr">{c.date}</span>
                  <span>❤ {fa(+c.reactions)}</span>
                </div>
                <div className="text">{c.text}</div>
              </div>
            )) : <Empty>—</Empty>}
          </div>
        </div>
      </div>
    </div>
  );
}

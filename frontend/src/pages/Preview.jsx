import { useEffect, useState } from 'react';
import { api, fa } from '../lib';
import { Banner, Empty, Pill, useToast } from '../components/ui';

function PageResult({ d }) {
  return (
    <div className="card">
      <div className="row small" style={{ marginBottom: 10 }}>
        <Pill status={d.ok ? 'done' : 'failed'}>{d.ok ? `HTTP ${d.status}` : 'خطا'}</Pill>
        <span className="ltr mono">GET {d.url}</span>
        <span className="muted">{fa(d.elapsed_ms)} ms</span>
        {d.bytes ? <span className="muted">{fa(Math.round(d.bytes / 1024))} KB</span> : null}
        <span className="muted">{d.proxy ? 'از طریق پراکسی HTTP' : 'بدون پراکسی'}</span>
        {d.title && <b>{d.title}</b>}
        <div className="spacer" />
        <span>{fa(d.posts?.length || 0)} پست پارس شد</span>
      </div>
      {d.error && <Banner tone="err"><span className="ltr">{d.error}</span></Banner>}
      {d.final_url && d.final_url !== d.url && (
        <Banner tone="err">ریدایرکت به <span className="ltr">{d.final_url}</span> — احتمالاً کانال عمومی نیست یا وجود ندارد.</Banner>
      )}
      {d.posts?.length ? (
        <div className="posts">
          {d.posts.map(p => (
            <div className="post" key={p.msgid}>
              <div className="meta">
                <b className="ltr">#{p.msgid}</b>
                <span>{p.shdate}</span>
                <span className="ltr">{p.date}</span>
                <span>👁 {fa(p.views)}</span>
                <span className="ltr">{p.type}</span>
              </div>
              <div className="text">{p.text || <span className="muted">(بدون متن)</span>}</div>
            </div>
          ))}
        </div>
      ) : d.ok ? <Empty>هیچ پستی در این صفحه پیدا نشد.</Empty> : null}
    </div>
  );
}

export default function Preview({ initial }) {
  const toast = useToast();
  const [input, setInput] = useState(initial || '');
  const [pages, setPages] = useState([]);
  const [loading, setLoading] = useState(false);

  async function fetchPage(channel, before) {
    setLoading(true);
    try {
      const d = await api(`/api/preview?channel=${encodeURIComponent(channel)}${before ? `&before=${before}` : ''}`);
      setPages(prev => (before ? [...prev, d] : [d]));
    } catch (e) {
      toast(e.message, true);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (initial) { setInput(initial); fetchPage(initial); }
  }, [initial]); // eslint-disable-line react-hooks/exhaustive-deps

  const last = pages[pages.length - 1];
  return (
    <div>
      <div className="page-title"><h2>پیش‌نمایش اسکرپ</h2></div>
      <div className="card">
        <p className="small muted" style={{ marginTop: 0 }}>
          دقیقاً همان کاری را می‌کند که فاز ۱ برای هر صفحه انجام می‌دهد (درخواست به <code>t.me/s/</code> با پراکسی HTTP تنظیم‌شده و پارس HTML)،
          ولی <b>چیزی در دیتابیس ذخیره نمی‌کند</b>.
        </p>
        <form className="row" onSubmit={e => { e.preventDefault(); if (input.trim()) fetchPage(input.trim()); }}>
          <input className="ltr grow" style={{ maxWidth: 420 }} placeholder="https://t.me/channel یا @channel" value={input} onChange={e => setInput(e.target.value)} />
          <button className="btn primary" disabled={loading || !input.trim()}>اسکرپ صفحهٔ اول</button>
          <button type="button" className="btn" disabled={loading || !last?.next_before} onClick={() => fetchPage(last.channel, last.next_before)}>
            صفحهٔ قدیمی‌تر ←
          </button>
          {loading && <span className="small muted">در حال دریافت…</span>}
        </form>
      </div>
      {pages.map((d, i) => <PageResult key={i} d={d} />)}
    </div>
  );
}

import { Fragment, useEffect, useRef, useState } from 'react';
import { MODE, PHASE, STATUS, api, duration, fa, fmtTime } from '../lib';
import { Empty, Kpi, Pill, Progress } from './ui';

function PostsPhase({ P, phase, serverTime }) {
  const processed = P.channels_done + P.channels_failed;
  const secs = phase.started_at ? (new Date(phase.finished_at || serverTime) - new Date(phase.started_at)) / 1000 : 0;
  const rate = secs > 5 ? (P.posts_fetched / secs) * 60 : 0;
  return (
    <div className="card">
      <div className="row" style={{ marginBottom: 10 }}>
        <h2 style={{ margin: 0 }}>فاز ۱ — اسکرپ پست‌ها از <span className="ltr">t.me/s/</span></h2>
        <Pill status={phase.status} />
      </div>
      <Progress
        done={processed}
        total={P.total_channels}
        finished={phase.status === 'done'}
        label={`کانال‌ها: ${fa(processed)} از ${fa(P.total_channels)} · بچ‌ها: ${fa(P.batches_done)} از ${fa(P.total_batches)}`}
      />
      <div className="kpis" style={{ marginTop: 14 }}>
        <Kpi value={fa(P.posts_fetched)} label="پست پیدا شده" />
        <Kpi value={fa(Math.round(rate))} label="پست در دقیقه" />
        <Kpi value={fa(P.inserted.telegram_posts || 0)} label="ردیف درج‌شده در DB" />
        <Kpi value={fa(P.channels_done)} label="کانال موفق" />
        <Kpi value={fa(P.channels_failed)} label="کانال ناموفق" tone={P.channels_failed ? 'bad' : ''} />
        <Kpi value={fa(P.http_errors)} label="خطای HTTP" tone={P.http_errors ? 'warn' : ''} />
        <Kpi value={fa(P.insert_errors)} label="خطای درج DB" tone={P.insert_errors ? 'bad' : ''} />
      </div>
      <div className="grid g2" style={{ marginTop: 14 }}>
        <div>
          <h3>در حال اسکرپ (تعداد پست تا این لحظه)</h3>
          <div className="chips">
            {P.active.length ? P.active.map(([c, n]) => <span key={c} className="chip">@{c}<b>{n}</b></span>)
              : <span className="small muted">—</span>}
          </div>
        </div>
        <div>
          <h3>آخرین کانال‌های تمام‌شده</h3>
          <div className="chips">
            {P.recent.length ? P.recent.map(([c, n, ok], i) => (
              <span key={c + i} className={`chip ${ok ? '' : 'bad'}`}>@{c}<b>{ok ? n : '✗'}</b></span>
            )) : <span className="small muted">—</span>}
          </div>
        </div>
      </div>
    </div>
  );
}

function CommentsPhase({ C, phase }) {
  const total = C.total_pairs || C.workers.reduce((a, w) => a + w.total, 0);
  const floods = C.workers.reduce((a, w) => a + w.flood_waits, 0);
  return (
    <div className="card">
      <div className="row" style={{ marginBottom: 10 }}>
        <h2 style={{ margin: 0 }}>فاز ۲ — کامنت و ری‌اکشن (Telethon)</h2>
        <Pill status={phase.status} />
      </div>
      <Progress
        done={C.done}
        total={total}
        finished={phase.status === 'done'}
        label="پیام‌های پردازش‌شده"
        right={`${fa(C.done)} از ${fa(total)}${total ? ` (${((C.done / total) * 100).toFixed(1)}٪)` : ''}`}
      />
      <div className="kpis" style={{ marginTop: 14 }}>
        <Kpi value={fa(C.inserted.telegram_comments || 0)} label="کامنت درج‌شده" />
        <Kpi value={fa(C.inserted.telegram_reactions || 0)} label="ردیف ری‌اکشن" />
        <Kpi value={`${fa(C.workers.filter(w => w.status === 'running').length)} / ${fa(C.workers.length)}`} label="ورکر فعال" />
        <Kpi value={fa(C.sessions)} label="سشن" />
        <Kpi value={fa(floods)} label="Flood wait" tone={floods ? 'warn' : ''} />
        <Kpi value={fa(C.errors)} label="خطا" tone={C.errors ? 'bad' : ''} />
      </div>
      <div className="table-wrap" style={{ marginTop: 14 }}>
        <table>
          <thead>
            <tr><th>ورکر</th><th>سشن</th><th>وضعیت</th><th style={{ width: '30%' }}>پیشرفت</th><th>کانال فعلی</th><th className="num">Flood wait</th><th className="num">خطا</th></tr>
          </thead>
          <tbody>
            {C.workers.length ? C.workers.map(w => (
              <tr key={w.id}>
                <td>{w.id}</td>
                <td className="ltr mono small">{w.session.split('/').pop()}</td>
                <td><Pill status={w.status === 'starting' ? '' : w.status}>{STATUS[w.status]}</Pill></td>
                <td><Progress done={w.done} total={w.total} finished={w.status === 'done'} label={`${fa(w.done)} / ${fa(w.total)}`} right="" /></td>
                <td className="ltr small">{w.channel ? `@${w.channel}` : ''}</td>
                <td className="num">{fa(w.flood_waits)}{w.flood_seconds ? <span className="muted small"> ({fa(w.flood_seconds)}ث)</span> : null}</td>
                <td className="num">{fa(w.errors)}</td>
              </tr>
            )) : (
              <tr><td colSpan="7"><Empty>{phase.status === 'pending' ? 'منتظر پایان فاز پست‌ها' : 'ورکری اجرا نشده'}</Empty></td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function lineClass(l) {
  if (/\[(ERROR|CRITICAL)\]|❌|✗|Traceback/.test(l)) return 'e';
  if (/\[WARNING\]|⚠️/.test(l)) return 'w';
  if (/✅|✓|🎉|🏁/.test(l)) return 'ok';
  return '';
}

const MAX_LINES = 4000;

function LogViewer({ runId, files, live, preferred }) {
  const [file, setFile] = useState('');
  const [lines, setLines] = useState([]);
  const [size, setSize] = useState(0);
  const [follow, setFollow] = useState(true);
  const offset = useRef(-1);
  const partial = useRef('');
  const box = useRef(null);

  useEffect(() => {
    if (!files.includes(file)) setFile(files.includes(preferred) ? preferred : files[0] || '');
  }, [files, file, preferred]);

  useEffect(() => {
    offset.current = -1;
    partial.current = '';
    setLines([]);
    if (!file) return undefined;
    let stop = false;
    async function tick() {
      try {
        const d = await api(`/api/runs/${encodeURIComponent(runId)}/log?file=${encodeURIComponent(file)}&offset=${offset.current}`);
        if (stop) return;
        offset.current = d.offset;
        setSize(d.size);
        if (d.text) {
          const parts = (partial.current + d.text).split('\n');
          partial.current = parts.pop();
          setLines(prev => {
            const next = prev.concat(parts);
            return next.length > MAX_LINES ? next.slice(-MAX_LINES) : next;
          });
        }
      } catch { /* ignore transient errors */ }
    }
    tick();
    const id = live ? setInterval(tick, 2000) : null;
    return () => { stop = true; if (id) clearInterval(id); };
  }, [runId, file, live]);

  useEffect(() => {
    if (follow && box.current) box.current.scrollTop = box.current.scrollHeight;
  }, [lines, follow]);

  return (
    <div className="card">
      <div className="row" style={{ marginBottom: 10 }}>
        <h2 style={{ margin: 0 }}>{live ? 'لاگ زنده' : 'لاگ'}</h2>
        <select className="ltr" style={{ width: 'auto', minWidth: 180 }} value={file} onChange={e => setFile(e.target.value)}>
          {files.map(f => <option key={f}>{f}</option>)}
        </select>
        <label className="check"><input type="checkbox" checked={follow} onChange={e => setFollow(e.target.checked)} /> دنبال کردن انتها</label>
        <div className="spacer" />
        <span className="small muted ltr">{(size / 1024).toFixed(1)} KB</span>
      </div>
      <pre className="log ltr mono" ref={box}>
        {lines.map((l, i) => {
          const c = lineClass(l);
          return c ? <span key={i} className={c}>{l + '\n'}</span> : <Fragment key={i}>{l + '\n'}</Fragment>;
        })}
      </pre>
    </div>
  );
}

/** Full view of one run: phases, progress, workers, issues, log. `st` is /api/status output. */
export default function RunDetail({ st }) {
  const r = st.run;
  const phase = n => r.phases.find(p => p.name === n);
  const issues = [...(st.progress.posts?.issues || []), ...(st.progress.comments?.issues || [])];
  const runningPhase = r.phases.find(p => p.status === 'running')?.name;
  return (
    <div>
      <div className="card">
        <div className="row" style={{ marginBottom: 12 }}>
          <h2 style={{ margin: 0 }}>اجرای <span className="ltr mono">{r.id}</span></h2>
          <Pill status={r.status} />
          <span className="small muted">
            {MODE[r.mode]} · شروع {fmtTime(r.started_at)} · مدت <bdi className="ltr">{duration(r.started_at, r.finished_at)}</bdi>
            {r.mode !== 'comments' && <> · {fa(r.params.days)} روز اخیر</>}
            {r.mode !== 'posts' && <> · سقف {fa(r.params.limit)} کامنت</>}
          </span>
        </div>
        <div className="row">
          {r.phases.map((p, i) => (
            <Fragment key={p.name}>
              {i > 0 && <span className="muted">←</span>}
              <span className="small">{PHASE[p.name]}</span>
              <Pill status={p.status} />
              <span className="small muted">
                {p.started_at ? <bdi>{duration(p.started_at, p.finished_at)}</bdi> : ''}
                {p.returncode ? ` · exit ${p.returncode}` : ''}
              </span>
            </Fragment>
          ))}
        </div>
      </div>

      {st.progress.posts && <PostsPhase P={st.progress.posts} phase={phase('posts')} serverTime={st.server_time} />}
      {st.progress.comments && <CommentsPhase C={st.progress.comments} phase={phase('comments')} />}

      <div className="card">
        <h2>هشدارها و خطاهای اخیر</h2>
        <div className="issues ltr mono">
          {issues.length ? issues.slice(-60).reverse().map((l, i) => (
            <div key={i} className={`issue ${/\[(ERROR|CRITICAL)\]/.test(l) ? 'e' : ''}`}>{l}</div>
          )) : <span className="small muted">موردی نیست 👌</span>}
        </div>
      </div>

      <LogViewer runId={r.id} files={st.files} live={st.running} preferred={runningPhase === 'comments' ? 'comments.log' : 'posts.log'} />
    </div>
  );
}

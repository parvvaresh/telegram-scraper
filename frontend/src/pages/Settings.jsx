import { useEffect, useState } from 'react';
import { api, fa } from '../lib';
import { Banner, useToast } from '../components/ui';

function Field({ s, set, path, label, hint, type = 'text', ltr, full, ...rest }) {
  const [sec, key] = path.split('.');
  const value = s?.[sec]?.[key] ?? '';
  return (
    <label className={`field ${full ? 'full' : ''}`}>
      {label}
      <input
        type={type}
        className={ltr ? 'ltr' : ''}
        value={value}
        onChange={e => set(prev => ({ ...prev, [sec]: { ...prev[sec], [key]: e.target.value } }))}
        autoComplete="off"
        {...rest}
      />
      {hint && <span className="hint">{hint}</span>}
    </label>
  );
}

export default function Settings() {
  const toast = useToast();
  const [s, setS] = useState(null);
  const [meta, setMeta] = useState({});
  const [sessions, setSessions] = useState([]);
  const [dbOut, setDbOut] = useState(null);

  async function load() {
    try {
      const d = await api('/api/settings');
      setS(d.settings);
      setMeta({ path: d.path, exists: d.exists });
      setSessions(await api('/api/sessions'));
    } catch (e) {
      toast(e.message, true);
    }
  }
  useEffect(() => { load(); }, []); // eslint-disable-line react-hooks/exhaustive-deps

  async function save(e) {
    e.preventDefault();
    try {
      const d = await api('/api/settings', { method: 'PUT', body: s });
      setS(d.settings);
      setMeta(m => ({ ...m, exists: true }));
      toast('تنظیمات ذخیره شد');
    } catch (err) {
      toast(err.message, true);
    }
  }

  async function testDb() {
    setDbOut({ loading: true });
    try {
      const d = await api('/api/db/test', { method: 'POST', body: s.clickhouse });
      const need = ['telegram_posts_buffer', 'telegram_comments_buffer', 'telegram_reactions_buffer'];
      setDbOut({ ok: d, missing: need.filter(t => !d.tables.includes(t)) });
    } catch (e) {
      setDbOut({ error: e.message });
    }
  }

  async function initDb() {
    if (!window.confirm('جدول‌های ClickHouse (اگر وجود ندارند) با تنظیمات ذخیره‌شده ساخته شوند؟')) return;
    try {
      const d = await api('/api/db/init', { method: 'POST' });
      toast(`${fa(d.statements.length)} دستور اجرا شد`);
      testDb();
    } catch (e) {
      setDbOut({ error: e.message });
    }
  }

  if (!s) return <div className="card muted">…</div>;
  const f = { s, set: setS };

  return (
    <form onSubmit={save}>
      <div className="page-title"><h2>تنظیمات</h2></div>
      <Banner>
        تنظیمات در <code>{meta.path}</code> ذخیره می‌شوند{meta.exists ? '' : ' (هنوز ساخته نشده؛ مقادیر پیش‌فرض نمایش داده می‌شوند)'}.
        این فایل در git نادیده گرفته می‌شود چون رمزها در آن است. تغییرات از اجرای بعدی اعمال می‌شوند.
      </Banner>
      <div className="grid g2" style={{ marginBottom: 16 }}>
        <div className="card">
          <h2>Telegram API</h2>
          <div className="fields">
            <Field {...f} path="telegram.api_id" label="api_id" type="number" hint="از my.telegram.org" />
            <Field {...f} path="telegram.api_hash" label="api_hash" type="password" ltr />
            <Field {...f} path="telegram.timeout" label="Timeout (ثانیه)" type="number" min="1" />
            <Field {...f} path="telegram.num_sessions" label="تعداد سشن برای ساخت" type="number" min="1" hint="برای session/create_esssion.py" />
          </div>
          <h3 style={{ marginTop: 16 }}>سشن‌های موجود</h3>
          {sessions.length ? (
            <div className="chips">{sessions.map(x => <span key={x.name} className="chip">{x.name}</span>)}</div>
          ) : (
            <div className="small muted">هیچ فایل <code>session/telegram_*.session</code> پیدا نشد — فاز کامنت بدون سشن اجرا نمی‌شود.</div>
          )}
          <details style={{ marginTop: 8 }}>
            <summary>ساخت سشن جدید</summary>
            <p className="small muted">ساخت سشن نیاز به شماره و کد تأیید دارد، پس در ترمینال اجرا کنید: <code>python3 session/create_esssion.py</code></p>
          </details>
        </div>

        <div className="card">
          <h2>ClickHouse</h2>
          <div className="fields">
            <Field {...f} path="clickhouse.url" label="HTTP URL" ltr full />
            <Field {...f} path="clickhouse.user" label="کاربر" ltr />
            <Field {...f} path="clickhouse.password" label="رمز" type="password" ltr />
            <Field {...f} path="clickhouse.database" label="دیتابیس" ltr />
          </div>
          <div className="row" style={{ marginTop: 12 }}>
            <button type="button" className="btn" onClick={testDb}>تست اتصال</button>
            <button type="button" className="btn" onClick={initDb}>ساخت جدول‌ها (اگر نیست)</button>
          </div>
          <div className="small" style={{ marginTop: 10 }}>
            {dbOut?.loading && <span className="muted">در حال تست…</span>}
            {dbOut?.error && <Banner tone="err"><span className="ltr">{dbOut.error}</span></Banner>}
            {dbOut?.ok && (
              <Banner tone={dbOut.missing.length ? 'err' : 'ok'}>
                ✓ وصل شد — ClickHouse {dbOut.ok.version} · دیتابیس <b className="ltr">{dbOut.ok.database}</b>
                {dbOut.missing.length ? <><br />جدول‌های ناموجود: <span className="ltr">{dbOut.missing.join(', ')}</span></> : ' · همهٔ جدول‌ها موجودند'}
              </Banner>
            )}
          </div>
        </div>

        <div className="card">
          <h2>پراکسی HTTP <span className="muted small">(برای اسکرپ پست‌ها)</span></h2>
          <div className="fields">
            <Field {...f} path="http_proxy.host" label="Host" ltr />
            <Field {...f} path="http_proxy.port" label="Port" type="number" />
            <Field {...f} path="http_proxy.user" label="User" ltr hint="اختیاری" />
            <Field {...f} path="http_proxy.password" label="Password" type="password" ltr />
          </div>
          <p className="small muted" style={{ marginBottom: 0 }}>اگر Host یا Port خالی باشد، درخواست‌ها مستقیم ارسال می‌شوند.</p>
        </div>

        <div className="card">
          <h2>پراکسی MTProto <span className="muted small">(برای Telethon)</span></h2>
          <div className="fields">
            <Field {...f} path="mtproto_proxy.server" label="Server" ltr />
            <Field {...f} path="mtproto_proxy.port" label="Port" type="number" />
            <Field {...f} path="mtproto_proxy.secret" label="Secret (hex)" type="password" ltr full />
          </div>
          <p className="small muted" style={{ marginBottom: 0 }}>اگر Server خالی باشد، Telethon مستقیم وصل می‌شود.</p>
        </div>

        <div className="card">
          <h2>اسکرپ پست‌ها</h2>
          <div className="fields">
            <Field {...f} path="posts.days" label="چند روز اخیر" type="number" min="1" />
            <Field {...f} path="posts.batch_size" label="کانال در هر بچ" type="number" min="1" hint="هر بچ یک پروسس" />
            <Field {...f} path="posts.max_parallel_batches" label="بچ‌های هم‌زمان" type="number" min="1" />
            <Field {...f} path="posts.max_threads" label="ترد در هر بچ" type="number" min="1" />
            <Field {...f} path="posts.max_pages" label="حداکثر صفحه برای هر کانال" type="number" min="1" />
            <Field {...f} path="posts.http_max_retries" label="تلاش مجدد HTTP" type="number" min="0" />
            <Field {...f} path="posts.delay_min" label="حداقل تأخیر بین صفحات (ث)" type="number" step="0.1" min="0" />
            <Field {...f} path="posts.delay_max" label="حداکثر تأخیر (ث)" type="number" step="0.1" min="0" />
            <Field {...f} path="posts.insert_batch_size" label="ردیف در هر insert" type="number" min="1" />
          </div>
        </div>

        <div className="card">
          <h2>کامنت و ری‌اکشن</h2>
          <div className="fields">
            <Field {...f} path="comments.limit" label="سقف کامنت هر پست" type="number" min="1" />
            <Field {...f} path="comments.num_workers" label="تعداد ورکر" type="number" min="1" hint="حداکثر به تعداد سشن‌ها" />
          </div>
          <p className="small muted" style={{ marginBottom: 0 }}>
            هر ورکر یک فایل سشن جدا می‌گیرد؛ اشتراک یک سشن بین چند پروسس باعث خطای <code>database is locked</code> می‌شود.
          </p>
        </div>
      </div>
      <div className="card row sticky-actions">
        <button type="submit" className="btn primary">ذخیرهٔ تنظیمات</button>
        <button type="button" className="btn" onClick={load}>بازخوانی</button>
      </div>
    </form>
  );
}

import { useCallback, useEffect, useRef, useState } from 'react';

export async function api(path, { method = 'GET', body } = {}) {
  const res = await fetch(path, {
    method,
    headers: body !== undefined ? { 'Content-Type': 'application/json' } : undefined,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || res.statusText);
  return data;
}

export const fa = n => Number(n ?? 0).toLocaleString('fa-IR');

export function duration(start, end) {
  if (!start) return '';
  const s = Math.max(0, Math.round(((end ? new Date(end) : new Date()) - new Date(start)) / 1000));
  const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60), ss = s % 60;
  return (h ? `${h}:${String(m).padStart(2, '0')}` : m) + ':' + String(ss).padStart(2, '0');
}

export const fmtTime = iso =>
  iso ? new Date(iso).toLocaleString('fa-IR', { dateStyle: 'short', timeStyle: 'short' }) : '';

export const normalizeChannel = s => {
  s = (s || '').trim().replace(/^@/, '');
  const parts = s.split('/');
  return parts[parts.length - 1] || null;
};

export const STATUS = {
  running: 'در حال اجرا', done: 'تمام شد', failed: 'ناموفق', stopped: 'متوقف شد', pending: 'در صف',
  skipped: 'رد شد', interrupted: 'قطع شد', finished: 'پایان', starting: 'در حال اتصال',
};
export const MODE = { all: 'کامل', posts: 'فقط پست', comments: 'فقط کامنت/ری‌اکشن' };
export const PHASE = { posts: 'پست‌ها', comments: 'کامنت و ری‌اکشن' };

/** Calls `fn` now and every `ms` while the tab is visible. Returns {data, error, reload}. */
export function usePoll(fn, ms, deps = []) {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const fnRef = useRef(fn);
  fnRef.current = fn;
  const reload = useCallback(async () => {
    try {
      setData(await fnRef.current());
      setError(null);
    } catch (e) {
      setError(e);
    }
  }, []);
  useEffect(() => {
    reload();
    if (!ms) return undefined;
    const id = setInterval(() => { if (!document.hidden) reload(); }, ms);
    return () => clearInterval(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ms, reload, ...deps]);
  return { data, error, reload };
}

/** Minimal hash router: "#/run/20250101-101010" -> ["run", "20250101-101010"]. */
export function useHashRoute() {
  const read = () => (window.location.hash.replace(/^#\/?/, '') || 'dashboard').split('/');
  const [route, setRoute] = useState(read);
  useEffect(() => {
    const on = () => setRoute(read());
    window.addEventListener('hashchange', on);
    return () => window.removeEventListener('hashchange', on);
  }, []);
  return route;
}

export const go = path => { window.location.hash = '#/' + path; };

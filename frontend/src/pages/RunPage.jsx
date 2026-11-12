import { api, usePoll } from '../lib';
import { Banner, Empty } from '../components/ui';
import RunControls from '../components/RunControls';
import RunDetail from '../components/RunDetail';

export default function RunPage({ runId }) {
  const { data: st, error, reload } = usePoll(
    () => api('/api/status' + (runId ? `?run_id=${encodeURIComponent(runId)}` : '')),
    2000,
    [runId],
  );
  const { data: summary, reload: reloadSummary } = usePoll(() => api('/api/summary'), 3000);
  const viewingOld = runId && summary && !(st?.running);

  return (
    <div>
      <div className="page-title">
        <h2>اجرا و مانیتور</h2>
        {runId && <a className="small" href="#/run">نمایش آخرین اجرا</a>}
      </div>
      {(!runId || summary?.running) && (
        <RunControls running={!!summary?.running} onChange={() => { reload(); reloadSummary(); }} />
      )}
      {viewingOld && <Banner>در حال مشاهدهٔ یک اجرای قبلی از <a href="#/history">تاریخچه</a>.</Banner>}
      {error && <Banner tone="err">{error.message}</Banner>}
      {st && !st.run && <div className="card"><Empty>هنوز هیچ اجرایی ثبت نشده. کانال‌ها و تنظیمات را بررسی کنید و «شروع اجرا» را بزنید.</Empty></div>}
      {st?.run && <RunDetail st={st} />}
    </div>
  );
}

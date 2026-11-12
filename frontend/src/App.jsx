import { PHASE, api, usePoll, useHashRoute } from './lib';
import { ToastProvider } from './components/ui';
import Dashboard from './pages/Dashboard';
import RunPage from './pages/RunPage';
import History from './pages/History';
import Channels from './pages/Channels';
import Settings from './pages/Settings';
import Data from './pages/Data';
import Preview from './pages/Preview';

const NAV = [
  ['dashboard', 'داشبورد'],
  ['run', 'اجرا و مانیتور'],
  ['history', 'تاریخچه'],
  ['channels', 'کانال‌ها'],
  ['settings', 'تنظیمات'],
  ['data', 'داده‌ها'],
  ['preview', 'پیش‌نمایش اسکرپ'],
];

function GlobalStatus() {
  const { data } = usePoll(() => api('/api/runs?limit=1'), 3000);
  const r = data?.[0];
  if (r?.status === 'running') {
    const phase = r.phases.find(p => p.status === 'running')?.name;
    return <a href="#/run" className="pill running">در حال اجرا · {PHASE[phase] || ''}</a>;
  }
  return <span className="pill">بیکار</span>;
}

export default function App() {
  const [page, arg] = useHashRoute();
  let content;
  switch (page) {
    case 'run': content = <RunPage runId={arg ? decodeURIComponent(arg) : null} />; break;
    case 'history': content = <History />; break;
    case 'channels': content = <Channels />; break;
    case 'settings': content = <Settings />; break;
    case 'data': content = <Data />; break;
    case 'preview': content = <Preview initial={arg ? decodeURIComponent(arg) : ''} />; break;
    default: content = <Dashboard />;
  }
  const active = NAV.some(([k]) => k === page) ? page : 'dashboard';
  return (
    <ToastProvider>
      <header>
        <div className="bar">
          <h1>📡 پنل اسکرپر تلگرام</h1>
          <nav>
            {NAV.map(([k, label]) => (
              <a key={k} href={`#/${k}`} className={active === k ? 'active' : ''}>{label}</a>
            ))}
          </nav>
          <div className="spacer" />
          <GlobalStatus />
        </div>
      </header>
      <main key={page + (arg || '')}>{content}</main>
    </ToastProvider>
  );
}

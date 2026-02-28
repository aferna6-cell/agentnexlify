import { useState, useCallback, Component } from 'react';
import Sidebar from './components/Sidebar';
import Dashboard from './components/Dashboard';
import LiveChat from './components/LiveChat';
import FAQBot from './components/FAQBot';
import Automations from './components/Automations';
import Notifications from './components/Notifications';

const pages = {
  dashboard: Dashboard,
  chat: LiveChat,
  faq: FAQBot,
  automations: Automations,
  notifications: Notifications,
};

class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false };
  }
  static getDerivedStateFromError() {
    return { hasError: true };
  }
  render() {
    if (this.state.hasError) {
      return <div style={{ padding: '2rem', textAlign: 'center' }}>Something went wrong — refresh to retry.</div>;
    }
    return this.props.children;
  }
}

function SkeletonLoader() {
  return (
    <div className="fade-in">
      <div className="skeleton-row">
        <div className="skeleton skeleton-card" />
        <div className="skeleton skeleton-card" />
        <div className="skeleton skeleton-card" />
        <div className="skeleton skeleton-card" />
      </div>
      <div className="skeleton skeleton-block" />
      <div className="skeleton skeleton-block" style={{ height: 200 }} />
    </div>
  );
}

export default function App() {
  const [currentPage, setCurrentPage] = useState('dashboard');
  const [loading, setLoading] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);

  const handleNavigate = useCallback((page) => {
    if (page === currentPage) return;
    if (page === 'settings') return; // placeholder
    setLoading(true);
    setTimeout(() => {
      setCurrentPage(page);
      setLoading(false);
    }, 200);
  }, [currentPage]);

  const handleRefresh = useCallback(() => {
    setRefreshKey((k) => k + 1);
  }, []);

  const PageComponent = pages[currentPage] || Dashboard;

  return (
    <div className="app">
      <Sidebar currentPage={currentPage} onNavigate={handleNavigate} />
      <main className="content">
        {loading ? (
          <SkeletonLoader />
        ) : (
          <div className="fade-in" key={`${currentPage}-${refreshKey}`}>
            <ErrorBoundary><PageComponent /></ErrorBoundary>
          </div>
        )}
      </main>
      <button className="refresh-btn" onClick={handleRefresh} title="Refresh demo data">
        {'\uD83D\uDD04'} Refresh Demo Data
      </button>
    </div>
  );
}

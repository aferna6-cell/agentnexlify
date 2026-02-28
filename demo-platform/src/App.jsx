import { useState, useCallback, useMemo, Component } from 'react';
import Sidebar from './components/Sidebar';
import Dashboard from './components/Dashboard';
import LiveChat from './components/LiveChat';
import FAQBot from './components/FAQBot';
import Automations from './components/Automations';
import Notifications from './components/Notifications';
import Widget from './components/Widget';
import SignupWizard from './pages/Signup/SignupWizard';
import SchemaOrg, { ORGANIZATION_SCHEMA, SOFTWARE_APP_SCHEMA } from './components/SchemaOrg';
import SEO from './components/SEO';

const pages = {
  dashboard: Dashboard,
  chat: LiveChat,
  faq: FAQBot,
  automations: Automations,
  notifications: Notifications,
  widget: Widget,
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
  const isSignup = window.location.pathname === '/signup';

  const schemas = useMemo(
    () => isSignup
      ? [ORGANIZATION_SCHEMA, SOFTWARE_APP_SCHEMA]
      : [ORGANIZATION_SCHEMA],
    [isSignup],
  );

  // Render signup wizard full-screen when on /signup path
  if (isSignup) {
    return (
      <ErrorBoundary>
        <SEO
          title="Get Your Free AI Chatbot | AgentNexLiFy"
          description="Create your free AI chatbot in 2 minutes. No credit card. Automatically captures leads, books appointments, and answers FAQs 24/7."
          canonical="/free-chatbot"
        />
        <SchemaOrg schemas={schemas} />
        <SignupWizard />
      </ErrorBoundary>
    );
  }

  return <DashboardApp schemas={schemas} />;
}

function DashboardApp({ schemas }) {
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
      <SEO
        title="AgentNexLiFy | Free AI Chatbot for Local Businesses"
        description="Add a free AI chatbot to your local business website. Handle inquiries 24/7, capture leads, and automate bookings — no coding required."
        canonical="/"
      />
      <SchemaOrg schemas={schemas} />
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

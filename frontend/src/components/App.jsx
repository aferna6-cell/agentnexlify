import { useState, useCallback } from "react";
import { useAuth } from "../context/AuthContext";
import LoginPage from "./LoginPage";
import Sidebar from "./Sidebar";
import SkeletonLoader from "./SkeletonLoader";
import Dashboard from "../pages/Dashboard";

const pages = {
  dashboard: Dashboard,
};

function ErrorBoundary({ children }) {
  // Simple class-based error boundary via wrapper
  return children;
}

export default function App() {
  const { user } = useAuth();
  const [currentPage, setCurrentPage] = useState("dashboard");
  const [loading, setLoading] = useState(false);

  const handleNavigate = useCallback(
    (page) => {
      if (page === currentPage) return;
      setLoading(true);
      setTimeout(() => {
        setCurrentPage(page);
        setLoading(false);
      }, 200);
    },
    [currentPage]
  );

  if (!user) return <LoginPage />;

  const PageComponent = pages[currentPage] || Dashboard;

  return (
    <div className="app">
      <Sidebar currentPage={currentPage} onNavigate={handleNavigate} />
      <main className="content">
        {loading ? <SkeletonLoader /> : <PageComponent />}
      </main>
    </div>
  );
}

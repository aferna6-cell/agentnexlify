import { useState, useEffect, useCallback } from "react";
import { useAuth } from "../../context/AuthContext";
import SkeletonLoader from "../../components/SkeletonLoader";
import { notify } from "../../utils/notify";
import { apiFetch, cardStyle, btnPrimary } from "./utils";
import EmptyState from "./EmptyState";
import TestsList from "./TestsList";
import ResultsPanel from "./ResultsPanel";
import CreateTestModal from "./CreateTestModal";

export default function ABTestsPage() {
  const { user, token } = useAuth();
  const [tests, setTests] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [selectedTest, setSelectedTest] = useState(null);

  const loadTests = useCallback(async () => {
    if (!user?.tenantId || !token) return;
    setLoading(true);
    try {
      const res = await apiFetch(`/ab-tests/${user.tenantId}`, token);
      setTests(Array.isArray(res) ? res : res.ab_tests || res.tests || []);
    } catch {
      setTests([]);
    } finally {
      setLoading(false);
    }
  }, [user?.tenantId, token]);

  useEffect(() => {
    loadTests();
  }, [loadTests]);

  const handleStartTest = async (testId) => {
    try {
      await apiFetch(`/ab-tests/${user.tenantId}/${testId}/start`, token, {
        method: "POST",
      });
      loadTests();
    } catch (e) {
      notify.error("Failed to start: " + (e.message || "Unknown error"));
    }
  };

  const handleCompleteTest = async (testId) => {
    if (!confirm("Complete this test and select a winner?")) return;
    try {
      const testRes = await apiFetch(
        `/ab-tests/${user.tenantId}/${testId}`,
        token,
      );
      const variants = testRes.variants || [];
      if (variants.length === 0) {
        notify.error("No variants found for this test");
        return;
      }
      const options = variants.map((v, i) => `${i + 1}. ${v.name}`).join("\n");
      const choice = prompt(`Select winner:\n${options}\n\nEnter number:`);
      const idx = parseInt(choice) - 1;
      if (isNaN(idx) || idx < 0 || idx >= variants.length) {
        notify.error("Invalid selection");
        return;
      }
      const winnerVariantId = variants[idx].id;
      await apiFetch(`/ab-tests/${user.tenantId}/${testId}/complete`, token, {
        method: "POST",
        body: JSON.stringify({ variant_id: winnerVariantId }),
      });
      loadTests();
      if (selectedTest?.id === testId) {
        setSelectedTest((prev) => ({ ...prev, status: "completed" }));
      }
    } catch (e) {
      notify.error("Failed to complete: " + (e.message || "Unknown error"));
    }
  };

  const handleDelete = async (testId) => {
    if (!confirm("Delete this A/B test?")) return;
    try {
      await apiFetch(`/ab-tests/${user.tenantId}/${testId}`, token, {
        method: "DELETE",
      });
      setTests((prev) => prev.filter((t) => t.id !== testId));
      if (selectedTest?.id === testId) setSelectedTest(null);
    } catch (e) {
      notify.error("Failed to delete: " + (e.message || "Unknown error"));
    }
  };

  if (loading && tests.length === 0) return <SkeletonLoader />;

  return (
    <div style={{ padding: "24px 32px", maxWidth: 1200 }}>
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          marginBottom: 24,
        }}
      >
        <div>
          <h1
            style={{
              fontSize: "1.5rem",
              fontWeight: 700,
              margin: 0,
              color: "var(--text-primary)",
            }}
          >
            A/B Tests
          </h1>
          <p
            style={{
              color: "var(--text-secondary)",
              margin: "4px 0 0",
              fontSize: "0.9rem",
            }}
          >
            Compare campaign variants to optimize performance
          </p>
        </div>
        <button onClick={() => setShowCreate(true)} style={btnPrimary}>
          + Create A/B Test
        </button>
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(3, 1fr)",
          gap: 16,
          marginBottom: 24,
        }}
      >
        {[
          { label: "Total Tests", value: tests.length },
          {
            label: "Running",
            value: tests.filter((t) => t.status === "running").length,
          },
          {
            label: "Completed",
            value: tests.filter((t) => t.status === "completed").length,
          },
        ].map((s) => (
          <div key={s.label} style={cardStyle}>
            <div
              style={{
                fontSize: "0.8rem",
                color: "var(--text-secondary)",
                marginBottom: 4,
              }}
            >
              {s.label}
            </div>
            <div
              style={{
                fontSize: "1.5rem",
                fontWeight: 700,
                color: "var(--accent)",
              }}
            >
              {s.value}
            </div>
          </div>
        ))}
      </div>

      {tests.length === 0 ? (
        <EmptyState message="No A/B tests yet" />
      ) : (
        <TestsList
          tests={tests}
          onSelect={setSelectedTest}
          onStart={handleStartTest}
          onComplete={handleCompleteTest}
          onDelete={handleDelete}
        />
      )}

      {selectedTest && (
        <ResultsPanel
          test={selectedTest}
          onClose={() => setSelectedTest(null)}
        />
      )}

      {showCreate && (
        <CreateTestModal
          tenantId={user?.tenantId}
          token={token}
          onClose={() => setShowCreate(false)}
          onCreated={() => {
            setShowCreate(false);
            loadTests();
          }}
        />
      )}
    </div>
  );
}

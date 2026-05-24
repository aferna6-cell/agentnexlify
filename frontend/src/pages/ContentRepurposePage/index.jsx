import { useState, useEffect, useCallback } from "react";
import { useAuth } from "../../context/AuthContext";
import { notify } from "../../utils/notify";
import {
  createRepurposeJob,
  listRepurposeJobs,
  getRepurposeJob,
  connectRepurposeOutputs,
  deleteRepurposeJob,
} from "../../utils/api/repurpose";
import { FORMAT_OPTIONS, TABS } from "./constants";
import UpgradePrompt from "./UpgradePrompt";
import InputPanel from "./InputPanel";
import JobHistory from "./JobHistory";
import OutputViewer from "./OutputViewer";

export default function ContentRepurposePage() {
  const { user } = useAuth();
  const tenantId = user?.tenantId;
  const plan = user?.plan || "free";
  const isEligible = plan === "professional" || plan === "enterprise";

  const [jobs, setJobs] = useState([]);
  const [selectedJob, setSelectedJob] = useState(null);
  const [activeTab, setActiveTab] = useState("x_thread");
  const [loading, setLoading] = useState(false);
  const [creating, setCreating] = useState(false);
  const [connecting, setConnecting] = useState({});

  const [sourceType, setSourceType] = useState("text");
  const [sourceInput, setSourceInput] = useState("");
  const [tone, setTone] = useState("professional");
  const [formats, setFormats] = useState(FORMAT_OPTIONS.map((f) => f.key));

  const loadJobs = useCallback(async () => {
    if (!tenantId || !isEligible) return;
    try {
      const data = await listRepurposeJobs(tenantId);
      setJobs(data.jobs || []);
    } catch {
      /* non-critical */
    }
  }, [tenantId, isEligible]);

  useEffect(() => {
    loadJobs();
  }, [loadJobs]);

  const loadJob = useCallback(
    async (jobId) => {
      if (!tenantId) return;
      setLoading(true);
      try {
        const data = await getRepurposeJob(tenantId, jobId);
        setSelectedJob(data);
        if (data.outputs) {
          const firstAvailable = TABS.find((t) => data.outputs[t.key]);
          if (firstAvailable) setActiveTab(firstAvailable.key);
        }
      } catch {
        /* non-critical */
      } finally {
        setLoading(false);
      }
    },
    [tenantId],
  );

  const handleCreate = async () => {
    if (!sourceInput.trim() || creating) return;
    setCreating(true);
    try {
      const data = await createRepurposeJob(tenantId, {
        source_type: sourceType,
        source_input: sourceInput,
        tone,
        formats,
      });
      setSourceInput("");
      await loadJobs();
      const pollId = setInterval(async () => {
        try {
          const job = await getRepurposeJob(tenantId, data.id);
          if (job.status !== "processing") {
            clearInterval(pollId);
            setSelectedJob(job);
            loadJobs();
          }
        } catch {
          clearInterval(pollId);
        }
      }, 3000);
    } catch (err) {
      notify.error(err.message || "Failed to create repurpose job");
    } finally {
      setCreating(false);
    }
  };

  const handleConnect = async (target) => {
    if (!selectedJob || connecting[target]) return;
    setConnecting((prev) => ({ ...prev, [target]: true }));
    try {
      await connectRepurposeOutputs(tenantId, selectedJob.id, [target]);
      notify.error(`Pushed to ${target.replace("_", " ")} successfully!`);
    } catch (err) {
      notify.error(err.message || `Failed to push to ${target}`);
    } finally {
      setConnecting((prev) => ({ ...prev, [target]: false }));
    }
  };

  const handleDelete = async (jobId) => {
    if (!confirm("Delete this repurpose job?")) return;
    try {
      await deleteRepurposeJob(tenantId, jobId);
      if (selectedJob?.id === jobId) setSelectedJob(null);
      loadJobs();
    } catch {
      /* non-critical */
    }
  };

  const toggleFormat = (key) => {
    setFormats((prev) =>
      prev.includes(key) ? prev.filter((f) => f !== key) : [...prev, key],
    );
  };

  if (!isEligible) {
    return <UpgradePrompt />;
  }

  return (
    <div style={{ display: "flex", gap: 24, height: "100%" }}>
      <div
        style={{
          width: 340,
          flexShrink: 0,
          display: "flex",
          flexDirection: "column",
          gap: 16,
        }}
      >
        <InputPanel
          sourceType={sourceType}
          setSourceType={setSourceType}
          sourceInput={sourceInput}
          setSourceInput={setSourceInput}
          tone={tone}
          setTone={setTone}
          formats={formats}
          toggleFormat={toggleFormat}
          creating={creating}
          onCreate={handleCreate}
        />
        <JobHistory
          jobs={jobs}
          selectedJob={selectedJob}
          onSelect={loadJob}
          onDelete={handleDelete}
        />
      </div>

      <div
        style={{
          flex: 1,
          background: "var(--card-bg)",
          borderRadius: 12,
          border: "1px solid var(--border)",
          display: "flex",
          flexDirection: "column",
          overflow: "hidden",
        }}
      >
        <OutputViewer
          selectedJob={selectedJob}
          loading={loading}
          activeTab={activeTab}
          setActiveTab={setActiveTab}
          connecting={connecting}
          onConnect={handleConnect}
        />
      </div>
    </div>
  );
}

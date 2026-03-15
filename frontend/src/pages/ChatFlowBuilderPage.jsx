import { useState, useEffect, useCallback, useMemo } from "react";
import { useAuth } from "../context/AuthContext";
import SkeletonLoader from "../components/SkeletonLoader";
import {
  ReactFlow,
  Controls,
  Background,
  MiniMap,
  addEdge,
  useNodesState,
  useEdgesState,
  Handle,
  Position,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import {
  fetchChatFlows,
  fetchFlowTemplates,
  createChatFlow,
  createFlowFromTemplate,
  updateChatFlow,
  deleteChatFlow,
} from "../utils/api";

// --- Custom Node Components ---

const NODE_COLORS = {
  greeting: { bg: "#1e3a5f", border: "#3b82f6", icon: "👋" },
  question: { bg: "#3b1f4e", border: "#8b5cf6", icon: "❓" },
  ai_response: { bg: "#1a3a2e", border: "#22c55e", icon: "🤖" },
  condition: { bg: "#3d2e10", border: "#f59e0b", icon: "🔀" },
  action: { bg: "#1a2e3e", border: "#06b6d4", icon: "⚡" },
  handoff: { bg: "#3e1a2e", border: "#ec4899", icon: "🤝" },
};

const nodeStyle = (type) => ({
  background: NODE_COLORS[type]?.bg || "#2a2a3e",
  border: `2px solid ${NODE_COLORS[type]?.border || "#555"}`,
  borderRadius: "10px",
  padding: "12px 16px",
  color: "#fff",
  fontSize: "13px",
  minWidth: "180px",
  maxWidth: "240px",
});

function GreetingNode({ data }) {
  return (
    <div style={nodeStyle("greeting")}>
      <Handle type="source" position={Position.Bottom} style={{ background: "#3b82f6" }} />
      <div style={{ fontWeight: 600, marginBottom: 4 }}>👋 Greeting</div>
      <div style={{ fontSize: 11, opacity: 0.8, wordBreak: "break-word" }}>
        {data.message || "Hi! How can I help?"}
      </div>
    </div>
  );
}

function QuestionNode({ data }) {
  return (
    <div style={nodeStyle("question")}>
      <Handle type="target" position={Position.Top} style={{ background: "#8b5cf6" }} />
      <Handle type="source" position={Position.Bottom} style={{ background: "#8b5cf6" }} />
      <div style={{ fontWeight: 600, marginBottom: 4 }}>❓ Question</div>
      <div style={{ fontSize: 11, opacity: 0.8, wordBreak: "break-word" }}>
        {data.question || data.label || "Ask a question"}
      </div>
    </div>
  );
}

function AiResponseNode({ data }) {
  return (
    <div style={nodeStyle("ai_response")}>
      <Handle type="target" position={Position.Top} style={{ background: "#22c55e" }} />
      <Handle type="source" position={Position.Bottom} style={{ background: "#22c55e" }} />
      <div style={{ fontWeight: 600, marginBottom: 4 }}>🤖 AI Response</div>
      <div style={{ fontSize: 11, opacity: 0.8 }}>{data.label || "Let AI respond"}</div>
    </div>
  );
}

function ConditionNode({ data }) {
  return (
    <div style={nodeStyle("condition")}>
      <Handle type="target" position={Position.Top} style={{ background: "#f59e0b" }} />
      <Handle type="source" position={Position.Bottom} id="yes" style={{ background: "#22c55e", left: "30%" }} />
      <Handle type="source" position={Position.Bottom} id="no" style={{ background: "#ef4444", left: "70%" }} />
      <div style={{ fontWeight: 600, marginBottom: 4 }}>🔀 Condition</div>
      <div style={{ fontSize: 11, opacity: 0.8 }}>{data.label || "If/else check"}</div>
      {data.condition && (
        <div style={{ fontSize: 10, opacity: 0.6, marginTop: 4, fontStyle: "italic" }}>
          Match: {data.condition}
        </div>
      )}
      <div style={{ display: "flex", justifyContent: "space-between", fontSize: 9, marginTop: 6, opacity: 0.5 }}>
        <span>✓ Yes</span>
        <span>✗ No</span>
      </div>
    </div>
  );
}

function ActionNode({ data }) {
  const actionLabels = {
    show_booking: "📅 Show Booking",
    show_menu: "🍽️ Show Menu",
    take_order: "🛒 Take Order",
    confirm_order: "✅ Confirm Order",
    collect_info: "📋 Collect Info",
  };
  return (
    <div style={nodeStyle("action")}>
      <Handle type="target" position={Position.Top} style={{ background: "#06b6d4" }} />
      <Handle type="source" position={Position.Bottom} style={{ background: "#06b6d4" }} />
      <div style={{ fontWeight: 600, marginBottom: 4 }}>⚡ Action</div>
      <div style={{ fontSize: 11, opacity: 0.8 }}>
        {data.label || actionLabels[data.action] || data.action || "Perform action"}
      </div>
    </div>
  );
}

function HandoffNode({ data }) {
  return (
    <div style={nodeStyle("handoff")}>
      <Handle type="target" position={Position.Top} style={{ background: "#ec4899" }} />
      <div style={{ fontWeight: 600, marginBottom: 4 }}>🤝 Handoff</div>
      <div style={{ fontSize: 11, opacity: 0.8 }}>{data.label || "Transfer to human"}</div>
    </div>
  );
}

const nodeTypes = {
  greeting: GreetingNode,
  question: QuestionNode,
  ai_response: AiResponseNode,
  condition: ConditionNode,
  action: ActionNode,
  handoff: HandoffNode,
};

// --- Node palette for drag-and-drop ---

const NODE_PALETTE = [
  { type: "greeting", label: "Greeting", icon: "👋", desc: "Starting message" },
  { type: "question", label: "Question", icon: "❓", desc: "Ask the visitor" },
  { type: "ai_response", label: "AI Response", icon: "🤖", desc: "Let AI handle it" },
  { type: "condition", label: "Condition", icon: "🔀", desc: "If/else branch" },
  { type: "action", label: "Action", icon: "⚡", desc: "Trigger an action" },
  { type: "handoff", label: "Handoff", icon: "🤝", desc: "Transfer to team" },
];

const ACTION_OPTIONS = [
  { value: "show_booking", label: "Show Booking Form" },
  { value: "show_menu", label: "Show Menu" },
  { value: "take_order", label: "Take Order" },
  { value: "confirm_order", label: "Confirm Order" },
  { value: "collect_info", label: "Collect Info" },
];

// --- Node Editor Panel ---

function NodeEditor({ node, onUpdate, onDelete }) {
  if (!node) return null;

  const t = node.type;
  const d = node.data || {};

  const update = (key, val) => onUpdate(node.id, { ...d, [key]: val });

  return (
    <div style={{
      background: "var(--card-bg, #1e1e2e)", borderRadius: 10, padding: 16,
      border: `1px solid ${NODE_COLORS[t]?.border || "#555"}`,
    }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
        <span style={{ fontWeight: 600, fontSize: 14 }}>
          {NODE_COLORS[t]?.icon} Edit {t.replace("_", " ")}
        </span>
        <button onClick={() => onDelete(node.id)} style={{
          background: "rgba(239,68,68,0.15)", color: "#ef4444", border: "none",
          borderRadius: 6, padding: "4px 10px", cursor: "pointer", fontSize: 12,
        }}>Delete</button>
      </div>

      {t === "greeting" && (
        <div>
          <label style={labelStyle}>Greeting message</label>
          <textarea value={d.message || ""} onChange={(e) => update("message", e.target.value)}
            style={{ ...inputStyle, minHeight: 60, resize: "vertical" }} placeholder="Hi! How can I help?" />
        </div>
      )}

      {t === "question" && (
        <div>
          <label style={labelStyle}>Label</label>
          <input value={d.label || ""} onChange={(e) => update("label", e.target.value)}
            style={inputStyle} placeholder="Question label" />
          <label style={{ ...labelStyle, marginTop: 8 }}>Question text</label>
          <textarea value={d.question || ""} onChange={(e) => update("question", e.target.value)}
            style={{ ...inputStyle, minHeight: 50, resize: "vertical" }} placeholder="What would you like help with?" />
        </div>
      )}

      {t === "ai_response" && (
        <div>
          <label style={labelStyle}>Label</label>
          <input value={d.label || ""} onChange={(e) => update("label", e.target.value)}
            style={inputStyle} placeholder="Answer FAQ" />
        </div>
      )}

      {t === "condition" && (
        <div>
          <label style={labelStyle}>Label</label>
          <input value={d.label || ""} onChange={(e) => update("label", e.target.value)}
            style={inputStyle} placeholder="Wants appointment?" />
          <label style={{ ...labelStyle, marginTop: 8 }}>Match keywords (pipe-separated)</label>
          <input value={d.condition || ""} onChange={(e) => update("condition", e.target.value)}
            style={inputStyle} placeholder="appointment|schedule|book" />
        </div>
      )}

      {t === "action" && (
        <div>
          <label style={labelStyle}>Label</label>
          <input value={d.label || ""} onChange={(e) => update("label", e.target.value)}
            style={inputStyle} placeholder="Show Booking Form" />
          <label style={{ ...labelStyle, marginTop: 8 }}>Action type</label>
          <select value={d.action || ""} onChange={(e) => update("action", e.target.value)} style={inputStyle}>
            <option value="">Select action...</option>
            {ACTION_OPTIONS.map((a) => <option key={a.value} value={a.value}>{a.label}</option>)}
          </select>
        </div>
      )}

      {t === "handoff" && (
        <div>
          <label style={labelStyle}>Label</label>
          <input value={d.label || ""} onChange={(e) => update("label", e.target.value)}
            style={inputStyle} placeholder="Transfer to Team" />
        </div>
      )}
    </div>
  );
}

const labelStyle = { display: "block", fontSize: 11, color: "var(--text-secondary, #888)", marginBottom: 4 };
const inputStyle = {
  width: "100%", padding: "8px 10px", background: "var(--bg, #0a0a0f)",
  border: "1px solid var(--border, #333)", borderRadius: 6, color: "#fff",
  fontSize: 13, outline: "none", boxSizing: "border-box",
};

// --- Main Page ---

let nodeIdCounter = 0;
function nextNodeId() {
  return `node_${Date.now()}_${++nodeIdCounter}`;
}

export default function ChatFlowBuilderPage() {
  const { user, token } = useAuth();
  const [flows, setFlows] = useState([]);
  const [templates, setTemplates] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedFlow, setSelectedFlow] = useState(null);
  const [saving, setSaving] = useState(false);
  const [showTemplates, setShowTemplates] = useState(false);
  const [flowName, setFlowName] = useState("");
  const [dirty, setDirty] = useState(false);

  // React Flow state
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [selectedNode, setSelectedNode] = useState(null);

  const nodeTypesMemo = useMemo(() => nodeTypes, []);

  const loadFlows = useCallback(async () => {
    if (!user?.tenantId) return;
    setLoading(true);
    try {
      const [flowData, tplData] = await Promise.all([
        fetchChatFlows(user.tenantId, token),
        fetchFlowTemplates(user.tenantId, token),
      ]);
      setFlows(flowData.flows || []);
      setTemplates(tplData.templates || []);
    } catch (err) {
      console.warn("Failed to load flows:", err.message);
    } finally {
      setLoading(false);
    }
  }, [user?.tenantId, token]);

  useEffect(() => { loadFlows(); }, [loadFlows]);

  const openFlow = useCallback((flow) => {
    setSelectedFlow(flow);
    setFlowName(flow.name);
    const fj = flow.flow_json || { nodes: [], edges: [] };
    setNodes((fj.nodes || []).map((n) => ({ ...n, type: n.type || "ai_response" })));
    setEdges((fj.edges || []).map((e, i) => ({
      id: e.id || `e_${i}`,
      source: e.source,
      target: e.target,
      sourceHandle: e.sourceHandle || null,
      label: e.label || "",
      animated: true,
      style: { stroke: "#555" },
    })));
    setSelectedNode(null);
    setDirty(false);
  }, [setNodes, setEdges]);

  const onConnect = useCallback((params) => {
    setEdges((eds) => addEdge({ ...params, animated: true, style: { stroke: "#555" } }, eds));
    setDirty(true);
  }, [setEdges]);

  const handleNodesChange = useCallback((changes) => {
    onNodesChange(changes);
    setDirty(true);
  }, [onNodesChange]);

  const handleEdgesChange = useCallback((changes) => {
    onEdgesChange(changes);
    setDirty(true);
  }, [onEdgesChange]);

  const addNode = useCallback((type) => {
    const id = nextNodeId();
    const defaults = {
      greeting: { message: "Hi! How can I help?" },
      question: { label: "New Question", question: "" },
      ai_response: { label: "AI Response" },
      condition: { label: "Condition", condition: "" },
      action: { label: "New Action", action: "" },
      handoff: { label: "Transfer to Team" },
    };
    const newNode = {
      id,
      type,
      data: defaults[type] || { label: type },
      position: { x: 200 + Math.random() * 100, y: 100 + Math.random() * 200 },
    };
    setNodes((nds) => [...nds, newNode]);
    setDirty(true);
  }, [setNodes]);

  const updateNodeData = useCallback((nodeId, newData) => {
    setNodes((nds) => nds.map((n) => n.id === nodeId ? { ...n, data: newData } : n));
    setDirty(true);
  }, [setNodes]);

  const deleteNode = useCallback((nodeId) => {
    setNodes((nds) => nds.filter((n) => n.id !== nodeId));
    setEdges((eds) => eds.filter((e) => e.source !== nodeId && e.target !== nodeId));
    setSelectedNode(null);
    setDirty(true);
  }, [setNodes, setEdges]);

  const onNodeClick = useCallback((_event, node) => {
    setSelectedNode(node);
  }, []);

  const onPaneClick = useCallback(() => {
    setSelectedNode(null);
  }, []);

  const saveFlow = useCallback(async () => {
    if (!selectedFlow || !user?.tenantId) return;
    setSaving(true);
    try {
      const flowJson = {
        nodes: nodes.map((n) => ({ id: n.id, type: n.type, data: n.data, position: n.position })),
        edges: edges.map((e) => ({ id: e.id, source: e.source, target: e.target, sourceHandle: e.sourceHandle, label: e.label })),
      };
      const updated = await updateChatFlow(user.tenantId, token, selectedFlow.id, {
        name: flowName.trim() || selectedFlow.name,
        flow_json: flowJson,
      });
      setSelectedFlow(updated);
      setFlows((prev) => prev.map((f) => f.id === updated.id ? updated : f));
      setDirty(false);
    } catch (err) {
      console.warn("Failed to save flow:", err.message);
    } finally {
      setSaving(false);
    }
  }, [selectedFlow, user?.tenantId, token, nodes, edges, flowName]);

  const toggleActive = useCallback(async (flow) => {
    if (!user?.tenantId) return;
    try {
      const updated = await updateChatFlow(user.tenantId, token, flow.id, { is_active: !flow.is_active });
      setFlows((prev) => prev.map((f) => {
        if (f.id === updated.id) return updated;
        if (updated.is_active && f.id !== updated.id) return { ...f, is_active: false };
        return f;
      }));
      if (selectedFlow?.id === updated.id) setSelectedFlow(updated);
    } catch (err) {
      console.warn("Failed to toggle flow:", err.message);
    }
  }, [user?.tenantId, token, selectedFlow]);

  const handleCreateFromTemplate = useCallback(async (index) => {
    if (!user?.tenantId) return;
    try {
      const newFlow = await createFlowFromTemplate(user.tenantId, token, index);
      setFlows((prev) => [newFlow, ...prev]);
      openFlow(newFlow);
      setShowTemplates(false);
    } catch (err) {
      console.warn("Failed to create from template:", err.message);
    }
  }, [user?.tenantId, token, openFlow]);

  const handleCreateBlank = useCallback(async () => {
    if (!user?.tenantId) return;
    try {
      const newFlow = await createChatFlow(user.tenantId, token, {
        name: "New Flow",
        flow_json: { nodes: [], edges: [] },
      });
      setFlows((prev) => [newFlow, ...prev]);
      openFlow(newFlow);
    } catch (err) {
      console.warn("Failed to create flow:", err.message);
    }
  }, [user?.tenantId, token, openFlow]);

  const handleDelete = useCallback(async (flowId) => {
    if (!user?.tenantId) return;
    try {
      await deleteChatFlow(user.tenantId, token, flowId);
      setFlows((prev) => prev.filter((f) => f.id !== flowId));
      if (selectedFlow?.id === flowId) {
        setSelectedFlow(null);
        setNodes([]);
        setEdges([]);
      }
    } catch (err) {
      console.warn("Failed to delete flow:", err.message);
    }
  }, [user?.tenantId, token, selectedFlow, setNodes, setEdges]);

  if (loading) return <SkeletonLoader />;

  // --- Flow Editor View ---
  if (selectedFlow) {
    const currentSelectedNode = selectedNode ? nodes.find((n) => n.id === selectedNode.id) : null;

    return (
      <div style={{ display: "flex", flexDirection: "column", height: "100%", gap: 0 }}>
        {/* Top bar */}
        <div style={{
          display: "flex", alignItems: "center", gap: 12, padding: "12px 20px",
          background: "var(--card-bg, #1e1e2e)", borderBottom: "1px solid var(--border, #333)",
          flexShrink: 0,
        }}>
          <button onClick={() => { setSelectedFlow(null); setSelectedNode(null); }} style={{
            background: "none", border: "none", color: "var(--text-secondary, #888)",
            cursor: "pointer", fontSize: 18, padding: "2px 8px",
          }}>←</button>
          <input value={flowName} onChange={(e) => { setFlowName(e.target.value); setDirty(true); }}
            style={{ ...inputStyle, flex: 1, maxWidth: 300 }} placeholder="Flow name" />
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginLeft: "auto" }}>
            {selectedFlow.is_active && (
              <span style={{ fontSize: 11, color: "#22c55e", background: "rgba(34,197,94,0.1)",
                padding: "3px 8px", borderRadius: 4, fontWeight: 600 }}>ACTIVE</span>
            )}
            <button onClick={() => toggleActive(selectedFlow)} style={{
              background: selectedFlow.is_active ? "rgba(239,68,68,0.15)" : "rgba(34,197,94,0.15)",
              color: selectedFlow.is_active ? "#ef4444" : "#22c55e",
              border: "none", borderRadius: 6, padding: "6px 14px", cursor: "pointer", fontSize: 12,
            }}>{selectedFlow.is_active ? "Deactivate" : "Activate"}</button>
            <button onClick={saveFlow} disabled={saving || !dirty} style={{
              background: dirty ? "var(--accent, #3b82f6)" : "rgba(59,130,246,0.3)",
              color: "#fff", border: "none", borderRadius: 6, padding: "6px 16px",
              cursor: dirty ? "pointer" : "default", fontSize: 12, fontWeight: 600, opacity: dirty ? 1 : 0.5,
            }}>{saving ? "Saving..." : dirty ? "Save" : "Saved"}</button>
          </div>
        </div>

        <div style={{ display: "flex", flex: 1, overflow: "hidden" }}>
          {/* Left: Node palette */}
          <div style={{
            width: 180, flexShrink: 0, padding: 12,
            background: "var(--card-bg, #1e1e2e)", borderRight: "1px solid var(--border, #333)",
            overflowY: "auto",
          }}>
            <div style={{ fontSize: 11, color: "var(--text-secondary, #888)", marginBottom: 8, fontWeight: 600, textTransform: "uppercase", letterSpacing: 1 }}>
              Add Node
            </div>
            {NODE_PALETTE.map((p) => (
              <button key={p.type} onClick={() => addNode(p.type)} style={{
                display: "flex", alignItems: "center", gap: 8, width: "100%",
                padding: "8px 10px", marginBottom: 4, background: "var(--bg, #0a0a0f)",
                border: `1px solid ${NODE_COLORS[p.type]?.border || "#555"}`,
                borderRadius: 8, color: "#fff", cursor: "pointer", textAlign: "left", fontSize: 12,
              }}>
                <span>{p.icon}</span>
                <div>
                  <div style={{ fontWeight: 600 }}>{p.label}</div>
                  <div style={{ fontSize: 10, opacity: 0.6 }}>{p.desc}</div>
                </div>
              </button>
            ))}
          </div>

          {/* Center: React Flow canvas */}
          <div style={{ flex: 1 }}>
            <ReactFlow
              nodes={nodes}
              edges={edges}
              onNodesChange={handleNodesChange}
              onEdgesChange={handleEdgesChange}
              onConnect={onConnect}
              onNodeClick={onNodeClick}
              onPaneClick={onPaneClick}
              nodeTypes={nodeTypesMemo}
              fitView
              proOptions={{ hideAttribution: true }}
              style={{ background: "#0a0a14" }}
            >
              <Controls position="bottom-left" style={{ background: "#1e1e2e", border: "1px solid #333", borderRadius: 8 }} />
              <MiniMap
                nodeColor={(n) => NODE_COLORS[n.type]?.border || "#555"}
                style={{ background: "#1a1a2e", border: "1px solid #333", borderRadius: 8 }}
                maskColor="rgba(0,0,0,0.6)"
              />
              <Background color="#222" gap={20} />
            </ReactFlow>
          </div>

          {/* Right: Node editor */}
          <div style={{
            width: 260, flexShrink: 0, padding: 12,
            background: "var(--card-bg, #1e1e2e)", borderLeft: "1px solid var(--border, #333)",
            overflowY: "auto",
          }}>
            {currentSelectedNode ? (
              <NodeEditor node={currentSelectedNode} onUpdate={updateNodeData} onDelete={deleteNode} />
            ) : (
              <div style={{ textAlign: "center", color: "var(--text-secondary, #888)", fontSize: 12, marginTop: 40 }}>
                <div style={{ fontSize: 32, marginBottom: 8 }}>🎯</div>
                <p>Click a node to edit it</p>
                <p style={{ marginTop: 8, fontSize: 11, opacity: 0.7 }}>
                  Drag between node handles to connect them
                </p>
              </div>
            )}
          </div>
        </div>
      </div>
    );
  }

  // --- Flow List View ---
  return (
    <div className="page-content" style={{ padding: 24 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20 }}>
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 700, color: "#fff", margin: 0 }}>Chat Flow Builder</h1>
          <p style={{ fontSize: 13, color: "var(--text-secondary, #888)", marginTop: 4 }}>
            Design custom conversation flows for your chat widget
          </p>
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          <button onClick={() => setShowTemplates(!showTemplates)} style={{
            background: "rgba(139,92,246,0.15)", color: "#8b5cf6", border: "none",
            borderRadius: 8, padding: "8px 16px", cursor: "pointer", fontSize: 13, fontWeight: 600,
          }}>From Template</button>
          <button onClick={handleCreateBlank} style={{
            background: "var(--accent, #3b82f6)", color: "#fff", border: "none",
            borderRadius: 8, padding: "8px 16px", cursor: "pointer", fontSize: 13, fontWeight: 600,
          }}>+ New Flow</button>
        </div>
      </div>

      {/* Templates Panel */}
      {showTemplates && (
        <div style={{
          display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(260px, 1fr))",
          gap: 12, marginBottom: 20, animation: "fadeIn 0.2s ease",
        }}>
          {templates.map((tpl, i) => (
            <div key={i} style={{
              background: "var(--card-bg, #1e1e2e)", border: "1px solid var(--border, #333)",
              borderRadius: 10, padding: 16, cursor: "pointer", transition: "border-color 0.2s",
            }}
              onClick={() => handleCreateFromTemplate(i)}
              onMouseEnter={(e) => e.currentTarget.style.borderColor = "#8b5cf6"}
              onMouseLeave={(e) => e.currentTarget.style.borderColor = "var(--border, #333)"}
            >
              <div style={{ fontSize: 14, fontWeight: 600, color: "#fff", marginBottom: 4 }}>{tpl.name}</div>
              <div style={{ fontSize: 12, color: "var(--text-secondary, #888)" }}>{tpl.description}</div>
              <div style={{ fontSize: 11, color: "#8b5cf6", marginTop: 8 }}>
                {tpl.flow_json?.nodes?.length || 0} nodes, {tpl.flow_json?.edges?.length || 0} connections
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Flow List */}
      {flows.length === 0 ? (
        <div style={{
          textAlign: "center", padding: 60, background: "var(--card-bg, #1e1e2e)",
          borderRadius: 12, border: "1px solid var(--border, #333)",
        }}>
          <div style={{ fontSize: 48, marginBottom: 12 }}>🔀</div>
          <h3 style={{ color: "#fff", marginBottom: 8 }}>No chat flows yet</h3>
          <p style={{ color: "var(--text-secondary, #888)", fontSize: 13, marginBottom: 16 }}>
            Create a flow from a template or start from scratch to customize your widget's conversation logic.
          </p>
          <button onClick={() => setShowTemplates(true)} style={{
            background: "var(--accent, #3b82f6)", color: "#fff", border: "none",
            borderRadius: 8, padding: "10px 20px", cursor: "pointer", fontSize: 13, fontWeight: 600,
          }}>Get Started with a Template</button>
        </div>
      ) : (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(300px, 1fr))", gap: 12 }}>
          {flows.map((flow) => (
            <div key={flow.id} style={{
              background: "var(--card-bg, #1e1e2e)", border: `1px solid ${flow.is_active ? "#22c55e" : "var(--border, #333)"}`,
              borderRadius: 10, padding: 16, cursor: "pointer", transition: "border-color 0.2s",
            }}
              onClick={() => openFlow(flow)}
              onMouseEnter={(e) => { if (!flow.is_active) e.currentTarget.style.borderColor = "var(--accent, #3b82f6)"; }}
              onMouseLeave={(e) => { if (!flow.is_active) e.currentTarget.style.borderColor = "var(--border, #333)"; }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <div style={{ fontSize: 15, fontWeight: 600, color: "#fff" }}>{flow.name}</div>
                {flow.is_active && (
                  <span style={{ fontSize: 10, color: "#22c55e", background: "rgba(34,197,94,0.1)",
                    padding: "2px 8px", borderRadius: 4, fontWeight: 600 }}>ACTIVE</span>
                )}
              </div>
              {flow.description && (
                <div style={{ fontSize: 12, color: "var(--text-secondary, #888)", marginTop: 4 }}>{flow.description}</div>
              )}
              <div style={{ display: "flex", gap: 12, marginTop: 10, fontSize: 11, color: "var(--text-secondary, #888)" }}>
                <span>{flow.flow_json?.nodes?.length || 0} nodes</span>
                <span>{flow.flow_json?.edges?.length || 0} connections</span>
              </div>
              <div style={{ display: "flex", gap: 6, marginTop: 10 }} onClick={(e) => e.stopPropagation()}>
                <button onClick={() => toggleActive(flow)} style={{
                  background: flow.is_active ? "rgba(239,68,68,0.1)" : "rgba(34,197,94,0.1)",
                  color: flow.is_active ? "#ef4444" : "#22c55e",
                  border: "none", borderRadius: 6, padding: "4px 10px", cursor: "pointer", fontSize: 11,
                }}>{flow.is_active ? "Deactivate" : "Activate"}</button>
                <button onClick={() => handleDelete(flow.id)} style={{
                  background: "rgba(239,68,68,0.1)", color: "#ef4444",
                  border: "none", borderRadius: 6, padding: "4px 10px", cursor: "pointer", fontSize: 11,
                }}>Delete</button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

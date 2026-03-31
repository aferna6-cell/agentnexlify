import { useState, useEffect, useCallback } from "react";
import { useAuth } from "../context/AuthContext";
import SkeletonLoader from "../components/SkeletonLoader";
import { fetchOrders, fetchOrderStats, updateOrderStatus } from "../utils/api/misc";

const STATUS_LABELS = {
  new: "New",
  confirmed: "Confirmed",
  preparing: "Preparing",
  ready: "Ready",
  delivered: "Delivered",
  cancelled: "Cancelled",
};

const STATUS_COLORS = {
  new: { color: "#3b82f6", bg: "rgba(59,130,246,0.1)" },
  confirmed: { color: "#8b5cf6", bg: "rgba(139,92,246,0.1)" },
  preparing: { color: "#f59e0b", bg: "rgba(245,158,11,0.1)" },
  ready: { color: "#22c55e", bg: "rgba(34,197,94,0.1)" },
  delivered: { color: "var(--text-muted)", bg: "var(--hover-overlay)" },
  cancelled: { color: "#ef4444", bg: "rgba(239,68,68,0.1)" },
};

const NEXT_STATUS = {
  new: "confirmed",
  confirmed: "preparing",
  preparing: "ready",
  ready: "delivered",
};

function timeAgo(dateStr) {
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

function formatCurrency(val) {
  return `$${parseFloat(val || 0).toFixed(2)}`;
}

export default function OrdersPage() {
  const { user, token } = useAuth();
  const [orders, setOrders] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [filterStatus, setFilterStatus] = useState("");
  const [selectedOrder, setSelectedOrder] = useState(null);
  const [updating, setUpdating] = useState(null);

  const load = useCallback(async () => {
    if (!user?.tenantId) return;
    try {
      const [ordersRes, statsRes] = await Promise.all([
        fetchOrders(user.tenantId, token, { status: filterStatus || undefined }),
        fetchOrderStats(user.tenantId, token),
      ]);
      setOrders(ordersRes.orders || []);
      setStats(statsRes);
    } catch (err) {
      console.warn("Failed to load orders:", err.message);
    } finally {
      setLoading(false);
    }
  }, [user?.tenantId, token, filterStatus]);

  useEffect(() => {
    setLoading(true);
    load();
  }, [load]);

  // Auto-refresh every 30s for near-real-time updates
  useEffect(() => {
    const interval = setInterval(load, 30000);
    return () => clearInterval(interval);
  }, [load]);

  const handleStatusChange = async (orderId, newStatus) => {
    setUpdating(orderId);
    try {
      const updated = await updateOrderStatus(user.tenantId, token, orderId, newStatus);
      setOrders((prev) => prev.map((o) => (o.id === orderId ? updated : o)));
      if (selectedOrder?.id === orderId) setSelectedOrder(updated);
      // Refresh stats
      fetchOrderStats(user.tenantId, token).then(setStats).catch((err) => console.warn("Order stats refresh failed:", err.message));
    } catch (err) {
      console.warn("Status update failed:", err.message);
    } finally {
      setUpdating(null);
    }
  };

  if (loading) return <SkeletonLoader />;

  const statCards = [
    { label: "New Orders", value: stats?.new_orders ?? 0, color: "#3b82f6" },
    { label: "Active", value: stats?.active_orders ?? 0, color: "#f59e0b" },
    { label: "Total Orders", value: stats?.total_orders ?? 0, color: "var(--text-secondary)" },
    { label: "Revenue", value: formatCurrency(stats?.total_revenue ?? 0), color: "#22c55e" },
  ];

  return (
    <div className="fade-in">
      <div className="page-header">
        <div>
          <h1>Orders</h1>
          <p>Manage incoming orders from your chat widget</p>
        </div>
        <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
          <select
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value)}
            style={{
              padding: "8px 12px", borderRadius: 8,
              border: "1px solid var(--border)",
              background: "var(--bg-secondary)", color: "var(--text-primary)",
              fontSize: "0.85rem",
            }}
          >
            <option value="">All Orders</option>
            {Object.entries(STATUS_LABELS).map(([k, v]) => (
              <option key={k} value={k}>{v}</option>
            ))}
          </select>
          <button className="btn-primary" onClick={() => { setLoading(true); load(); }} style={{
            background: "transparent", border: "1px solid var(--border)", color: "var(--text-primary)",
          }}>
            Refresh
          </button>
        </div>
      </div>

      {/* Stats Cards */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))", gap: 12, marginBottom: 24 }}>
        {statCards.map((card) => (
          <div key={card.label} style={{
            background: "var(--bg-secondary)", border: "1px solid var(--border)",
            borderRadius: 12, padding: "16px 20px",
          }}>
            <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginBottom: 4 }}>{card.label}</div>
            <div style={{ fontSize: "1.5rem", fontWeight: 700, color: card.color }}>{card.value}</div>
          </div>
        ))}
      </div>

      {/* Orders List */}
      {orders.length === 0 ? (
        <div style={{ textAlign: "center", padding: "60px 20px", color: "var(--text-muted)" }}>
          <div style={{ fontSize: "2rem", marginBottom: 12 }}>No orders yet</div>
          <p style={{ maxWidth: 400, margin: "0 auto" }}>
            Orders placed through your chat widget will appear here. Make sure your menu is set up and your AI knows to take orders.
          </p>
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          {orders.map((order) => {
            const items = Array.isArray(order.items_json) ? order.items_json : [];
            const statusColor = STATUS_COLORS[order.status] || STATUS_COLORS.new;
            const nextStatus = NEXT_STATUS[order.status];
            return (
              <div
                key={order.id}
                style={{
                  background: "var(--bg-secondary)", border: "1px solid var(--border)",
                  borderRadius: 12, padding: 16, cursor: "pointer",
                  borderLeft: `4px solid ${statusColor.color}`,
                }}
                onClick={() => setSelectedOrder(order)}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: 8 }}>
                  <div style={{ flex: 1, minWidth: 200 }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
                      <span style={{ fontWeight: 600, fontSize: "0.95rem" }}>
                        {order.customer_name || "Unknown Customer"}
                      </span>
                      <span style={{
                        display: "inline-block", padding: "2px 8px", borderRadius: 4,
                        fontSize: "0.7rem", fontWeight: 600,
                        color: statusColor.color, background: statusColor.bg,
                      }}>
                        {STATUS_LABELS[order.status] || order.status}
                      </span>
                      <span style={{
                        display: "inline-block", padding: "2px 8px", borderRadius: 4,
                        fontSize: "0.7rem", fontWeight: 500,
                        color: "var(--text-muted)", background: "var(--hover-overlay)",
                        textTransform: "capitalize",
                      }}>
                        {order.order_type}
                      </span>
                    </div>
                    <div style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>
                      {items.length} item{items.length !== 1 ? "s" : ""}: {items.slice(0, 3).map((i) => i.name || i.item_name || "item").join(", ")}
                      {items.length > 3 ? ` +${items.length - 3} more` : ""}
                    </div>
                  </div>
                  <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                    <div style={{ textAlign: "right" }}>
                      <div style={{ fontWeight: 700, fontSize: "1.1rem", color: "var(--green, #22c55e)" }}>
                        {formatCurrency(order.total)}
                      </div>
                      <div style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
                        {timeAgo(order.created_at)}
                      </div>
                    </div>
                    {nextStatus && (
                      <button
                        onClick={(e) => { e.stopPropagation(); handleStatusChange(order.id, nextStatus); }}
                        disabled={updating === order.id}
                        className="btn-primary"
                        style={{ fontSize: "0.8rem", padding: "6px 14px", whiteSpace: "nowrap" }}
                      >
                        {updating === order.id ? "..." : STATUS_LABELS[nextStatus]}
                      </button>
                    )}
                    {order.status !== "cancelled" && order.status !== "delivered" && (
                      <button
                        onClick={(e) => { e.stopPropagation(); handleStatusChange(order.id, "cancelled"); }}
                        disabled={updating === order.id}
                        style={{
                          background: "none", border: "1px solid var(--border)", borderRadius: 6,
                          padding: "6px 10px", color: "var(--red, #ef4444)", cursor: "pointer",
                          fontSize: "0.8rem",
                        }}
                      >
                        Cancel
                      </button>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Order Detail Modal */}
      {selectedOrder && (
        <div
          style={{
            position: "fixed", inset: 0, background: "rgba(0,0,0,0.5)",
            display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000,
          }}
          onClick={() => setSelectedOrder(null)}
        >
          <div
            style={{
              background: "var(--bg-primary)", borderRadius: 12, padding: 24,
              width: "90%", maxWidth: 520, maxHeight: "80vh", overflowY: "auto",
              border: "1px solid var(--border)",
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 16 }}>
              <div>
                <h3 style={{ margin: 0 }}>Order Details</h3>
                <div style={{ fontSize: "0.8rem", color: "var(--text-muted)", marginTop: 4 }}>
                  {new Date(selectedOrder.created_at).toLocaleString()}
                </div>
              </div>
              <span style={{
                padding: "4px 12px", borderRadius: 6, fontSize: "0.8rem", fontWeight: 600,
                color: (STATUS_COLORS[selectedOrder.status] || STATUS_COLORS.new).color,
                background: (STATUS_COLORS[selectedOrder.status] || STATUS_COLORS.new).bg,
              }}>
                {STATUS_LABELS[selectedOrder.status] || selectedOrder.status}
              </span>
            </div>

            {/* Customer Info */}
            <div style={{
              background: "var(--bg-secondary)", borderRadius: 8, padding: 12, marginBottom: 16,
              border: "1px solid var(--border)",
            }}>
              <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginBottom: 8, fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.05em" }}>Customer</div>
              <div style={{ fontSize: "0.9rem", fontWeight: 600 }}>{selectedOrder.customer_name || "Not provided"}</div>
              {selectedOrder.customer_phone && (
                <div style={{ fontSize: "0.85rem", color: "var(--text-secondary)", marginTop: 2 }}>{selectedOrder.customer_phone}</div>
              )}
              {selectedOrder.customer_email && (
                <div style={{ fontSize: "0.85rem", color: "var(--text-secondary)", marginTop: 2 }}>{selectedOrder.customer_email}</div>
              )}
              <div style={{ marginTop: 6 }}>
                <span style={{
                  display: "inline-block", padding: "2px 8px", borderRadius: 4,
                  fontSize: "0.75rem", fontWeight: 500, textTransform: "capitalize",
                  color: selectedOrder.order_type === "delivery" ? "#f59e0b" : "#3b82f6",
                  background: selectedOrder.order_type === "delivery" ? "rgba(245,158,11,0.1)" : "rgba(59,130,246,0.1)",
                }}>
                  {selectedOrder.order_type}
                </span>
              </div>
              {selectedOrder.delivery_address && (
                <div style={{ fontSize: "0.85rem", color: "var(--text-secondary)", marginTop: 6 }}>
                  Delivery: {selectedOrder.delivery_address}
                </div>
              )}
            </div>

            {/* Items */}
            <div style={{
              background: "var(--bg-secondary)", borderRadius: 8, padding: 12, marginBottom: 16,
              border: "1px solid var(--border)",
            }}>
              <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginBottom: 8, fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.05em" }}>Items</div>
              {(Array.isArray(selectedOrder.items_json) ? selectedOrder.items_json : []).map((item, idx) => (
                <div key={idx} style={{
                  display: "flex", justifyContent: "space-between", alignItems: "center",
                  padding: "6px 0", borderBottom: idx < selectedOrder.items_json.length - 1 ? "1px solid var(--border)" : "none",
                }}>
                  <div>
                    <span style={{ fontWeight: 500 }}>{item.name || item.item_name || "Item"}</span>
                    {item.quantity && item.quantity > 1 && (
                      <span style={{ color: "var(--text-muted)", fontSize: "0.8rem", marginLeft: 6 }}>x{item.quantity}</span>
                    )}
                  </div>
                  <span style={{ fontWeight: 600 }}>{formatCurrency(item.price || item.total || 0)}</span>
                </div>
              ))}
              <div style={{ borderTop: "2px solid var(--border)", marginTop: 8, paddingTop: 8 }}>
                {selectedOrder.subtotal > 0 && selectedOrder.subtotal !== selectedOrder.total && (
                  <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.85rem", color: "var(--text-secondary)" }}>
                    <span>Subtotal</span>
                    <span>{formatCurrency(selectedOrder.subtotal)}</span>
                  </div>
                )}
                {selectedOrder.tax > 0 && (
                  <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.85rem", color: "var(--text-secondary)" }}>
                    <span>Tax</span>
                    <span>{formatCurrency(selectedOrder.tax)}</span>
                  </div>
                )}
                <div style={{ display: "flex", justifyContent: "space-between", fontWeight: 700, fontSize: "1.1rem", marginTop: 4 }}>
                  <span>Total</span>
                  <span style={{ color: "var(--green, #22c55e)" }}>{formatCurrency(selectedOrder.total)}</span>
                </div>
              </div>
            </div>

            {/* Notes */}
            {selectedOrder.notes && (
              <div style={{
                background: "var(--bg-secondary)", borderRadius: 8, padding: 12, marginBottom: 16,
                border: "1px solid var(--border)",
              }}>
                <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginBottom: 4, fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.05em" }}>Notes</div>
                <div style={{ fontSize: "0.85rem", color: "var(--text-secondary)" }}>{selectedOrder.notes}</div>
              </div>
            )}

            {/* Actions */}
            <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
              {selectedOrder.status !== "cancelled" && selectedOrder.status !== "delivered" && (
                <button
                  onClick={() => { handleStatusChange(selectedOrder.id, "cancelled"); }}
                  disabled={updating === selectedOrder.id}
                  style={{
                    background: "none", border: "1px solid var(--border)", borderRadius: 8,
                    padding: "8px 16px", color: "var(--red, #ef4444)", cursor: "pointer",
                  }}
                >
                  Cancel Order
                </button>
              )}
              {NEXT_STATUS[selectedOrder.status] && (
                <button
                  className="btn-primary"
                  onClick={() => { handleStatusChange(selectedOrder.id, NEXT_STATUS[selectedOrder.status]); }}
                  disabled={updating === selectedOrder.id}
                >
                  {updating === selectedOrder.id ? "Updating..." : `Mark ${STATUS_LABELS[NEXT_STATUS[selectedOrder.status]]}`}
                </button>
              )}
              <button
                onClick={() => setSelectedOrder(null)}
                style={{
                  background: "transparent", border: "1px solid var(--border)", borderRadius: 8,
                  padding: "8px 16px", color: "var(--text-primary)", cursor: "pointer",
                }}
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

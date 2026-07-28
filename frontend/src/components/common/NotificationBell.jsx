import React, { useCallback, useEffect, useMemo, useState } from "react";
import { Bell, Check, CheckCheck, ExternalLink, Loader2, X } from "lucide-react";
import {
  DropdownMenu, DropdownMenuTrigger, DropdownMenuContent,
} from "@/components/ui/dropdown-menu";
import { toast } from "sonner";
import { Link } from "react-router-dom";

const API = process.env.REACT_APP_BACKEND_URL || "";
const POLL_MS = 30000;

const SEVERITY_STYLES = {
  info:     { dot: "bg-blue-500",  label: "text-blue-600"  },
  success:  { dot: "bg-emerald-500", label: "text-emerald-600" },
  warning:  { dot: "bg-amber-500", label: "text-amber-600" },
  critical: { dot: "bg-rose-500",  label: "text-rose-600"  },
};

const ENTITY_LINKS = {
  order: (id) => `/app/order-trace?id=${encodeURIComponent(id)}`,
  primary_order: (id) => `/app/primary-orders?id=${encodeURIComponent(id)}`,
  secondary_order: (id) => `/app/secondary-orders?id=${encodeURIComponent(id)}`,
  invoice: () => `/app/invoices`,
  payment: () => `/app/payments`,
  claim: () => `/app/claims`,
  return: () => `/app/returns`,
  batch: () => `/app/batches`,
  approval: () => `/app/approval-engine`,
  approvals: () => `/app/approvals`,
  inventory: () => `/app/inventory`,
  expiry: () => `/app/expiry`,
  finance: () => `/app/outstanding`,
  billing: () => `/app/invoices`,
  claims: () => `/app/claims`,
};

function formatTime(iso) {
  try {
    const d = new Date(iso);
    const diff = (Date.now() - d.getTime()) / 1000;
    if (diff < 60) return "just now";
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
    if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
    if (diff < 604800) return `${Math.floor(diff / 86400)}d ago`;
    return d.toLocaleDateString();
  } catch (e) { return ""; }
}

async function api(path, opts = {}) {
  const token = localStorage.getItem("go_oil_token");
  const resp = await fetch(`${API}/api${path}`, {
    ...opts,
    headers: {
      "Content-Type": "application/json",
      Authorization: token ? `Bearer ${token}` : "",
      ...(opts.headers || {}),
    },
    credentials: "include",
  });
  if (!resp.ok) throw new Error(await resp.text());
  const ct = resp.headers.get("content-type") || "";
  return ct.includes("application/json") ? resp.json() : resp.text();
}

export default function NotificationBell() {
  const [unread, setUnread] = useState(0);
  const [items, setItems] = useState([]);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);

  const fetchUnread = useCallback(async () => {
    try {
      const j = await api("/notifications/unread-count");
      setUnread(j.unread || 0);
    } catch (e) { /* silent; user may be logged out */ }
  }, []);

  const fetchItems = useCallback(async () => {
    setLoading(true);
    try {
      const j = await api("/notifications/?limit=20");
      setItems(j.data || []);
    } catch (e) {
      toast.error("Could not load notifications");
    } finally { setLoading(false); }
  }, []);

  useEffect(() => {
    fetchUnread();
    const t = setInterval(fetchUnread, POLL_MS);
    return () => clearInterval(t);
  }, [fetchUnread]);

  useEffect(() => {
    if (open) fetchItems();
  }, [open, fetchItems]);

  const markRead = async (id) => {
    try {
      await api(`/notifications/mark-read/${id}`, { method: "POST" });
      setItems((prev) => prev.map((n) => (n.id === id ? { ...n, read: true } : n)));
      setUnread((u) => Math.max(0, u - 1));
    } catch (e) { /* ignore */ }
  };

  const markAllRead = async () => {
    try {
      await api("/notifications/mark-all-read", { method: "POST" });
      setItems((prev) => prev.map((n) => ({ ...n, read: true })));
      setUnread(0);
      toast.success("All notifications marked read");
    } catch (e) { toast.error("Could not mark all read"); }
  };

  const remove = async (id) => {
    try {
      await api(`/notifications/${id}`, { method: "DELETE" });
      setItems((prev) => prev.filter((n) => n.id !== id));
      fetchUnread();
    } catch (e) { /* ignore */ }
  };

  const badge = useMemo(() => {
    if (!unread) return null;
    return unread > 99 ? "99+" : String(unread);
  }, [unread]);

  return (
    <DropdownMenu open={open} onOpenChange={setOpen}>
      <DropdownMenuTrigger asChild>
        <button
          className="relative h-10 w-10 rounded-full border border-[#E5E7EB] bg-white flex items-center justify-center text-ink-muted hover:text-ink hover:bg-canvas transition"
          data-testid="topbar-notifications"
          aria-label="Notifications"
        >
          <Bell size={16} />
          {badge && (
            <span
              className="absolute -top-1 -right-1 min-w-[18px] h-[18px] px-1 rounded-full bg-rose-500 text-white text-[10px] font-semibold flex items-center justify-center"
              data-testid="notif-unread-count"
            >
              {badge}
            </span>
          )}
        </button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-96 p-0" data-testid="notif-dropdown">
        <div className="flex items-center justify-between px-4 py-3 border-b border-[#E5E7EB]">
          <div>
            <div className="text-sm font-semibold text-ink">Notifications</div>
            <div className="text-xs text-ink-muted">{unread} unread</div>
          </div>
          <div className="flex items-center gap-1">
            <button
              onClick={markAllRead}
              disabled={unread === 0}
              className="text-xs px-2 py-1 rounded hover:bg-canvas text-ink-muted hover:text-ink flex items-center gap-1 disabled:opacity-40"
              data-testid="notif-mark-all"
            >
              <CheckCheck size={12} /> Mark all read
            </button>
            <Link
              to="/app/notifications"
              className="text-xs px-2 py-1 rounded hover:bg-canvas text-ink-muted hover:text-ink"
              onClick={() => setOpen(false)}
            >
              View all
            </Link>
          </div>
        </div>
        <div className="max-h-[420px] overflow-y-auto" data-testid="notif-list">
          {loading && (
            <div className="p-6 text-center text-ink-muted text-sm flex items-center justify-center gap-2">
              <Loader2 size={14} className="animate-spin" /> Loading…
            </div>
          )}
          {!loading && items.length === 0 && (
            <div className="p-8 text-center text-ink-muted text-sm">
              <Bell size={20} className="mx-auto mb-2 opacity-40" />
              You're all caught up.
            </div>
          )}
          {!loading && items.map((n) => {
            const sev = SEVERITY_STYLES[n.severity] || SEVERITY_STYLES.info;
            const link = n.entity_type && ENTITY_LINKS[n.entity_type]
              ? ENTITY_LINKS[n.entity_type](n.entity_id)
              : (ENTITY_LINKS[n.category] ? ENTITY_LINKS[n.category](n.entity_id) : null);
            return (
              <div
                key={n.id}
                className={`px-4 py-3 border-b border-[#F3F4F6] hover:bg-canvas transition group ${
                  !n.read ? "bg-blue-50/30" : ""
                }`}
                data-testid={`notif-item-${n.id}`}
              >
                <div className="flex items-start gap-2.5">
                  <span className={`mt-1.5 w-2 h-2 rounded-full flex-shrink-0 ${sev.dot}`} />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between gap-2">
                      <div className={`text-sm font-semibold truncate ${!n.read ? "text-ink" : "text-ink-muted"}`}>
                        {n.title}
                      </div>
                      <div className="text-[10px] text-ink-muted whitespace-nowrap">
                        {formatTime(n.created_at)}
                      </div>
                    </div>
                    <div className="text-xs text-ink-muted mt-0.5 line-clamp-2">{n.body}</div>
                    <div className="flex items-center gap-1.5 mt-1.5 opacity-0 group-hover:opacity-100 transition">
                      {!n.read && (
                        <button
                          onClick={() => markRead(n.id)}
                          className="text-[10px] px-1.5 py-0.5 rounded hover:bg-white text-ink-muted flex items-center gap-1"
                        >
                          <Check size={10} /> Mark read
                        </button>
                      )}
                      {link && (
                        <Link
                          to={link}
                          onClick={() => { markRead(n.id); setOpen(false); }}
                          className="text-[10px] px-1.5 py-0.5 rounded hover:bg-white text-ink-muted flex items-center gap-1"
                        >
                          <ExternalLink size={10} /> Open
                        </Link>
                      )}
                      <button
                        onClick={() => remove(n.id)}
                        className="text-[10px] px-1.5 py-0.5 rounded hover:bg-white text-ink-muted flex items-center gap-1"
                      >
                        <X size={10} /> Dismiss
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

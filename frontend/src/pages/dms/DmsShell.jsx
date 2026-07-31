import React, { useEffect, useState, useCallback } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { dms } from "./api";
import { ImpersonationBanner } from "./OwnerUsersPage";
import SalespersonGpsPinger from "@/components/SalespersonGpsPinger";
import { Bell, LogOut, Menu, X, Package, Boxes, Handshake, ShoppingCart, LayoutDashboard, Receipt, Warehouse, ScrollText, Store, MapPin, ClipboardList, Users, TrendingUp, ChevronRight } from "lucide-react";

const ICONS = { LayoutDashboard, Boxes, Package, Handshake, ShoppingCart, Warehouse, Receipt, ScrollText, Store, MapPin, ClipboardList, Users, TrendingUp };

const NAV_BY_ROLE = {
  owner: [
    { label: "Dashboard",       to: "/dms",                     icon: "LayoutDashboard" },
    { label: "Categories",      to: "/dms/owner/categories",    icon: "Boxes" },
    { label: "Products",        to: "/dms/owner/products",      icon: "Package" },
    { label: "Distributors",    to: "/dms/owner/distributors",  icon: "Handshake" },
    { label: "Primary Orders",  to: "/dms/owner/primary-orders",icon: "ShoppingCart" },
    { label: "Owner Inventory", to: "/dms/owner/inventory",     icon: "Warehouse" },
    { label: "Primary Ledger",  to: "/dms/owner/ledger",        icon: "ScrollText" },
    { label: "Retailer Prices", to: "/dms/owner/retailer-prices", icon: "TrendingUp" },
    { label: "User Management", to: "/dms/owner/users",         icon: "Users" },
    { label: "Live Tracking",   to: "/dms/owner/live-tracking", icon: "MapPin" },
    { label: "TL Performance",  to: "/dms/owner/tl-performance", icon: "TrendingUp" },
    { label: "Sales Visibility",to: "/dms/owner/distributor-sales", icon: "Store" },
  ],
  owner_accountant: [
    { label: "Dashboard",       to: "/dms",                     icon: "LayoutDashboard" },
    { label: "Primary Ledger",  to: "/dms/owner/ledger",        icon: "ScrollText" },
    { label: "Primary Orders",  to: "/dms/owner/primary-orders",icon: "Receipt" },
    { label: "Owner Inventory", to: "/dms/owner/inventory",     icon: "Warehouse" },
  ],
  distributor: [
    { label: "Dashboard",         to: "/dms",                            icon: "LayoutDashboard" },
    { label: "Browse & Order",    to: "/dms/distributor/browse",         icon: "ShoppingCart" },
    { label: "My Primary Orders", to: "/dms/distributor/my-orders",      icon: "ClipboardList" },
    { label: "My Stock",          to: "/dms/distributor/stock",          icon: "Warehouse" },
    { label: "My Retailers",      to: "/dms/distributor/retailers",      icon: "Store" },
    { label: "Retailer Orders",   to: "/dms/distributor/retail-orders",  icon: "ShoppingCart" },
    { label: "Secondary Ledger",  to: "/dms/distributor/sec-ledger",     icon: "ScrollText" },
    { label: "Primary Ledger",    to: "/dms/distributor/ledger",         icon: "ScrollText" },
  ],
  distributor_accountant: [
    { label: "Dashboard",         to: "/dms",                            icon: "LayoutDashboard" },
    { label: "Secondary Ledger",  to: "/dms/distributor/sec-ledger",     icon: "ScrollText" },
    { label: "Primary Ledger",    to: "/dms/distributor/ledger",         icon: "ScrollText" },
    { label: "Retailer Orders",   to: "/dms/distributor/retail-orders",  icon: "ClipboardList" },
    { label: "Primary Orders",    to: "/dms/distributor/my-orders",      icon: "ClipboardList" },
  ],
  retailer: [
    { label: "Dashboard",       to: "/dms",                    icon: "LayoutDashboard" },
    { label: "Browse & Order",  to: "/dms/retailer/browse",    icon: "ShoppingCart" },
    { label: "My Orders",       to: "/dms/retailer/my-orders", icon: "ClipboardList" },
  ],
  salesperson: [
    { label: "Dashboard",       to: "/dms",                            icon: "LayoutDashboard" },
    { label: "My Distributors", to: "/dms/salesperson/distributors",   icon: "Handshake" },
    { label: "My Retailers",    to: "/dms/salesperson/retailers",      icon: "Store" },
    { label: "New Retailer",    to: "/dms/salesperson/new-retailer",   icon: "MapPin" },
  ],
  team_leader: [
    { label: "Dashboard",       to: "/dms",                             icon: "LayoutDashboard" },
    { label: "My Distributors", to: "/dms/team-leader/distributors",    icon: "Handshake" },
    { label: "My Salespersons", to: "/dms/team-leader/salespersons",    icon: "Users" },
    { label: "Order Monitoring",to: "/dms/team-leader/orders",          icon: "ShoppingCart" },
    { label: "My Retailers",    to: "/dms/team-leader/retailers",       icon: "Store" },
    { label: "Live Tracking",   to: "/dms/team-leader/live-tracking",   icon: "MapPin" },
    { label: "Attendance",      to: "/dms/team-leader/attendance",      icon: "ClipboardList" },
    { label: "Assignments",     to: "/dms/team-leader/assignments",     icon: "Users" },
  ],
  regional_manager: [
    { label: "Dashboard",         to: "/dms",                                    icon: "LayoutDashboard" },
    { label: "Team Leaders",      to: "/dms/regional-manager/team-leaders",      icon: "Users" },
    { label: "Region Performance",to: "/dms/regional-manager/performance",       icon: "TrendingUp" },
    { label: "Distributors",      to: "/dms/regional-manager/distributors",      icon: "Handshake" },
    { label: "Salespersons",      to: "/dms/regional-manager/salespersons",      icon: "Users" },
    { label: "Live Tracking",     to: "/dms/regional-manager/live-tracking",     icon: "MapPin" },
  ],
  super_admin: [
    { label: "Dashboard",       to: "/dms",                     icon: "LayoutDashboard" },
    { label: "All Users",       to: "/dms/admin/users",         icon: "Users" },
    { label: "Categories",      to: "/dms/owner/categories",    icon: "Boxes" },
    { label: "Products",        to: "/dms/owner/products",      icon: "Package" },
    { label: "Distributors",    to: "/dms/owner/distributors",  icon: "Handshake" },
    { label: "Primary Orders",  to: "/dms/owner/primary-orders",icon: "ShoppingCart" },
    { label: "Owner Inventory", to: "/dms/owner/inventory",     icon: "Warehouse" },
    { label: "Primary Ledger",  to: "/dms/owner/ledger",        icon: "ScrollText" },
  ],
};

const ROLE_LABEL = {
  owner: "Company Owner", owner_accountant: "Owner Accountant",
  distributor: "Distributor", distributor_accountant: "Distributor Accountant",
  retailer: "Retailer", salesperson: "Salesperson",
  team_leader: "Team Leader", regional_manager: "Regional Manager",
  super_admin: "Super Admin",
};

function NotificationsBell() {
  const [open, setOpen] = useState(false);
  const [data, setData] = useState({ data: [], unread: 0 });
  const nav = useNavigate();

  const refresh = useCallback(async () => {
    try {
      const d = await dms.notifications();
      setData(d);
    } catch { /* ignore */ }
  }, []);

  useEffect(() => {
    refresh();
    const t = setInterval(refresh, 30000);
    return () => clearInterval(t);
  }, [refresh]);

  const click = async (n) => {
    try { await dms.markRead(n.id); } catch {}
    setOpen(false);
    if (n.link) nav(n.link.replace("/dms", "/dms"));
    refresh();
  };

  return (
    <div className="relative">
      <button onClick={() => setOpen(!open)} className="relative p-2 rounded-lg hover:bg-slate-100" data-testid="notif-bell">
        <Bell size={20} className="text-slate-600" />
        {data.unread > 0 && (
          <span className="absolute top-0 right-0 -mt-0.5 -mr-0.5 bg-rose-600 text-white text-[10px] font-bold rounded-full min-w-[18px] h-[18px] flex items-center justify-center px-1">{data.unread}</span>
        )}
      </button>
      {open && (
        <>
          <div className="fixed inset-0 z-40" onClick={() => setOpen(false)} />
          <div className="absolute right-0 mt-2 w-96 max-h-[70vh] overflow-y-auto bg-white rounded-xl border border-slate-200 shadow-2xl z-50">
            <div className="px-4 py-3 border-b border-slate-100 flex items-center justify-between">
              <div className="font-semibold text-slate-900">Notifications</div>
              {data.unread > 0 && (
                <button onClick={async () => { await dms.markAllRead(); refresh(); }} className="text-xs text-teal-700 hover:underline">Mark all read</button>
              )}
            </div>
            {data.data.length === 0 && (
              <div className="p-6 text-center text-sm text-slate-500">No notifications yet</div>
            )}
            {data.data.map(n => (
              <button key={n.id} onClick={() => click(n)} className={`w-full text-left px-4 py-3 border-b border-slate-50 hover:bg-slate-50 flex gap-3 ${n.read ? "opacity-60" : ""}`}>
                <div className={`mt-1 h-2 w-2 rounded-full ${n.read ? "bg-slate-300" : "bg-teal-500"}`} />
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-medium text-slate-900">{n.title}</div>
                  <div className="text-xs text-slate-500 mt-0.5">{n.body}</div>
                </div>
              </button>
            ))}
          </div>
        </>
      )}
    </div>
  );
}

export default function DmsShell({ children }) {
  const { user, logout } = useAuth();
  const location = useLocation();
  const [mobileOpen, setMobileOpen] = useState(false);
  const role = user?.role || "owner";
  const items = NAV_BY_ROLE[role] || NAV_BY_ROLE.owner;

  const isActive = (to) => (to === "/dms" ? location.pathname === "/dms" : location.pathname.startsWith(to));

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col">
      <ImpersonationBanner />
      <SalespersonGpsPinger />
      <div className="flex-1 flex">
      {/* Sidebar - Desktop */}
      <aside className="hidden lg:flex flex-col w-60 bg-white border-r border-slate-200 sticky top-0 h-screen">
        <div className="h-16 flex items-center px-5 border-b border-slate-100">
          <div className="flex items-center gap-2">
            <div className="h-8 w-8 rounded-lg bg-gradient-to-br from-teal-600 to-teal-800 flex items-center justify-center text-white font-bold text-sm">B</div>
            <div>
              <div className="font-bold text-slate-900 leading-none">Bharat Oil</div>
              <div className="text-[10px] text-slate-500 uppercase tracking-wider">DMS</div>
            </div>
          </div>
        </div>
        <nav className="flex-1 overflow-y-auto p-3 space-y-1">
          {items.map(it => {
            const Icon = ICONS[it.icon] || Package;
            const active = isActive(it.to);
            return (
              <Link key={it.to} to={it.to} className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm ${active ? "bg-teal-50 text-teal-800 font-semibold" : "text-slate-700 hover:bg-slate-50"}`} data-testid={`nav-${it.label.toLowerCase().replace(/\s+/g, "-")}`}>
                <Icon size={18} className={active ? "text-teal-700" : "text-slate-400"} />
                {it.label}
                {active && <ChevronRight size={14} className="ml-auto text-teal-500" />}
              </Link>
            );
          })}
        </nav>
        <div className="p-4 border-t border-slate-100">
          <div className="flex items-center gap-3">
            <div className="h-9 w-9 rounded-full bg-teal-100 text-teal-800 font-semibold flex items-center justify-center text-sm">{(user?.name || "?").split(" ").map(w => w[0]).join("").slice(0, 2).toUpperCase()}</div>
            <div className="flex-1 min-w-0">
              <div className="text-sm font-medium text-slate-900 truncate">{user?.name}</div>
              <div className="text-[11px] text-slate-500 truncate">{ROLE_LABEL[role]}</div>
            </div>
            <button onClick={logout} className="p-1.5 rounded-lg text-slate-500 hover:bg-rose-50 hover:text-rose-600" title="Log out" data-testid="logout-btn">
              <LogOut size={16} />
            </button>
          </div>
        </div>
      </aside>

      {/* Mobile sidebar */}
      {mobileOpen && (
        <div className="lg:hidden fixed inset-0 z-50">
          <div className="absolute inset-0 bg-slate-900/50" onClick={() => setMobileOpen(false)} />
          <aside className="absolute left-0 top-0 bottom-0 w-64 bg-white flex flex-col">
            <div className="h-16 flex items-center justify-between px-4 border-b border-slate-100">
              <div className="flex items-center gap-2">
                <div className="h-8 w-8 rounded-lg bg-gradient-to-br from-teal-600 to-teal-800 flex items-center justify-center text-white font-bold text-sm">B</div>
                <div className="font-bold text-slate-900">Bharat Oil DMS</div>
              </div>
              <button onClick={() => setMobileOpen(false)}><X size={20} /></button>
            </div>
            <nav className="flex-1 overflow-y-auto p-3 space-y-1">
              {items.map(it => {
                const Icon = ICONS[it.icon] || Package;
                const active = isActive(it.to);
                return (
                  <Link key={it.to} to={it.to} onClick={() => setMobileOpen(false)} className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm ${active ? "bg-teal-50 text-teal-800 font-semibold" : "text-slate-700 hover:bg-slate-50"}`}>
                    <Icon size={18} />
                    {it.label}
                  </Link>
                );
              })}
            </nav>
            <div className="p-3 border-t border-slate-100">
              <button onClick={logout} className="w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm text-rose-600 hover:bg-rose-50">
                <LogOut size={16} /> Log out
              </button>
            </div>
          </aside>
        </div>
      )}

      {/* Main */}
      <div className="flex-1 flex flex-col min-w-0">
        <header className="h-16 bg-white border-b border-slate-200 flex items-center px-4 lg:px-6 sticky top-0 z-30">
          <button className="lg:hidden p-2" onClick={() => setMobileOpen(true)}><Menu size={22} /></button>
          <div className="flex-1" />
          <div className="flex items-center gap-2">
            <NotificationsBell />
          </div>
        </header>
        <main className="flex-1 p-4 lg:p-6">{children}</main>
      </div>
      </div>
    </div>
  );
}

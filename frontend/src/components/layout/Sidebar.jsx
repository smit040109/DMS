import React, { useMemo } from "react";
import { NavLink, useLocation } from "react-router-dom";
import * as Icons from "lucide-react";
import { filterNavForRole } from "@/lib/nav";
import GoldLogo from "@/components/common/GoldLogo";
import { useAuth } from "@/context/AuthContext";
import { ChevronsLeft } from "lucide-react";

export default function Sidebar({ collapsed, onToggle }) {
  const { user } = useAuth();
  const location = useLocation();
  const groups = useMemo(() => filterNavForRole(user?.role || "customer"), [user?.role]);

  return (
    <aside
      className={`bg-white border-r border-[#E5E7EB] h-screen sticky top-0 flex flex-col transition-all duration-200 ${
        collapsed ? "w-[74px]" : "w-[260px]"
      }`}
      data-testid="sidebar"
    >
      <div className="px-4 h-16 flex items-center border-b border-[#E5E7EB] justify-between">
        {!collapsed ? (
          <GoldLogo size={34} />
        ) : (
          <GoldLogo size={34} showText={false} />
        )}
        <button
          onClick={onToggle}
          className="rounded-md p-1.5 text-ink-muted hover:bg-canvas hover:text-ink transition"
          data-testid="sidebar-collapse"
          aria-label="Toggle sidebar"
        >
          <ChevronsLeft size={16} className={`transition ${collapsed ? "rotate-180" : ""}`} />
        </button>
      </div>

      <nav className="flex-1 overflow-y-auto px-3 py-4">
        {groups.map((group) => (
          <div key={group.label} className="mb-5">
            {!collapsed && (
              <div className="text-[10px] uppercase tracking-[0.22em] text-ink-muted font-semibold px-3 mb-2">
                {group.label}
              </div>
            )}
            <ul className="space-y-0.5">
              {group.items.map((it) => {
                const Icon = Icons[it.icon] || Icons.Circle;
                const isActive =
                  location.pathname === it.to ||
                  (it.to !== "/app" && location.pathname.startsWith(it.to));
                return (
                  <li key={it.key}>
                    <NavLink
                      to={it.to}
                      end={it.to === "/app"}
                      className={`group relative flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
                        isActive
                          ? "bg-gold-tint/60 text-ink"
                          : "text-ink-muted hover:bg-canvas hover:text-ink"
                      }`}
                      data-testid={`nav-${it.key}`}
                    >
                      {isActive && (
                        <span className="absolute left-0 top-1/2 -translate-y-1/2 h-6 w-[3px] rounded-r bg-gold" />
                      )}
                      <Icon size={17} strokeWidth={1.6} className={isActive ? "text-gold-dark" : ""} />
                      {!collapsed && <span className="truncate">{it.label}</span>}
                    </NavLink>
                  </li>
                );
              })}
            </ul>
          </div>
        ))}
      </nav>

      {!collapsed && (
        <div className="mx-3 mb-3 rounded-lg border border-emerald-100 bg-emerald-50/60 p-3">
          <div className="flex items-center gap-2 text-xs font-semibold text-emerald-800">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
            System healthy
          </div>
          <div className="mt-1 text-[11px] text-emerald-700/80">Last sync 4 mins ago</div>
        </div>
      )}
    </aside>
  );
}

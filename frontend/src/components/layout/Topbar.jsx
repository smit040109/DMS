import React, { useState } from "react";
import { Search, Sparkles, ChevronDown, LogOut, User as UserIcon, Menu } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuLabel,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuGroup,
} from "@/components/ui/dropdown-menu";
import { useAuth } from "@/context/AuthContext";
import { ROLE_LABELS } from "@/lib/nav";
import NotificationBell from "@/components/common/NotificationBell";

export default function Topbar({ onOpenAi, onOpenMobileNav }) {
  const { user, logout, switchRole } = useAuth();
  const [q, setQ] = useState("");

  const roleKeys = Object.keys(ROLE_LABELS);

  return (
    <header
      className="sticky top-0 z-20 h-16 bg-white/85 backdrop-blur-md border-b border-[#E5E7EB] flex items-center gap-2 sm:gap-4 px-3 sm:px-6"
      data-testid="topbar"
    >
      <button
        onClick={onOpenMobileNav}
        className="md:hidden h-10 w-10 rounded-lg border border-[#E5E7EB] bg-white flex items-center justify-center text-ink-muted hover:text-ink transition"
        aria-label="Open menu"
        data-testid="topbar-hamburger"
      >
        <Menu size={18} />
      </button>

      <div className="text-sm text-ink-muted hidden sm:flex items-center gap-2">
        <span>Dashboard</span>
        <span className="text-ink-muted/50">/</span>
        <span>Operations</span>
        <span className="text-ink-muted/50">/</span>
        <span className="text-ink font-semibold">Distribution</span>
      </div>

      <div className="flex-1" />

      <div className="relative hidden md:block w-72">
        <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-ink-muted" />
        <Input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Search orders, SKUs, distributors..."
          className="pl-9 h-10 bg-canvas border-[#E5E7EB]"
          data-testid="topbar-search"
        />
      </div>

      {/* Role switcher — hide on mobile */}
      <div className="hidden sm:block">
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button
            variant="outline"
            className="h-10 border-[#E5E7EB] text-ink font-medium gap-2"
            data-testid="role-switcher"
          >
            {ROLE_LABELS[user?.role] || "Role"}
            <ChevronDown size={14} className="text-ink-muted" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end" className="w-56">
          <DropdownMenuLabel>Switch role</DropdownMenuLabel>
          <DropdownMenuSeparator />
          <DropdownMenuGroup>
            {roleKeys.map((k) => (
              <DropdownMenuItem
                key={k}
                onClick={() => switchRole(k)}
                data-testid={`role-option-${k}`}
                className={user?.role === k ? "text-gold-dark font-semibold" : ""}
              >
                {ROLE_LABELS[k]}
              </DropdownMenuItem>
            ))}
          </DropdownMenuGroup>
        </DropdownMenuContent>
      </DropdownMenu>
      </div>

      <NotificationBell />

      <button
        onClick={onOpenAi}
        className="h-10 rounded-full pl-3 pr-3 sm:pr-4 border border-gold/40 bg-gold/10 text-gold-dark flex items-center gap-2 hover:bg-gold/20 transition font-semibold text-sm"
        data-testid="topbar-ai"
      >
        <Sparkles size={15} /> <span className="hidden sm:inline">AI</span>
      </button>

      {/* User */}
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <button className="flex items-center gap-2.5 pl-1 pr-2 py-1 rounded-full hover:bg-canvas transition" data-testid="user-menu">
            <div className="h-9 w-9 rounded-full bg-gold text-white flex items-center justify-center font-semibold text-xs">
              {user?.avatar || (user?.name?.[0] ?? "U")}
            </div>
            <div className="hidden lg:block text-left">
              <div className="text-sm font-semibold text-ink leading-tight">{user?.name || "User"}</div>
              <div className="text-[11px] text-ink-muted leading-tight">{ROLE_LABELS[user?.role]}</div>
            </div>
            <ChevronDown size={14} className="text-ink-muted" />
          </button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end" className="w-56">
          <DropdownMenuLabel>
            <div className="text-sm font-semibold text-ink">{user?.name}</div>
            <div className="text-xs text-ink-muted">{user?.email}</div>
          </DropdownMenuLabel>
          <DropdownMenuSeparator />
          <DropdownMenuItem data-testid="menu-profile">
            <UserIcon size={14} className="mr-2" /> Profile
          </DropdownMenuItem>
          <DropdownMenuItem onClick={logout} data-testid="menu-logout" className="text-rose-600">
            <LogOut size={14} className="mr-2" /> Sign out
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </header>
  );
}

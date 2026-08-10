import React, { useEffect, useState } from "react";
import { Moon, Sun } from "lucide-react";
import { getTheme, toggleTheme } from "@/lib/theme";

// Night-mode (black + gold) toggle. Available on every login/role.
export default function ThemeToggle({ className = "" }) {
  const [theme, setThemeState] = useState(getTheme());

  useEffect(() => {
    const handler = () => setThemeState(getTheme());
    window.addEventListener("dms-theme-change", handler);
    return () => window.removeEventListener("dms-theme-change", handler);
  }, []);

  const isDark = theme === "dark";
  return (
    <button
      type="button"
      onClick={() => setThemeState(toggleTheme())}
      title={isDark ? "Switch to Day mode" : "Switch to Night mode"}
      aria-label="Toggle night mode"
      data-testid="theme-toggle"
      className={`relative inline-flex items-center justify-center h-9 w-9 rounded-lg border border-slate-200 hover:border-[#c9a227] hover:bg-[#faf6e6] transition-colors dark-toggle-btn ${className}`}
    >
      {isDark
        ? <Sun size={18} className="text-[#e9c85a]" />
        : <Moon size={18} className="text-slate-600" />}
    </button>
  );
}

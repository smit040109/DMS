// Global light/dark ("night" — black + gold) theme helper.
const KEY = "dms-theme";

export function getTheme() {
  try { return localStorage.getItem(KEY) === "dark" ? "dark" : "light"; }
  catch { return "light"; }
}

export function applyTheme(theme) {
  const root = document.documentElement;
  if (theme === "dark") root.classList.add("dark");
  else root.classList.remove("dark");
}

export function setTheme(theme) {
  try { localStorage.setItem(KEY, theme); } catch { /* ignore */ }
  applyTheme(theme);
  // notify listeners in the same tab
  window.dispatchEvent(new CustomEvent("dms-theme-change", { detail: theme }));
}

export function toggleTheme() {
  const next = getTheme() === "dark" ? "light" : "dark";
  setTheme(next);
  return next;
}

export function initTheme() {
  applyTheme(getTheme());
}

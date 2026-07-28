/**
 * TenantContext — hydrates the current tenant's config (name, logo, colours,
 * labels, modules) and exposes helpers used by AppShell / Topbar / Login /
 * industry-specific labels.
 *
 * Falls back to the VayuERP platform default chrome when no user is logged
 * in (login screen) OR when the current user is the platform_owner.
 */
import React, { createContext, useContext, useEffect, useState, useCallback, useMemo } from "react";
import api from "@/lib/api";
import { useAuth } from "@/context/AuthContext";

const TenantContext = createContext(null);

const PLATFORM_DEFAULT = {
  id: "platform",
  slug: "vayuerp",
  name: "VayuERP",
  display_name: "VayuERP",
  brand_colors: { primary: "#0F172A", secondary: "#F59E0B", accent: "#10B981" },
  labels: {},
  is_platform: true,
  logo_url: null,
};

export function TenantProvider({ children }) {
  const { user } = useAuth();
  const [tenant, setTenant] = useState(null);
  const [loading, setLoading] = useState(false);

  const refresh = useCallback(async () => {
    if (!user) { setTenant(null); return; }
    setLoading(true);
    try {
      const { data } = await api.get("/platform/me/tenant");
      setTenant(data);
    } catch {
      setTenant(PLATFORM_DEFAULT);
    } finally {
      setLoading(false);
    }
  }, [user]);

  useEffect(() => { refresh(); }, [refresh]);

  // Apply brand colours as CSS variables on the document root so any
  // component can consume them via `var(--brand-primary)`.
  useEffect(() => {
    const colours = tenant?.brand_colors || PLATFORM_DEFAULT.brand_colors;
    const root = document.documentElement;
    root.style.setProperty("--brand-primary", colours.primary);
    root.style.setProperty("--brand-secondary", colours.secondary);
    root.style.setProperty("--brand-accent", colours.accent);
    // Update page title
    const title = tenant?.display_name || tenant?.name || "VayuERP";
    document.title = tenant?.is_platform ? "VayuERP — SaaS ERP Platform" : `${title} · VayuERP`;
  }, [tenant]);

  const value = useMemo(() => ({
    tenant: tenant || PLATFORM_DEFAULT,
    loading,
    refresh,
    isPlatform: !!(tenant?.is_platform),
    // Localised label helpers (Slice 1 — Module 15 productization)
    label: (key, fallback) => {
      const labels = tenant?.labels || {};
      return labels[key] || fallback || key;
    },
    brandName: tenant?.display_name || tenant?.name || "VayuERP",
    brandColors: tenant?.brand_colors || PLATFORM_DEFAULT.brand_colors,
    logoUrl: tenant?.logo_url || null,
  }), [tenant, loading, refresh]);

  return <TenantContext.Provider value={value}>{children}</TenantContext.Provider>;
}

export function useTenant() {
  return useContext(TenantContext) || { tenant: PLATFORM_DEFAULT, isPlatform: true, brandName: "VayuERP",
      brandColors: PLATFORM_DEFAULT.brand_colors, label: (k, f) => f || k, logoUrl: null };
}

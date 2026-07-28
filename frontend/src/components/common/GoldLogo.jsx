import React from "react";
import { useTenant } from "@/context/TenantContext";

/**
 * BrandLogo — tenant-aware brand mark.
 *
 * Behaviour:
 *  - If a logged-in tenant provides `logo_url`, render that image.
 *  - Otherwise render the SaaS default (VayuERP droplet emblem in the
 *    tenant's primary colour).
 *  - Text shows the tenant's display name; falls back to "VayuERP".
 *
 * The old export name `GoldLogo` is kept for backward-compatibility with
 * existing imports across the codebase.
 */
export function GoldLogo({ size = 36, showText = true, className = "" }) {
  const { tenant, brandName, brandColors, logoUrl, isPlatform } = useTenant();
  const primary = brandColors?.primary || "#0F172A";
  const secondary = brandColors?.secondary || "#F59E0B";

  const suffix = isPlatform ? "Platform" : "ERP";
  return (
    <div className={`flex items-center gap-3 ${className}`} data-testid="brand-logo">
      {logoUrl ? (
        <img
          src={logoUrl}
          alt={brandName}
          className="rounded-xl object-cover"
          style={{ width: size, height: size }}
        />
      ) : (
        <div
          className="relative flex items-center justify-center rounded-xl"
          style={{
            width: size,
            height: size,
            background: `linear-gradient(135deg, ${secondary} 0%, ${primary} 100%)`,
            boxShadow: `0 6px 18px -6px ${primary}55`,
          }}
        >
          <svg viewBox="0 0 24 24" width={size * 0.55} height={size * 0.55} fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
            <path
              d="M12 2.5C12 2.5 5.5 10 5.5 15a6.5 6.5 0 0 0 13 0c0-5-6.5-12.5-6.5-12.5Z"
              fill="#ffffff"
              fillOpacity="0.96"
            />
            <path
              d="M9.5 15c0-1.6 1-3.4 2.5-5"
              stroke={primary}
              strokeWidth="1.5"
              strokeLinecap="round"
            />
          </svg>
        </div>
      )}
      {showText && (
        <div className="leading-none">
          <div className="font-display font-extrabold text-ink tracking-tight" style={{ fontSize: 15 }}>
            {brandName} <span className="text-[#6B7280] font-medium">{suffix}</span>
          </div>
          <div className="text-[10px] uppercase tracking-[0.22em] text-ink-muted mt-1">
            {tenant?.industry ? tenant.industry.charAt(0).toUpperCase() + tenant.industry.slice(1) : "Enterprise"} · powered by VayuERP
          </div>
        </div>
      )}
    </div>
  );
}

export default GoldLogo;

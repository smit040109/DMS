import React from "react";

// Emblem for GO OIL — a stylized gold droplet inside a rounded square.
export function GoldLogo({ size = 36, showText = true, className = "" }) {
  return (
    <div className={`flex items-center gap-3 ${className}`} data-testid="go-oil-logo">
      <div
        className="relative flex items-center justify-center rounded-xl"
        style={{
          width: size,
          height: size,
          background:
            "linear-gradient(135deg, #C9A227 0%, #A67C00 100%)",
          boxShadow: "0 6px 18px -6px rgba(166,124,0,0.55)",
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
            stroke="#A67C00"
            strokeWidth="1.5"
            strokeLinecap="round"
          />
        </svg>
      </div>
      {showText && (
        <div className="leading-none">
          <div className="font-display font-extrabold text-ink tracking-tight" style={{ fontSize: 15 }}>
            GO OIL <span className="text-[#6B7280] font-medium">DMS</span>
          </div>
          <div className="text-[10px] uppercase tracking-[0.22em] text-ink-muted mt-1">
            Enterprise Command
          </div>
        </div>
      )}
    </div>
  );
}

export default GoldLogo;

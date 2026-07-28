import React from "react";
import { ChevronRight } from "lucide-react";

export default function PageHeader({ crumbs = [], title, subtitle, actions, testId = "page-header" }) {
  return (
    <div className="mb-6 flex flex-col md:flex-row md:items-end md:justify-between gap-4" data-testid={testId}>
      <div>
        <div className="flex items-center gap-1 text-xs text-ink-muted">
          {crumbs.map((c, i) => (
            <span key={i} className="flex items-center gap-1">
              <span>{c}</span>
              {i < crumbs.length - 1 && <ChevronRight size={12} strokeWidth={1.5} />}
            </span>
          ))}
        </div>
        <h1 className="mt-1 font-display font-extrabold text-3xl md:text-4xl text-ink tracking-tight">
          {title}
        </h1>
        {subtitle && <p className="mt-1.5 text-sm text-ink-muted">{subtitle}</p>}
      </div>
      {actions && <div className="flex items-center gap-2 flex-wrap">{actions}</div>}
    </div>
  );
}

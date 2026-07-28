import React, { useMemo, useState } from "react";
import { Search, SlidersHorizontal, ChevronLeft, ChevronRight, MoreHorizontal } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import StatusPill from "@/components/common/StatusPill";
import ExportMenu from "@/components/common/ExportMenu";

export default function DataTable({
  data = [],
  columns = [], // [{key,label,render?,align?,width?,type?:'status'|'currency'|'date'|'chip'}]
  loading = false,
  pageSize = 10,
  searchable = true,
  onRowClick,
  actions,
  emptyLabel = "No records found",
  testId = "data-table",
  exportTitle,
  exportResource, // if set, uses server-side full-collection export via /api/exports/{resource}
  exportable = true,
}) {
  const [q, setQ] = useState("");
  const [page, setPage] = useState(1);

  const filtered = useMemo(() => {
    if (!q) return data;
    const ql = q.toLowerCase();
    return data.filter((r) =>
      columns.some((c) => String(r[c.key] ?? "").toLowerCase().includes(ql))
    );
  }, [data, q, columns]);

  const totalPages = Math.max(1, Math.ceil(filtered.length / pageSize));
  const curPage = Math.min(page, totalPages);
  const start = (curPage - 1) * pageSize;
  const rows = filtered.slice(start, start + pageSize);

  const renderCell = (row, col) => {
    if (col.render) return col.render(row);
    const val = row[col.key];
    if (val === undefined || val === null || val === "") return <span className="text-ink-muted">—</span>;
    if (col.type === "status") return <StatusPill value={val} />;
    if (col.type === "currency") return (
      <span className="font-medium text-ink tabular-nums">
        {typeof val === "number" ? `$${val.toLocaleString(undefined, { maximumFractionDigits: 0 })}` : val}
      </span>
    );
    if (col.type === "date") {
      try { return new Date(val).toLocaleDateString(undefined, { day: "2-digit", month: "short", year: "numeric" }); }
      catch { return String(val); }
    }
    if (col.type === "chip") return (
      <span className="inline-flex items-center rounded-md bg-slate-100 text-slate-700 px-2 py-0.5 text-xs font-medium">{String(val)}</span>
    );
    return <span className="text-ink">{String(val)}</span>;
  };

  return (
    <div className="bg-white border border-[#E5E7EB] rounded-xl card-soft overflow-hidden" data-testid={testId}>
      {/* Toolbar */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-3 p-4 border-b border-[#E5E7EB]">
        {searchable ? (
          <div className="relative w-full lg:max-w-md">
            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-ink-muted" />
            <Input
              value={q}
              onChange={(e) => { setQ(e.target.value); setPage(1); }}
              placeholder="Search records..."
              className="pl-9 h-10 bg-canvas border-[#E5E7EB] focus-visible:ring-gold/40"
              data-testid={`${testId}-search`}
            />
          </div>
        ) : <div />}
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" className="border-[#E5E7EB] h-9" data-testid={`${testId}-filters`}>
            <SlidersHorizontal size={14} className="mr-1.5" /> Filters
          </Button>
          {exportable && (
            <ExportMenu
              rows={filtered}
              columns={columns.map((c) => c.key)}
              resource={exportResource}
              title={exportTitle || testId.replace(/-/g, " ")}
              subtitle={`${filtered.length} rows`}
              testId={`${testId}-export`}
            />
          )}
          {actions}
        </div>
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-[#E5E7EB] bg-canvas">
              {columns.map((c) => (
                <th
                  key={c.key}
                  className={`px-5 py-3 text-[11px] font-semibold uppercase tracking-wider text-ink-muted ${
                    c.align === "right" ? "text-right" : "text-left"
                  }`}
                  style={{ width: c.width }}
                >
                  {c.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {loading && (
              <tr>
                <td className="px-5 py-8 text-center text-ink-muted" colSpan={columns.length}>
                  Loading...
                </td>
              </tr>
            )}
            {!loading && rows.length === 0 && (
              <tr>
                <td className="px-5 py-10 text-center text-ink-muted" colSpan={columns.length}>
                  {emptyLabel}
                </td>
              </tr>
            )}
            {!loading &&
              rows.map((row, idx) => (
                <tr
                  key={row.id || idx}
                  className="border-b border-[#F1F5F9] hover:bg-canvas transition-colors cursor-pointer"
                  onClick={() => onRowClick?.(row)}
                  data-testid={`${testId}-row-${row.id || idx}`}
                >
                  {columns.map((c) => (
                    <td
                      key={c.key}
                      className={`px-5 py-4 align-middle ${c.align === "right" ? "text-right" : "text-left"}`}
                    >
                      {renderCell(row, c)}
                    </td>
                  ))}
                </tr>
              ))}
          </tbody>
        </table>
      </div>

      {/* Footer */}
      <div className="flex items-center justify-between px-4 py-3 border-t border-[#E5E7EB]">
        <div className="text-xs text-ink-muted">
          Showing <span className="text-ink font-semibold">{filtered.length ? start + 1 : 0}</span>–
          <span className="text-ink font-semibold">{Math.min(start + pageSize, filtered.length)}</span> of{" "}
          <span className="text-ink font-semibold">{filtered.length}</span>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            className="border-[#E5E7EB] h-8 w-8 p-0"
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={curPage === 1}
            data-testid={`${testId}-prev`}
          >
            <ChevronLeft size={14} />
          </Button>
          <div className="text-xs text-ink-muted">
            Page <span className="font-semibold text-ink">{curPage}</span> of {totalPages}
          </div>
          <Button
            variant="outline"
            size="sm"
            className="border-[#E5E7EB] h-8 w-8 p-0"
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            disabled={curPage === totalPages}
            data-testid={`${testId}-next`}
          >
            <ChevronRight size={14} />
          </Button>
        </div>
      </div>
    </div>
  );
}

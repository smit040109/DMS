import React, { useState } from "react";
import { Download, FileText, FileSpreadsheet, FileType2, Printer, Loader2 } from "lucide-react";
import {
  DropdownMenu, DropdownMenuTrigger, DropdownMenuContent, DropdownMenuItem, DropdownMenuLabel,
  DropdownMenuSeparator,
} from "@/components/ui/dropdown-menu";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";

const API = process.env.REACT_APP_BACKEND_URL || "";

/**
 * ExportMenu — 4-format export dropdown reusable across every page.
 *
 * Two ways to use:
 *   1. Row-set export (client-supplied): pass `rows` + optional `columns` (array of keys)
 *      → posts to /api/exports/render (exactly the rows currently visible).
 *   2. Resource export (server-side full collection): pass `resource="products"`
 *      → GET /api/exports/{resource}?format=…
 */
export default function ExportMenu({
  rows,
  columns,
  resource,
  title = "Export",
  subtitle = "",
  disabled = false,
  size = "sm",
  testId = "export-menu",
}) {
  const [busy, setBusy] = useState(false);

  const download = (blob, filename) => {
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.rel = "noopener";
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    setTimeout(() => URL.revokeObjectURL(url), 5000);
  };

  const openPrint = (blob) => {
    const url = URL.createObjectURL(blob);
    const w = window.open(url, "_blank", "noopener,noreferrer");
    if (!w) toast.error("Pop-up blocked. Allow pop-ups for print view.");
    setTimeout(() => URL.revokeObjectURL(url), 60000);
  };

  const handle = async (format) => {
    if (disabled || busy) return;
    setBusy(true);
    const token = localStorage.getItem("go_oil_token");
    try {
      let resp;
      if (resource) {
        resp = await fetch(`${API}/api/exports/${resource}?format=${format}`, {
          headers: { Authorization: token ? `Bearer ${token}` : "" },
          credentials: "include",
        });
      } else {
        resp = await fetch(`${API}/api/exports/render`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: token ? `Bearer ${token}` : "",
          },
          credentials: "include",
          body: JSON.stringify({
            rows: rows || [],
            columns: columns || null,
            format,
            title,
            subtitle,
          }),
        });
      }
      if (!resp.ok) {
        const err = await resp.text();
        throw new Error(err || `HTTP ${resp.status}`);
      }
      const blob = await resp.blob();
      const safeTitle = (title || "export").toLowerCase().replace(/[^a-z0-9-_]+/g, "-");
      const stamp = new Date().toISOString().replace(/[:.]/g, "-").slice(0, 15);
      const ext = { csv: "csv", xlsx: "xlsx", pdf: "pdf", print: "html", html: "html" }[format] || "bin";
      const filename = `${safeTitle}-${stamp}.${ext}`;
      if (format === "print" || format === "html") {
        openPrint(blob);
      } else {
        download(blob, filename);
      }
      toast.success(`${format.toUpperCase()} export ready`);
    } catch (e) {
      toast.error(`Export failed: ${e.message || e}`);
    } finally {
      setBusy(false);
    }
  };

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          variant="outline"
          size={size}
          className="border-[#E5E7EB] h-9"
          disabled={disabled || busy}
          data-testid={testId}
        >
          {busy ? (
            <Loader2 size={14} className="mr-1.5 animate-spin" />
          ) : (
            <Download size={14} className="mr-1.5" />
          )}
          Export
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-52">
        <DropdownMenuLabel className="text-xs text-ink-muted uppercase tracking-wider">
          Download as
        </DropdownMenuLabel>
        <DropdownMenuItem onClick={() => handle("csv")} data-testid={`${testId}-csv`}>
          <FileText size={14} className="mr-2" /> CSV
        </DropdownMenuItem>
        <DropdownMenuItem onClick={() => handle("xlsx")} data-testid={`${testId}-xlsx`}>
          <FileSpreadsheet size={14} className="mr-2" /> Excel (.xlsx)
        </DropdownMenuItem>
        <DropdownMenuItem onClick={() => handle("pdf")} data-testid={`${testId}-pdf`}>
          <FileType2 size={14} className="mr-2" /> PDF
        </DropdownMenuItem>
        <DropdownMenuSeparator />
        <DropdownMenuItem onClick={() => handle("print")} data-testid={`${testId}-print`}>
          <Printer size={14} className="mr-2" /> Print View
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

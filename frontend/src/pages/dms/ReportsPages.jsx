import React, { useEffect, useMemo, useState, useCallback } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { dms, inr } from "./api";
import { PageHeader } from "./OwnerPages";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter
} from "@/components/ui/dialog";
import { toast } from "sonner";
import {
  Star, ChevronDown, ChevronRight, Search, ArrowLeft, Printer, Download,
  Clock, TrendingUp, Save, X, BarChart3
} from "lucide-react";

// ---------------------------------------------------------------------------
// Reports Hub
// ---------------------------------------------------------------------------
const CATEGORY_STYLES = {
  transaction: { accent: "border-l-4 border-[#c9a227]" },
  party:       { accent: "border-l-4 border-blue-500" },
  gst:         { accent: "border-l-4 border-emerald-500" },
  stock:       { accent: "border-l-4 border-violet-500" },
  sales_team:  { accent: "border-l-4 border-rose-500" },
};

export function ReportsHubPage() {
  const [groups, setGroups] = useState([]);
  const [favorites, setFavorites] = useState([]);
  const [openCats, setOpenCats] = useState({});
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const nav = useNavigate();

  const load = async () => {
    setLoading(true);
    try {
      const d = await dms.reportsCatalog();
      setGroups(d.groups || []);
      setFavorites(d.favorites || []);
      const init = {};
      (d.groups || []).forEach(g => { init[g.category] = true; });
      setOpenCats(init);
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Failed to load reports");
    } finally { setLoading(false); }
  };
  useEffect(() => { load(); }, []);

  const toggleFav = async (rid) => {
    try { await dms.toggleReportFavorite(rid); await load(); }
    catch (e) { toast.error(e?.response?.data?.detail || "Could not update favorite"); }
  };

  const filtered = useMemo(() => {
    const q = (search || "").trim().toLowerCase();
    if (!q) return groups;
    return groups
      .map(g => ({ ...g, items: g.items.filter(it =>
        it.name.toLowerCase().includes(q) ||
        (it.description || "").toLowerCase().includes(q)
      )}))
      .filter(g => g.items.length > 0);
  }, [groups, search]);

  const openReport = (item) => nav(`/dms/reports/${item.id}`);

  return (
    <div className="space-y-6">
      <PageHeader
        title="Reports"
        subtitle="Browse, favorite and run reports across your business"
        icon={<TrendingUp className="w-6 h-6 text-[#a67c00]" />}
      />
      <div className="flex flex-col md:flex-row md:items-center gap-3">
        <div className="relative flex-1 max-w-xl">
          <Search className="absolute left-3 top-3 w-4 h-4 text-slate-400" />
          <Input placeholder="Search reports…" value={search}
            onChange={(e) => setSearch(e.target.value)} className="pl-9"
            data-testid="reports-search" />
        </div>
        <div className="text-sm text-slate-500">
          {loading ? "Loading…" : `${filtered.reduce((a, g) => a + g.items.length, 0)} reports available`}
        </div>
      </div>

      {favorites.length > 0 && (
        <Card className="p-4 border-amber-200 bg-amber-50/40">
          <div className="flex items-center gap-2 mb-3">
            <Star className="w-4 h-4 fill-amber-500 text-amber-500" />
            <div className="font-semibold text-slate-800">Your favorites</div>
          </div>
          <div className="flex flex-wrap gap-2">
            {favorites.map(f => (
              <button key={f.id} onClick={() => openReport(f)}
                className="px-3 py-1.5 text-sm bg-white border border-amber-200 rounded-full hover:bg-amber-100 hover:border-amber-300 transition"
                data-testid={`fav-chip-${f.id}`}>
                {f.name}
                {f.status !== "live" && <span className="ml-2 text-xs text-slate-500">(soon)</span>}
              </button>
            ))}
          </div>
        </Card>
      )}

      <div className="space-y-4">
        {filtered.map(group => {
          const style = CATEGORY_STYLES[group.category] || {};
          const open = openCats[group.category];
          return (
            <Card key={group.category} className={`overflow-hidden ${style.accent || ""}`}>
              <button
                onClick={() => setOpenCats(s => ({ ...s, [group.category]: !s[group.category] }))}
                className="w-full flex items-center justify-between px-5 py-3 hover:bg-slate-50 transition"
                data-testid={`cat-toggle-${group.category}`}>
                <div className="flex items-center gap-3">
                  {open ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
                  <div className="font-semibold text-slate-800">{group.label}</div>
                  <Badge variant="outline" className="text-xs">{group.items.length}</Badge>
                </div>
              </button>
              {open && (
                <div className="px-5 pb-4 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                  {group.items.map(item => (
                    <div key={item.id}
                      className="border rounded-lg p-3 hover:shadow-sm hover:border-amber-300 transition bg-white flex flex-col gap-2"
                      data-testid={`report-tile-${item.id}`}>
                      <div className="flex items-start justify-between gap-2">
                        <button onClick={() => openReport(item)} className="text-left flex-1"
                          data-testid={`report-open-${item.id}`}>
                          <div className="font-medium text-slate-800 leading-tight">{item.name}</div>
                          <div className="text-xs text-slate-500 mt-1 line-clamp-2">{item.description}</div>
                        </button>
                        <button onClick={(e) => { e.stopPropagation(); toggleFav(item.id); }}
                          className={`p-1 rounded hover:bg-amber-50 ${item.is_favorite ? "text-amber-500" : "text-slate-300"}`}
                          data-testid={`fav-toggle-${item.id}`}>
                          <Star className={`w-4 h-4 ${item.is_favorite ? "fill-amber-500" : ""}`} />
                        </button>
                      </div>
                      <div className="flex items-center gap-2 mt-1">
                        {item.status === "live" ? (
                          <Badge className="bg-emerald-100 text-emerald-800 border-emerald-200 text-[10px] uppercase tracking-wide">Live</Badge>
                        ) : (
                          <Badge className="bg-slate-100 text-slate-700 border-slate-200 text-[10px] uppercase tracking-wide">
                            <Clock className="w-3 h-3 mr-1 inline" />Coming soon
                          </Badge>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </Card>
          );
        })}
        {!loading && filtered.length === 0 && (
          <Card className="p-8 text-center text-slate-500">No reports match your search.</Card>
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Formatting helpers used by GenericReportPage
// ---------------------------------------------------------------------------
const firstOfMonth = () => {
  const d = new Date(); return new Date(d.getFullYear(), d.getMonth(), 1).toISOString().slice(0, 10);
};
const today = () => new Date().toISOString().slice(0, 10);
const fmtDateShort = (v) => {
  if (!v) return "—";
  try { return new Date(v).toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "2-digit" }); }
  catch { return String(v).slice(0, 10); }
};

function renderCell(row, col) {
  const v = row[col.key];
  if (v === undefined || v === null || v === "") return <span className="text-slate-400">—</span>;
  if (col.type === "currency") return inr(v);
  if (col.type === "pct") return `${Number(v).toFixed(2)}%`;
  if (col.type === "number") return Number(v).toLocaleString("en-IN", { maximumFractionDigits: 2 });
  if (col.type === "int") return Number(v).toLocaleString("en-IN");
  if (col.type === "date") return fmtDateShort(v);
  return String(v);
}

// ---------------------------------------------------------------------------
// Generic Report Page — driven by report_id + columns metadata
// ---------------------------------------------------------------------------

const FILTER_LABELS = {
  date_from: "From", date_to: "To", as_on_date: "As On",
  date: "Date", sale_type: "Sale Type", status: "Status", category: "Category",
  party_id: "Party", item_id: "Item", fy_year: "FY Year",
};

export function GenericReportPage() {
  const { reportId } = useParams();
  const nav = useNavigate();
  const [catalog, setCatalog] = useState([]);
  const [meta, setMeta] = useState(null);
  const [filters, setFilters] = useState({});
  const [data, setData] = useState({ rows: [], totals: {}, columns: [] });
  const [loading, setLoading] = useState(false);
  const [distributors, setDistributors] = useState([]);
  const [retailers, setRetailers] = useState([]);
  const [products, setProducts] = useState([]);
  const [categories, setCategories] = useState([]);
  const [savedFilters, setSavedFilters] = useState([]);
  const [saveDialogOpen, setSaveDialogOpen] = useState(false);
  const [saveName, setSaveName] = useState("");
  const [showChart, setShowChart] = useState(true);

  // Load catalog to get filters + meta for this report
  useEffect(() => {
    dms.reportsCatalog().then((d) => {
      const flat = [];
      (d.groups || []).forEach(g => g.items.forEach(it => flat.push({ ...it, category_label: g.label })));
      setCatalog(flat);
      const found = flat.find(x => x.id === reportId);
      setMeta(found || null);
    }).catch(() => setMeta(null));
  }, [reportId]);

  // Initialize default filters
  useEffect(() => {
    if (!meta) return;
    const init = {};
    (meta.filters || []).forEach(f => {
      if (f === "date_from") init[f] = firstOfMonth();
      else if (f === "date_to") init[f] = today();
      else if (f === "as_on_date") init[f] = today();
      else if (f === "date") init[f] = today();
      else if (f === "sale_type") init[f] = "both";
      else if (f === "status") init[f] = "";
      else if (f === "party_id") init[f] = "";
      else if (f === "item_id") init[f] = "";
      else if (f === "category") init[f] = "";
      else if (f === "fy_year") init[f] = String(new Date().getFullYear());
    });
    setFilters(init);
  }, [meta]);

  // Load party/product/category dropdowns if needed
  useEffect(() => {
    if (!meta) return;
    const needsParty = (meta.filters || []).includes("party_id");
    const needsItem = (meta.filters || []).includes("item_id");
    const needsCat = (meta.filters || []).includes("category");
    if (needsParty) {
      Promise.all([
        dms.listDistributors().catch(() => ({ data: [] })),
        dms.listRetailers ? dms.listRetailers().catch(() => ({ data: [] })) : Promise.resolve({ data: [] }),
      ]).then(([d, r]) => { setDistributors(d.data || []); setRetailers(r.data || []); });
    }
    if (needsItem) {
      dms.listProducts().then(d => setProducts(d.data || d || [])).catch(() => setProducts([]));
    }
    if (needsCat) {
      dms.listCategories ? dms.listCategories().then(d => setCategories(d.data || d || [])).catch(() => setCategories([]))
        : setCategories([]);
    }
  }, [meta]);

  // Load saved filters
  const loadSavedFilters = useCallback(() => {
    dms.listSavedFilters(reportId).then(d => setSavedFilters(d.data || [])).catch(() => {});
  }, [reportId]);
  useEffect(() => { loadSavedFilters(); }, [loadSavedFilters]);

  const run = useCallback(async () => {
    if (!meta) return;
    setLoading(true);
    try {
      const params = { ...filters };
      // Blank out "all" placeholders
      Object.keys(params).forEach(k => { if (params[k] === "all") params[k] = ""; });
      const d = await dms.runReport(reportId, params);
      setData(d);
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Failed to run report");
      setData({ rows: [], totals: {}, columns: [] });
    } finally { setLoading(false); }
  }, [meta, filters, reportId]);

  // Auto-run once filters initialized
  useEffect(() => {
    if (!meta) return;
    // Only auto-run when at least one filter key exists or the report has no filters
    run();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [meta]);

  const exportExcel = () => {
    const params = { ...filters };
    Object.keys(params).forEach(k => { if (params[k] === "all" || params[k] === "") delete params[k]; });
    const url = dms.reportExportUrl(reportId, params);
    fetch(url, {
      headers: { "Authorization": "Bearer " + (localStorage.getItem("go_oil_token") || "") },
    }).then(async r => {
      if (!r.ok) throw new Error("Export failed");
      const blob = await r.blob();
      const a = document.createElement("a");
      const u = URL.createObjectURL(blob);
      a.href = u; a.download = `${reportId}_${today()}.xlsx`;
      document.body.appendChild(a); a.click(); document.body.removeChild(a);
      URL.revokeObjectURL(u);
    }).catch(e => toast.error(e.message || "Export failed"));
  };
  const printPdf = () => window.print();

  const applySavedFilter = (sf) => {
    setFilters({ ...(sf.filters || {}) });
    setTimeout(() => run(), 50);
  };
  const saveCurrentFilter = async () => {
    if (!saveName.trim()) { toast.error("Give this filter a name"); return; }
    try {
      await dms.saveFilter(reportId, { name: saveName.trim(), filters });
      toast.success("Filter saved");
      setSaveName("");
      setSaveDialogOpen(false);
      loadSavedFilters();
    } catch (e) { toast.error(e?.response?.data?.detail || "Failed to save"); }
  };
  const deleteSavedFilter = async (id) => {
    try { await dms.deleteSavedFilter(id); loadSavedFilters(); } catch { /* ignore */ }
  };

  if (!meta) {
    return (
      <div className="p-8 text-center text-slate-500">Loading report…</div>
    );
  }

  if (meta.status !== "live") {
    return <ComingSoonInline meta={meta} nav={nav} />;
  }

  const cols = data.columns || [];
  const rows = data.rows || [];
  const t = data.totals || {};

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between gap-2 print:hidden">
        <Button variant="outline" size="sm" onClick={() => nav("/dms/reports")} data-testid="back-to-reports">
          <ArrowLeft className="w-4 h-4 mr-2" /> Back to Reports
        </Button>
      </div>

      <PageHeader
        title={meta.name}
        subtitle={meta.description}
        icon={<TrendingUp className="w-6 h-6 text-[#a67c00]" />}
      />

      {/* Filter panel */}
      {(meta.filters || []).length > 0 && (
        <Card className="p-4 print:hidden" data-testid="report-filters">
          <div className="grid grid-cols-1 md:grid-cols-4 lg:grid-cols-5 gap-3 items-end">
            {(meta.filters || []).map(f => (
              <FilterInput
                key={f}
                type={f}
                value={filters[f] || ""}
                onChange={(v) => setFilters(s => ({ ...s, [f]: v }))}
                distributors={distributors}
                retailers={retailers}
                products={products}
                categories={categories}
              />
            ))}
            <div className="flex gap-2 items-end flex-wrap">
              <Button onClick={run} disabled={loading} data-testid="run-report"
                className="bg-[#c9a227] hover:bg-[#a67c00]">
                {loading ? "Running…" : "Run"}
              </Button>
            </div>
          </div>

          {/* Saved filters row */}
          <div className="mt-3 pt-3 border-t border-slate-100 flex flex-wrap items-center gap-2">
            <span className="text-xs text-slate-500 mr-1">Saved filters:</span>
            {savedFilters.map(sf => (
              <span key={sf.id} className="inline-flex items-center gap-1 bg-slate-50 border border-slate-200 rounded-full px-2.5 py-1 text-xs">
                <button onClick={() => applySavedFilter(sf)} className="hover:underline"
                  data-testid={`apply-sf-${sf.id}`}>{sf.name}</button>
                <button onClick={() => deleteSavedFilter(sf.id)} className="text-slate-400 hover:text-rose-500">
                  <X className="w-3 h-3" />
                </button>
              </span>
            ))}
            {savedFilters.length === 0 && <span className="text-xs text-slate-400 italic">none yet</span>}
            <Button variant="outline" size="sm" className="ml-auto" onClick={() => setSaveDialogOpen(true)}
              data-testid="save-filter">
              <Save className="w-3 h-3 mr-1" /> Save current
            </Button>
          </div>
        </Card>
      )}

      {/* Totals strip */}
      <TotalsStrip totals={t} columns={cols} />

      {/* Charts */}
      {shouldShowChart(reportId, rows, cols) && (
        <div className="print:hidden">
          <div className="flex items-center justify-between mb-2">
            <div className="text-sm text-slate-500 flex items-center gap-2">
              <BarChart3 className="w-4 h-4" /> Charts
            </div>
            <button onClick={() => setShowChart(s => !s)} className="text-xs text-slate-500 hover:underline">
              {showChart ? "Hide" : "Show"}
            </button>
          </div>
          {showChart && <ChartsPanel reportId={reportId} rows={rows} columns={cols} />}
        </div>
      )}

      {/* Actions */}
      <div className="flex items-center justify-between print:hidden">
        <div className="text-sm text-slate-500">
          {rows.length} row{rows.length === 1 ? "" : "s"}
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={exportExcel} data-testid="export-excel">
            <Download className="w-4 h-4 mr-2" /> Excel
          </Button>
          <Button variant="outline" onClick={printPdf} data-testid="print-pdf">
            <Printer className="w-4 h-4 mr-2" /> Print / PDF
          </Button>
        </div>
      </div>

      {/* Table */}
      <Card className="overflow-hidden">
        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                {cols.map(c => (
                  <TableHead key={c.key} className={c.align === "right" ? "text-right" : c.align === "center" ? "text-center" : ""}>
                    {c.label}
                  </TableHead>
                ))}
              </TableRow>
            </TableHeader>
            <TableBody>
              {rows.length === 0 && (
                <TableRow>
                  <TableCell colSpan={cols.length || 1} className="text-center text-slate-500 py-8">
                    {data.empty_message || "No data in this range."}
                  </TableCell>
                </TableRow>
              )}
              {rows.map((r, i) => (
                <TableRow key={i}>
                  {cols.map(c => (
                    <TableCell key={c.key} className={c.align === "right" ? "text-right" : c.align === "center" ? "text-center" : ""}>
                      {renderCell(r, c)}
                    </TableCell>
                  ))}
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </Card>

      <Dialog open={saveDialogOpen} onOpenChange={setSaveDialogOpen}>
        <DialogContent>
          <DialogHeader><DialogTitle>Save current filters</DialogTitle></DialogHeader>
          <div className="space-y-3">
            <Label>Name</Label>
            <Input placeholder="e.g. This month · Distributor1 · Primary" value={saveName}
              onChange={(e) => setSaveName(e.target.value)} data-testid="save-filter-name" />
            <div className="bg-slate-50 border p-3 rounded text-xs text-slate-600">
              <div className="mb-1 font-medium">Current filters:</div>
              {Object.entries(filters).filter(([_, v]) => v).map(([k, v]) => (
                <div key={k}>{FILTER_LABELS[k] || k}: <span className="font-mono">{v}</span></div>
              ))}
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setSaveDialogOpen(false)}>Cancel</Button>
            <Button onClick={saveCurrentFilter} className="bg-[#c9a227] hover:bg-[#a67c00]">Save</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

// ---------- Inline Coming Soon (when navigated but report not live) ----------
function ComingSoonInline({ meta, nav }) {
  return (
    <div className="space-y-5">
      <Button variant="outline" size="sm" onClick={() => nav("/dms/reports")}>
        <ArrowLeft className="w-4 h-4 mr-2" /> Back to Reports
      </Button>
      <PageHeader title={meta.name} subtitle={meta.category_label || ""}
        icon={<Clock className="w-6 h-6 text-slate-500" />} />
      <Card className="p-8 text-center">
        <Clock className="w-10 h-10 text-slate-400 mx-auto mb-3" />
        <div className="text-lg font-semibold text-slate-800 mb-1">Coming Soon</div>
        <div className="text-sm text-slate-500 max-w-md mx-auto">{meta.description || ""}</div>
        <div className="mt-6">
          <Link to="/dms/reports" className="text-[#a67c00] hover:underline text-sm">
            ← Browse other reports
          </Link>
        </div>
      </Card>
    </div>
  );
}

// ---------- Totals strip ----------
function TotalsStrip({ totals, columns }) {
  const items = [];
  const currencyCols = (columns || []).filter(c => c.get ? false : c.totals && c.type === "currency");
  // Prefer specific keys, then column totals
  const preferKeys = ["total", "grand_total", "revenue", "profit", "outstanding", "amount", "stock_value", "gst", "count", "subtotal"];
  const seen = new Set();
  for (const k of preferKeys) {
    if (k in (totals || {})) { items.push({ key: k, val: totals[k] }); seen.add(k); }
    if (items.length >= 4) break;
  }
  if (items.length < 4) {
    for (const c of currencyCols) {
      if (seen.has(c.key)) continue;
      if (c.key in (totals || {})) { items.push({ key: c.key, val: totals[c.key], label: c.label }); seen.add(c.key); }
      if (items.length >= 4) break;
    }
  }
  if (items.length === 0) return null;
  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
      {items.map((it, idx) => (
        <Card key={it.key} className={`p-4 ${idx === items.length - 1 ? "border-amber-200" : ""}`}>
          <div className="text-xs uppercase text-slate-500">{prettyLabel(it.key)}</div>
          <div className={`text-xl font-semibold ${idx === items.length - 1 ? "text-[#a67c00]" : ""}`}>
            {typeof it.val === "number"
              ? (["count", "orders", "bills", "retailers_covered", "new_retailers", "gps_pings", "punch_days", "visits", "distributors", "retailers", "primary_count", "secondary_count"].includes(it.key)
                  ? Number(it.val).toLocaleString("en-IN")
                  : inr(it.val))
              : String(it.val ?? "")}
          </div>
        </Card>
      ))}
    </div>
  );
}
function prettyLabel(k) {
  return k.replace(/_/g, " ").replace(/\b\w/g, ch => ch.toUpperCase());
}

// ---------- Charts (lightweight, no external lib) ----------
function shouldShowChart(reportId, rows, columns) {
  if (!rows || rows.length < 2) return false;
  // Only enable charts for reports with a date column or a party column + currency total
  const hasDate = columns.some(c => c.type === "date");
  const hasParty = columns.some(c => ["party_name", "party", "supplier", "distributor", "retailer", "salesperson", "product_name", "category", "member"].includes(c.key));
  const hasCurrency = columns.some(c => c.type === "currency");
  return hasCurrency && (hasDate || hasParty);
}

function ChartsPanel({ reportId, rows, columns }) {
  const dateCol = columns.find(c => c.type === "date");
  const currencyCol = columns.find(c => c.type === "currency" && (c.key === "total" || c.key === "amount" || c.key === "revenue" || c.key === "outstanding" || c.key === "profit" || c.key === "stock_value")) || columns.find(c => c.type === "currency");
  const partyCol = columns.find(c => ["party_name", "party", "supplier", "distributor", "retailer", "salesperson", "product_name", "category", "member"].includes(c.key));

  // Daily trend
  const trend = {};
  if (dateCol && currencyCol) {
    rows.forEach(r => {
      const k = (r[dateCol.key] || "").slice(0, 10);
      if (!k) return;
      trend[k] = (trend[k] || 0) + Number(r[currencyCol.key] || 0);
    });
  }
  const trendEntries = Object.entries(trend).sort();
  const trendMax = Math.max(1, ...trendEntries.map(([_, v]) => v));

  // Top 5 by party
  const byParty = {};
  if (partyCol && currencyCol) {
    rows.forEach(r => {
      const k = r[partyCol.key] || "—";
      byParty[k] = (byParty[k] || 0) + Number(r[currencyCol.key] || 0);
    });
  }
  const top5 = Object.entries(byParty).sort((a, b) => b[1] - a[1]).slice(0, 5);
  const top5Max = Math.max(1, ...top5.map(([_, v]) => v));

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
      {trendEntries.length > 1 && (
        <Card className="p-4">
          <div className="text-sm font-semibold text-slate-800 mb-3">
            Daily Trend — {currencyCol?.label || "Amount"}
          </div>
          <div className="flex items-end gap-1 h-32">
            {trendEntries.map(([d, v]) => {
              const h = Math.max(4, Math.round((v / trendMax) * 100));
              return (
                <div key={d} className="flex-1 flex flex-col items-center justify-end group relative">
                  <div className="w-full rounded-t bg-gradient-to-t from-[#a67c00] to-[#c9a227] hover:opacity-80 transition"
                    style={{ height: `${h}%` }}
                    title={`${d}: ${inr(v)}`} />
                  <div className="text-[9px] text-slate-500 mt-1 rotate-45 origin-top-left whitespace-nowrap">
                    {d.slice(5)}
                  </div>
                </div>
              );
            })}
          </div>
        </Card>
      )}
      {top5.length > 0 && (
        <Card className="p-4">
          <div className="text-sm font-semibold text-slate-800 mb-3">
            Top {top5.length} by {partyCol?.label || "Party"} — {currencyCol?.label || "Amount"}
          </div>
          <div className="space-y-2">
            {top5.map(([name, v]) => (
              <div key={name}>
                <div className="flex justify-between text-xs mb-0.5">
                  <span className="truncate max-w-[65%]">{name}</span>
                  <span className="font-mono">{inr(v)}</span>
                </div>
                <div className="h-2 bg-slate-100 rounded overflow-hidden">
                  <div className="h-full bg-gradient-to-r from-[#c9a227] to-[#a67c00]"
                    style={{ width: `${(v / top5Max) * 100}%` }} />
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
}

// ---------- Filter input builder ----------
function FilterInput({ type, value, onChange, distributors, retailers, products, categories }) {
  const label = FILTER_LABELS[type] || type;
  const [pq, setPq] = React.useState("");
  if (["date_from", "date_to", "as_on_date", "date"].includes(type)) {
    return (
      <div>
        <Label>{label}</Label>
        <Input type="date" value={value} onChange={(e) => onChange(e.target.value)}
          data-testid={`filter-${type}`} />
      </div>
    );
  }
  if (type === "sale_type") {
    return (
      <div>
        <Label>{label}</Label>
        <Select value={value || "both"} onValueChange={onChange}>
          <SelectTrigger data-testid="filter-sale-type"><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value="both">Both</SelectItem>
            <SelectItem value="primary">Primary</SelectItem>
            <SelectItem value="secondary">Secondary</SelectItem>
          </SelectContent>
        </Select>
      </div>
    );
  }
  if (type === "status") {
    return (
      <div>
        <Label>{label}</Label>
        <Select value={value || "all"} onValueChange={(v) => onChange(v === "all" ? "" : v)}>
          <SelectTrigger data-testid="filter-status"><SelectValue placeholder="All" /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All</SelectItem>
            <SelectItem value="pending">Pending</SelectItem>
            <SelectItem value="approved">Approved</SelectItem>
            <SelectItem value="dispatched">Dispatched</SelectItem>
            <SelectItem value="fulfilled">Fulfilled</SelectItem>
            <SelectItem value="cancelled">Cancelled</SelectItem>
          </SelectContent>
        </Select>
      </div>
    );
  }
  if (type === "party_id") {
    const term = pq.trim().toLowerCase();
    const dList = (distributors || []).filter(d => !term || (d.name || "").toLowerCase().includes(term));
    const rList = (retailers || []).filter(r => !term || (r.name || "").toLowerCase().includes(term));
    return (
      <div>
        <Label>{label}</Label>
        <Select value={value || "all"} onValueChange={(v) => onChange(v === "all" ? "" : v)}>
          <SelectTrigger data-testid="filter-party"><SelectValue placeholder="All parties" /></SelectTrigger>
          <SelectContent>
            <div className="px-2 py-2 sticky top-0 bg-white z-10 border-b">
              <div className="relative">
                <Search className="w-3.5 h-3.5 absolute left-2 top-1/2 -translate-y-1/2 text-slate-400" />
                <Input value={pq} onChange={(e) => setPq(e.target.value)} placeholder="Search party…"
                  className="pl-7 h-8 text-sm" data-testid="party-search"
                  onKeyDown={(e) => e.stopPropagation()} />
              </div>
            </div>
            <SelectItem value="all">All parties</SelectItem>
            {dList.map(d => (
              <SelectItem key={d.id} value={d.id}>{d.name} (Distributor)</SelectItem>
            ))}
            {rList.map(r => (
              <SelectItem key={r.id} value={r.id}>{r.name} (Retailer)</SelectItem>
            ))}
            {dList.length === 0 && rList.length === 0 && (
              <div className="px-3 py-2 text-xs text-slate-400">No parties match “{pq}”</div>
            )}
          </SelectContent>
        </Select>
      </div>
    );
  }
  if (type === "item_id") {
    return (
      <div>
        <Label>{label}</Label>
        <Select value={value || "all"} onValueChange={(v) => onChange(v === "all" ? "" : v)}>
          <SelectTrigger data-testid="filter-item"><SelectValue placeholder="All items" /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All items</SelectItem>
            {(products || []).slice(0, 200).map(p => (
              <SelectItem key={p.id} value={p.id}>{p.name || p.sku_code}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
    );
  }
  if (type === "category") {
    return (
      <div>
        <Label>{label}</Label>
        <Select value={value || "all"} onValueChange={(v) => onChange(v === "all" ? "" : v)}>
          <SelectTrigger data-testid="filter-category"><SelectValue placeholder="All categories" /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All categories</SelectItem>
            {(categories || []).map(c => (
              <SelectItem key={c.id || c} value={c.id || c}>{c.name || c}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
    );
  }
  if (type === "fy_year") {
    const y = new Date().getFullYear();
    const options = [y, y - 1, y - 2].map(String);
    return (
      <div>
        <Label>{label}</Label>
        <Select value={value || String(y)} onValueChange={onChange}>
          <SelectTrigger data-testid="filter-fy"><SelectValue /></SelectTrigger>
          <SelectContent>
            {options.map(o => <SelectItem key={o} value={o}>{o}</SelectItem>)}
          </SelectContent>
        </Select>
      </div>
    );
  }
  // Fallback: text input
  return (
    <div>
      <Label>{label}</Label>
      <Input value={value || ""} onChange={(e) => onChange(e.target.value)} />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Sale Report page — uses the same generic engine (backward compat)
// ---------------------------------------------------------------------------
export function SaleReportPage() {
  // Delegate to GenericReportPage by simulating params
  const nav = useNavigate();
  useEffect(() => { nav("/dms/reports/sale", { replace: true }); }, [nav]);
  return null;
}

// ---------- Coming Soon (only used if generic page not routed) ----------
export function ComingSoonReportPage() {
  return <GenericReportPage />;
}

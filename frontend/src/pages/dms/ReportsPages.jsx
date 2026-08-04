import React, { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { dms, inr, niceDate } from "./api";
import { PageHeader } from "./OwnerPages";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { toast } from "sonner";
import { Star, ChevronDown, ChevronRight, Search, ArrowLeft, Printer, Download, Clock, TrendingUp } from "lucide-react";

// ---------------------------------------------------------------------------
// Reports Hub — sidebar entry point for the whole Reports section
// ---------------------------------------------------------------------------

const CATEGORY_STYLES = {
  transaction: { accent: "border-l-4 border-[#c9a227]", chipBg: "bg-amber-50 text-amber-800 border-amber-200" },
  party:       { accent: "border-l-4 border-blue-500",   chipBg: "bg-blue-50 text-blue-800 border-blue-200" },
  gst:         { accent: "border-l-4 border-emerald-500", chipBg: "bg-emerald-50 text-emerald-800 border-emerald-200" },
  stock:       { accent: "border-l-4 border-violet-500", chipBg: "bg-violet-50 text-violet-800 border-violet-200" },
  sales_team:  { accent: "border-l-4 border-rose-500",   chipBg: "bg-rose-50 text-rose-800 border-rose-200" },
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
      // default: expand all categories on first load
      const init = {};
      (d.groups || []).forEach(g => { init[g.category] = true; });
      setOpenCats(init);
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Failed to load reports");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const toggleFav = async (rid) => {
    try {
      await dms.toggleReportFavorite(rid);
      await load();
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Could not update favorite");
    }
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

  const openReport = (item) => {
    if (item.status === "live" && item.id === "sale") {
      nav("/dms/reports/sale");
    } else {
      nav(`/dms/reports/${item.id}`);
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Reports"
        subtitle="Browse, favorite and run reports across your business"
        icon={<TrendingUp className="w-6 h-6 text-[#a67c00]" />}
      />

      {/* Search + summary bar */}
      <div className="flex flex-col md:flex-row md:items-center gap-3">
        <div className="relative flex-1 max-w-xl">
          <Search className="absolute left-3 top-3 w-4 h-4 text-slate-400" />
          <Input
            placeholder="Search reports…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9"
            data-testid="reports-search"
          />
        </div>
        <div className="text-sm text-slate-500">
          {loading ? "Loading…" : `${filtered.reduce((a, g) => a + g.items.length, 0)} reports available`}
        </div>
      </div>

      {/* Favorites strip */}
      {favorites.length > 0 && (
        <Card className="p-4 border-amber-200 bg-amber-50/40">
          <div className="flex items-center gap-2 mb-3">
            <Star className="w-4 h-4 fill-amber-500 text-amber-500" />
            <div className="font-semibold text-slate-800">Your favorites</div>
          </div>
          <div className="flex flex-wrap gap-2">
            {favorites.map(f => (
              <button
                key={f.id}
                onClick={() => openReport(f)}
                className="px-3 py-1.5 text-sm bg-white border border-amber-200 rounded-full hover:bg-amber-100 hover:border-amber-300 transition"
                data-testid={`fav-chip-${f.id}`}
              >
                {f.name}
                {f.status !== "live" && (
                  <span className="ml-2 text-xs text-slate-500">(soon)</span>
                )}
              </button>
            ))}
          </div>
        </Card>
      )}

      {/* Categorised report groups */}
      <div className="space-y-4">
        {filtered.map(group => {
          const style = CATEGORY_STYLES[group.category] || {};
          const open = openCats[group.category];
          return (
            <Card key={group.category} className={`overflow-hidden ${style.accent || ""}`}>
              <button
                onClick={() => setOpenCats(s => ({ ...s, [group.category]: !s[group.category] }))}
                className="w-full flex items-center justify-between px-5 py-3 hover:bg-slate-50 transition"
                data-testid={`cat-toggle-${group.category}`}
              >
                <div className="flex items-center gap-3">
                  {open ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
                  <div className="font-semibold text-slate-800">{group.label}</div>
                  <Badge variant="outline" className="text-xs">{group.items.length}</Badge>
                </div>
              </button>
              {open && (
                <div className="px-5 pb-4 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                  {group.items.map(item => (
                    <div
                      key={item.id}
                      className="border rounded-lg p-3 hover:shadow-sm hover:border-amber-300 transition bg-white flex flex-col gap-2"
                      data-testid={`report-tile-${item.id}`}
                    >
                      <div className="flex items-start justify-between gap-2">
                        <button
                          onClick={() => openReport(item)}
                          className="text-left flex-1"
                          data-testid={`report-open-${item.id}`}
                        >
                          <div className="font-medium text-slate-800 leading-tight">{item.name}</div>
                          <div className="text-xs text-slate-500 mt-1 line-clamp-2">{item.description}</div>
                        </button>
                        <button
                          onClick={(e) => { e.stopPropagation(); toggleFav(item.id); }}
                          className={`p-1 rounded hover:bg-amber-50 ${item.is_favorite ? "text-amber-500" : "text-slate-300"}`}
                          data-testid={`fav-toggle-${item.id}`}
                          title={item.is_favorite ? "Remove favorite" : "Add to favorites"}
                        >
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
// Sale Report — live report page
// ---------------------------------------------------------------------------

const fmtDate = (iso) => {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "2-digit" });
  } catch { return String(iso).slice(0, 10); }
};

const firstOfMonth = () => {
  const d = new Date();
  return new Date(d.getFullYear(), d.getMonth(), 1).toISOString().slice(0, 10);
};
const today = () => new Date().toISOString().slice(0, 10);

export function SaleReportPage() {
  const [dateFrom, setDateFrom] = useState(firstOfMonth());
  const [dateTo, setDateTo] = useState(today());
  const [saleType, setSaleType] = useState("both");
  const [partyId, setPartyId] = useState("");
  const [distributors, setDistributors] = useState([]);
  const [retailers, setRetailers] = useState([]);
  const [data, setData] = useState({ rows: [], totals: { count: 0, subtotal: 0, gst_total: 0, total: 0 } });
  const [loading, setLoading] = useState(false);
  const nav = useNavigate();

  const loadParties = async () => {
    try {
      const [d, r] = await Promise.all([
        dms.listDistributors().catch(() => ({ data: [] })),
        dms.listRetailers ? dms.listRetailers().catch(() => ({ data: [] })) : Promise.resolve({ data: [] }),
      ]);
      setDistributors(d.data || []);
      setRetailers(r.data || []);
    } catch { /* silent */ }
  };

  const run = async () => {
    setLoading(true);
    try {
      const params = { sale_type: saleType };
      if (dateFrom) params.date_from = dateFrom;
      if (dateTo) params.date_to = dateTo;
      if (partyId && partyId !== "all") params.party_id = partyId;
      const d = await dms.runSaleReport(params);
      setData(d);
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Failed to run report");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadParties(); run(); /* eslint-disable-next-line */ }, []);

  const exportExcel = () => {
    const params = { sale_type: saleType };
    if (dateFrom) params.date_from = dateFrom;
    if (dateTo) params.date_to = dateTo;
    if (partyId && partyId !== "all") params.party_id = partyId;
    const url = dms.saleReportExportUrl(params);
    // Open in a new tab — axios interceptor adds Bearer via cookie/session isn't
    // used, so instead fetch as blob to preserve auth header.
    fetch(url, {
      headers: { "Authorization": "Bearer " + (localStorage.getItem("go_oil_token") || "") },
    })
      .then(async (res) => {
        if (!res.ok) throw new Error("Export failed");
        const blob = await res.blob();
        const a = document.createElement("a");
        const objUrl = URL.createObjectURL(blob);
        a.href = objUrl;
        a.download = `sale_report_${new Date().toISOString().slice(0, 10)}.xlsx`;
        document.body.appendChild(a); a.click(); document.body.removeChild(a);
        URL.revokeObjectURL(objUrl);
      })
      .catch((e) => toast.error(e.message || "Export failed"));
  };

  const printPdf = () => {
    // Uses the browser print dialog — user picks "Save as PDF"
    window.print();
  };

  const t = data.totals || {};

  return (
    <div className="space-y-5">
      <div className="flex items-center gap-2 print:hidden">
        <Button variant="outline" size="sm" onClick={() => nav("/dms/reports")} data-testid="back-to-reports">
          <ArrowLeft className="w-4 h-4 mr-2" /> Back to Reports
        </Button>
      </div>

      <PageHeader
        title="Sale Report"
        subtitle="Combined view of primary + secondary sales across your scope."
        icon={<TrendingUp className="w-6 h-6 text-[#a67c00]" />}
      />

      {/* Filter panel */}
      <Card className="p-4 print:hidden" data-testid="sale-report-filters">
        <div className="grid grid-cols-1 md:grid-cols-5 gap-3 items-end">
          <div>
            <Label>From</Label>
            <Input type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} data-testid="filter-date-from" />
          </div>
          <div>
            <Label>To</Label>
            <Input type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} data-testid="filter-date-to" />
          </div>
          <div>
            <Label>Sale Type</Label>
            <Select value={saleType} onValueChange={setSaleType}>
              <SelectTrigger data-testid="filter-sale-type"><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="both">Both</SelectItem>
                <SelectItem value="primary">Primary (Owner → Distributor)</SelectItem>
                <SelectItem value="secondary">Secondary (Distributor → Retailer)</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div>
            <Label>Party (optional)</Label>
            <Select value={partyId || "all"} onValueChange={setPartyId}>
              <SelectTrigger data-testid="filter-party"><SelectValue placeholder="All parties" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All parties</SelectItem>
                {distributors.map(d => (
                  <SelectItem key={d.id} value={d.id}>{d.name} (Distributor)</SelectItem>
                ))}
                {retailers.map(r => (
                  <SelectItem key={r.id} value={r.id}>{r.name} (Retailer)</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="flex gap-2">
            <Button onClick={run} disabled={loading} data-testid="run-report" className="bg-[#c9a227] hover:bg-[#a67c00]">
              {loading ? "Running…" : "Run"}
            </Button>
          </div>
        </div>
      </Card>

      {/* Totals strip */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <Card className="p-4">
          <div className="text-xs uppercase text-slate-500">Bills</div>
          <div className="text-xl font-semibold" data-testid="totals-count">{t.count || 0}</div>
          <div className="text-[11px] text-slate-500 mt-0.5">
            {t.primary_count || 0} primary • {t.secondary_count || 0} secondary
          </div>
        </Card>
        <Card className="p-4">
          <div className="text-xs uppercase text-slate-500">Subtotal</div>
          <div className="text-xl font-semibold" data-testid="totals-subtotal">{inr(t.subtotal)}</div>
        </Card>
        <Card className="p-4">
          <div className="text-xs uppercase text-slate-500">GST</div>
          <div className="text-xl font-semibold">{inr(t.gst_total)}</div>
        </Card>
        <Card className="p-4 border-amber-200">
          <div className="text-xs uppercase text-slate-500">Grand Total</div>
          <div className="text-xl font-semibold text-[#a67c00]" data-testid="totals-total">{inr(t.total)}</div>
        </Card>
      </div>

      {/* Actions */}
      <div className="flex items-center justify-between print:hidden">
        <div className="text-sm text-slate-500">
          Range: {fmtDate(dateFrom)} — {fmtDate(dateTo)} • {saleType}
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

      {/* Rows table */}
      <Card className="overflow-hidden">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Type</TableHead>
              <TableHead>Bill No</TableHead>
              <TableHead>Date</TableHead>
              <TableHead>Order No</TableHead>
              <TableHead>Party</TableHead>
              <TableHead className="text-right">Items</TableHead>
              <TableHead className="text-right">Subtotal</TableHead>
              <TableHead className="text-right">GST</TableHead>
              <TableHead className="text-right">Total</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {(data.rows || []).length === 0 && (
              <TableRow><TableCell colSpan={9} className="text-center text-slate-500 py-8">No bills in this range.</TableCell></TableRow>
            )}
            {(data.rows || []).map((r, idx) => (
              <TableRow key={r.bill_id || idx} data-testid={`row-${r.bill_no}`}>
                <TableCell>
                  {r.sale_type === "primary" ? (
                    <Badge className="bg-amber-100 text-amber-800 border-amber-200">Primary</Badge>
                  ) : (
                    <Badge className="bg-blue-100 text-blue-800 border-blue-200">Secondary</Badge>
                  )}
                </TableCell>
                <TableCell className="font-mono text-sm">{r.bill_no}</TableCell>
                <TableCell>{fmtDate(r.date)}</TableCell>
                <TableCell className="font-mono text-xs text-slate-600">{r.order_no || "—"}</TableCell>
                <TableCell>
                  <div className="font-medium">{r.party_name || "—"}</div>
                  <div className="text-xs text-slate-500">{r.party_type}</div>
                </TableCell>
                <TableCell className="text-right">{r.items_count}</TableCell>
                <TableCell className="text-right">{inr(r.subtotal)}</TableCell>
                <TableCell className="text-right">{inr(r.gst_total)}</TableCell>
                <TableCell className="text-right font-semibold">{inr(r.total)}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Card>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Coming Soon placeholder — any report_id that isn't yet live
// ---------------------------------------------------------------------------

export function ComingSoonReportPage() {
  const { reportId } = useParams();
  const nav = useNavigate();
  const [meta, setMeta] = useState(null);

  useEffect(() => {
    dms.reportsCatalog().then((d) => {
      for (const g of (d.groups || [])) {
        const found = g.items.find((it) => it.id === reportId);
        if (found) { setMeta({ ...found, category_label: g.label }); return; }
      }
      setMeta({ id: reportId, name: reportId, category_label: "Reports", description: "" });
    }).catch(() => setMeta({ id: reportId, name: reportId, category_label: "Reports", description: "" }));
  }, [reportId]);

  return (
    <div className="space-y-5">
      <Button variant="outline" size="sm" onClick={() => nav("/dms/reports")}>
        <ArrowLeft className="w-4 h-4 mr-2" /> Back to Reports
      </Button>
      <PageHeader
        title={meta?.name || "Report"}
        subtitle={meta?.category_label || ""}
        icon={<Clock className="w-6 h-6 text-slate-500" />}
      />
      <Card className="p-8 text-center">
        <Clock className="w-10 h-10 text-slate-400 mx-auto mb-3" />
        <div className="text-lg font-semibold text-slate-800 mb-1">Coming Soon</div>
        <div className="text-sm text-slate-500 max-w-md mx-auto">
          {meta?.description || "This report will be available in a future iteration."}
        </div>
        <div className="mt-6">
          <Link to="/dms/reports" className="text-[#a67c00] hover:underline text-sm">
            ← Browse other reports
          </Link>
        </div>
      </Card>
    </div>
  );
}

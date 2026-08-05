import React, { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { dms, inr, niceDate, statusPill } from "./api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Card } from "@/components/ui/card";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { toast } from "sonner";
import { Plus, Edit, ArrowLeft, Package, TrendingUp, ShoppingCart, Warehouse, ScrollText, Users, ChevronRight, Truck, CheckCircle2, ClipboardList, Trash2, IndianRupee, Percent, Handshake, IdCard, Paperclip, Boxes, History, Receipt } from "lucide-react";
import LocationDocumentsBlock from "./LocationDocumentsBlock";

// ============================================================================
// Shared: PageHeader
// ============================================================================
export function PageHeader({ title, subtitle, action, back }) {
  const nav = useNavigate();
  return (
    <div className="flex items-start justify-between gap-4 mb-5">
      <div className="flex items-start gap-3 min-w-0">
        {back && (
          <button onClick={() => nav(back)} className="mt-1 p-1.5 rounded-lg hover:bg-slate-100 shrink-0" data-testid="back-btn">
            <ArrowLeft size={18} className="text-slate-600" />
          </button>
        )}
        <div className="min-w-0">
          <h1 className="text-2xl font-bold text-slate-900 truncate">{title}</h1>
          {subtitle && <p className="text-sm text-slate-500 mt-0.5">{subtitle}</p>}
        </div>
      </div>
      {action}
    </div>
  );
}

export function EmptyState({ icon: Icon = Package, title, description, action }) {
  return (
    <Card className="p-12 text-center border-dashed">
      <div className="mx-auto h-12 w-12 rounded-full bg-slate-100 text-slate-400 flex items-center justify-center mb-4">
        <Icon size={22} />
      </div>
      <div className="font-semibold text-slate-900">{title}</div>
      {description && <div className="text-sm text-slate-500 mt-1">{description}</div>}
      {action && <div className="mt-4">{action}</div>}
    </Card>
  );
}

// Clickable Finance stat cell — used on the dashboard Cash & Bank Snapshot
function FinanceStat({ label, value, valueClass = "", borderLeft = false, onClick }) {
  return (
    <div
      role="button"
      tabIndex={0}
      onClick={onClick}
      onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") onClick?.(); }}
      className={`group rounded-lg cursor-pointer p-2 -m-2 hover:bg-amber-50/60 transition ${borderLeft ? "border-l pl-4" : ""}`}
      data-testid={`finance-stat-${label.toLowerCase().replace(/[^a-z0-9]+/g, "-")}`}
    >
      <div className="text-xs uppercase text-slate-500 flex items-center gap-1">
        {label}
        <ChevronRight size={11} className="text-slate-300 group-hover:text-[#a67c00] transition-colors" />
      </div>
      <div className={`text-xl font-bold ${valueClass} group-hover:underline decoration-dotted underline-offset-4`}>
        {value}
      </div>
    </div>
  );
}

// ============================================================================
// Owner — Dashboard
// ============================================================================
export function OwnerDashboardPage() {
  const [kpis, setKpis] = useState(null);
  const [recent, setRecent] = useState([]);
  const [finance, setFinance] = useState(null);
  const nav = useNavigate();
  useEffect(() => {
    dms.ownerDashboard().then(d => setKpis(d.kpis)).catch(() => {});
    dms.listOrders().then(d => setRecent((d.data || []).slice(0, 5))).catch(() => {});
    dms.financeSnapshot().then(setFinance).catch(() => {});
  }, []);
  const cards = [
    { label: "Distributors",         value: kpis?.distributors ?? "—",           icon: Handshake,    color: "teal",    to: "/dms/owner/distributors" },
    { label: "Products",             value: kpis?.products ?? "—",               icon: Package,      color: "indigo",  to: "/dms/owner/products" },
    { label: "Pending Orders",       value: kpis?.pending_orders ?? "—",         icon: ShoppingCart, color: "amber",   to: "/dms/owner/primary-orders?status=pending" },
    { label: "Ready to Dispatch",    value: kpis?.ready_to_go ?? "—",            icon: Truck,        color: "blue",    to: "/dms/owner/primary-orders?status=ready_to_go" },
    { label: "Revenue (MTD)",        value: kpis ? inr(kpis.revenue_mtd) : "—",  icon: TrendingUp,   color: "emerald", to: "/dms/owner/primary-orders" },
    { label: "Outstanding",          value: kpis ? inr(kpis.outstanding_receivable) : "—", icon: ScrollText, color: "rose",   to: "/dms/owner/ledger" },
    { label: "Inventory Value",      value: kpis ? inr(kpis.inventory_value) : "—", icon: Warehouse, color: "slate",   to: "/dms/owner/inventory" },
  ];
  const colorMap = {
    teal: "bg-[#faf6e6] text-[#a67c00]", indigo: "bg-indigo-50 text-indigo-700",
    amber: "bg-amber-50 text-amber-700", blue: "bg-blue-50 text-blue-700",
    emerald: "bg-emerald-50 text-emerald-700", rose: "bg-rose-50 text-rose-700",
    slate: "bg-slate-100 text-slate-700",
  };
  return (
    <div>
      <PageHeader title="Owner Dashboard" subtitle="Overview of your distribution business" />
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
        {cards.map(c => (
          <Card key={c.label} className="p-4 cursor-pointer group hover:shadow-md hover:border-amber-300 hover:-translate-y-0.5 transition-all relative"
                onClick={() => nav(c.to)} data-testid={`owner-kpi-${c.label.toLowerCase().replace(/[^a-z0-9]+/g, "-")}`}>
            <div className="flex items-start justify-between">
              <div className={`h-9 w-9 rounded-lg flex items-center justify-center ${colorMap[c.color]}`}><c.icon size={18} /></div>
              <ChevronRight size={16} className="text-slate-300 group-hover:text-[#a67c00] group-hover:translate-x-0.5 transition-all" />
            </div>
            <div className="mt-3 text-xs text-slate-500 uppercase tracking-wider">{c.label}</div>
            <div className="mt-1 text-xl font-bold text-slate-900 group-hover:text-[#8a6600] transition-colors">{c.value}</div>
            <div className="mt-2 text-[10px] text-slate-400 group-hover:text-[#a67c00] uppercase tracking-wider font-semibold opacity-0 group-hover:opacity-100 transition-opacity">
              View details →
            </div>
          </Card>
        ))}
      </div>

      <div className="mt-6">
        <div className="flex items-center justify-between mb-3">
          <h3 className="font-semibold text-slate-900">Cash &amp; Bank Snapshot</h3>
          <button onClick={() => nav("/dms/finance/bank-accounts")} className="text-sm text-[#a67c00] hover:underline">Manage →</button>
        </div>
        <Card className="p-5 border-amber-200" data-testid="finance-snapshot-card">
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
            <FinanceStat label="Cash in Bank" value={finance ? inr(finance.cash_in_bank) : "—"}
                          valueClass="text-emerald-700"
                          onClick={() => nav("/dms/finance/bank-accounts")} />
            <FinanceStat label="Cash in Hand" value={finance ? inr(finance.cash_in_hand) : "—"}
                          valueClass="text-amber-700"
                          onClick={() => nav("/dms/finance/cash-transactions")} />
            <FinanceStat label="Outstanding Loans" value={finance ? inr(finance.outstanding_loans) : "—"}
                          valueClass="text-rose-700"
                          onClick={() => nav("/dms/finance/loans")} />
            <FinanceStat label="Net Liquid" value={finance ? inr(finance.net_liquid) : "—"}
                          valueClass="text-slate-900" borderLeft
                          onClick={() => nav("/dms/finance/bank-accounts")} />
            <FinanceStat label="Net Position"
                          value={finance ? inr(finance.net_position) : "—"}
                          valueClass={finance && finance.net_position < 0 ? "text-rose-700" : "text-emerald-700"}
                          onClick={() => nav("/dms/owner/ledger")} />
          </div>
        </Card>
      </div>

      <div className="mt-6">
        <div className="flex items-center justify-between mb-3">
          <h3 className="font-semibold text-slate-900">Recent Primary Orders</h3>
          <button onClick={() => nav("/dms/owner/primary-orders")} className="text-sm text-[#a67c00] hover:underline">View all →</button>
        </div>
        <Card className="overflow-hidden">
          {recent.length === 0 ? (
            <div className="p-6 text-center text-sm text-slate-500">No orders yet</div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Order #</TableHead>
                  <TableHead>Distributor</TableHead>
                  <TableHead>Total</TableHead>
                  <TableHead>Fulfillment</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Placed</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {recent.map(o => (
                  <TableRow key={o.id} className="cursor-pointer hover:bg-slate-50" onClick={() => nav(`/dms/owner/primary-orders/${o.id}`)}>
                    <TableCell className="font-mono text-sm">{o.order_no}</TableCell>
                    <TableCell>{o.distributor_name}</TableCell>
                    <TableCell className="font-medium">{inr(o.total)}</TableCell>
                    <TableCell><div className="flex items-center gap-2"><div className="w-16 h-1.5 bg-slate-100 rounded overflow-hidden"><div className="h-full bg-[#faf6e6]0" style={{ width: `${o.fulfillment_pct}%` }} /></div><span className="text-xs text-slate-600">{o.fulfillment_pct}%</span></div></TableCell>
                    <TableCell><span className={`text-xs px-2 py-1 rounded-full border ${statusPill(o.status)}`}>{o.status.replace(/_/g, " ")}</span></TableCell>
                    <TableCell className="text-xs text-slate-500">{niceDate(o.created_at)}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </Card>
      </div>
    </div>
  );
}

// ============================================================================
// Owner — Categories
// ============================================================================
export function CategoriesPage() {
  const [list, setList] = useState([]);
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState({ name: "", description: "" });

  const load = () => dms.listCategories().then(d => setList(d.data));
  useEffect(() => { load(); }, []);

  const save = async () => {
    try {
      if (editing) { await dms.updateCategory(editing.id, form); toast.success("Updated"); }
      else { await dms.createCategory(form); toast.success("Created"); }
      setOpen(false); setEditing(null); setForm({ name: "", description: "" }); load();
    } catch (e) { toast.error(e.response?.data?.detail || "Failed"); }
  };

  const del = async (c) => {
    if (!window.confirm(`Delete "${c.name}"?`)) return;
    try { await dms.deleteCategory(c.id); toast.success("Deleted"); load(); }
    catch (e) { toast.error(e.response?.data?.detail || "Failed"); }
  };

  return (
    <div>
      <PageHeader
        title="Product Categories"
        subtitle="Group your products (Engine Oil, Gear Oil, Brake Fluid, etc.)"
        action={<Button onClick={() => { setEditing(null); setForm({ name: "", description: "" }); setOpen(true); }} className="bg-gradient-to-r from-[#c9a227] to-[#a67c00] hover:from-[#b8931f] hover:to-[#8a6600] text-white" data-testid="add-category-btn"><Plus size={16} className="mr-1" /> New Category</Button>}
      />
      <Card>
        <Table>
          <TableHeader><TableRow><TableHead>Name</TableHead><TableHead>Description</TableHead><TableHead>Created</TableHead><TableHead className="w-24"></TableHead></TableRow></TableHeader>
          <TableBody>
            {list.map(c => (
              <TableRow key={c.id}>
                <TableCell className="font-medium">{c.name}</TableCell>
                <TableCell className="text-slate-600 text-sm">{c.description || "—"}</TableCell>
                <TableCell className="text-xs text-slate-500">{niceDate(c.created_at)}</TableCell>
                <TableCell className="text-right">
                  <button onClick={() => { setEditing(c); setForm({ name: c.name, description: c.description || "" }); setOpen(true); }} className="p-1.5 hover:bg-slate-100 rounded" data-testid={`edit-cat-${c.id}`}><Edit size={14} /></button>
                  <button onClick={() => del(c)} className="p-1.5 hover:bg-rose-50 text-rose-600 rounded ml-1"><Trash2 size={14} /></button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
        {list.length === 0 && <div className="p-8 text-center text-sm text-slate-500">No categories yet</div>}
      </Card>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent>
          <DialogHeader><DialogTitle>{editing ? "Edit" : "New"} Category</DialogTitle></DialogHeader>
          <div className="space-y-3">
            <div><Label>Name</Label><Input value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} data-testid="cat-name-input" /></div>
            <div><Label>Description (optional)</Label><Textarea value={form.description} onChange={e => setForm({ ...form, description: e.target.value })} /></div>
          </div>
          <DialogFooter><Button onClick={save} className="bg-gradient-to-r from-[#c9a227] to-[#a67c00] hover:from-[#b8931f] hover:to-[#8a6600] text-white" data-testid="save-cat-btn">{editing ? "Update" : "Create"}</Button></DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

// ============================================================================
// Owner — Products
// ============================================================================
// ============================================================================
// Owner — UNIFIED Product Master (products + categories + current pricing in ONE page)
// ============================================================================
export function ProductsPage() {
  const nav = useNavigate();
  const [list, setList] = useState([]);
  const [cats, setCats] = useState([]);
  const [activeLines, setActiveLines] = useState({});     // product_id -> latest active circular line
  const [circulars, setCirculars] = useState([]);         // batch history
  const [loading, setLoading] = useState(true);

  const [prodOpen, setProdOpen] = useState(false);
  const [editingProd, setEditingProd] = useState(null);
  const [form, setForm] = useState({ material_description: "", grade_specs: "", pack_size: "", category_id: "", sku_code: "" });

  const [catsOpen, setCatsOpen] = useState(false);        // manage-categories modal
  const [histOpen, setHistOpen] = useState(false);        // price history / batch modal

  const [q, setQ] = useState("");
  const [catFilter, setCatFilter] = useState("all");

  const load = async () => {
    setLoading(true);
    try {
      const [pRes, cRes, ccRes] = await Promise.all([
        dms.listProducts(),
        dms.listCategories(),
        dms.listPriceCirculars(),
      ]);
      setList(pRes.data || []);
      setCats(cRes.data || []);
      const cs = ccRes.data || [];
      setCirculars(cs);
      // Fetch the LATEST active line for each product by pulling the current top circular's details
      // Build a merged map: for each product, find the newest active line across all circulars
      const map = {};
      // Fetch details of the top 5 circulars (batches are usually recent-heavy)
      const details = await Promise.all(cs.slice(0, 5).map(c => dms.getPriceCircular(c.id)));
      details.forEach(det => {
        (det.lines || []).forEach(l => {
          if (!l.is_active) return;
          const prev = map[l.product_id];
          if (!prev || (l.batch_no || 0) > (prev.batch_no || 0)) map[l.product_id] = l;
        });
      });
      setActiveLines(map);
    } finally { setLoading(false); }
  };
  useEffect(() => { load(); }, []);

  const openNewProduct = () => {
    if (cats.length === 0) { toast.error("Create a category first"); return; }
    setEditingProd(null);
    setForm({ material_description: "", grade_specs: "-", pack_size: "", category_id: cats[0].id, sku_code: "" });
    setProdOpen(true);
  };
  const openEditProduct = (p) => {
    setEditingProd(p);
    setForm({
      material_description: p.material_description || p.name || "",
      grade_specs: p.grade_specs || "-",
      pack_size: p.pack_size || "",
      category_id: p.category_id,
      sku_code: p.sku_code,
    });
    setProdOpen(true);
  };
  const saveProduct = async () => {
    try {
      const body = {
        name: `${form.material_description} (${form.pack_size})`,
        material_description: form.material_description,
        grade_specs: form.grade_specs,
        pack_size: form.pack_size,
        category_id: form.category_id,
        sku_code: form.sku_code,
        box_qty: editingProd?.box_qty ?? 1,
        unit_price: editingProd?.unit_price ?? 0,
      };
      if (editingProd) { await dms.updateProduct(editingProd.id, body); toast.success("Product updated"); }
      else { await dms.createProduct(body); toast.success("Product created — set pricing via Update Prices"); }
      setProdOpen(false); load();
    } catch (e) { toast.error(e.response?.data?.detail || "Failed"); }
  };

  const filtered = list.filter(p => {
    if (catFilter !== "all" && p.category_id !== catFilter) return false;
    if (q) {
      const s = q.toLowerCase();
      const hay = `${p.material_description || p.name} ${p.grade_specs} ${p.pack_size} ${p.category_name}`.toLowerCase();
      if (!hay.includes(s)) return false;
    }
    return true;
  });

  // group by category, PDF-style
  const grouped = {};
  filtered.forEach(p => {
    const k = p.category_name || "Uncategorised";
    if (!grouped[k]) grouped[k] = [];
    grouped[k].push(p);
  });
  const catOrder = Object.keys(grouped).sort();

  const activeCircular = circulars.find(c => c.is_active) || circulars[0];

  return (
    <div>
      <PageHeader
        title="Product Master"
        subtitle={`${list.length} products · ${cats.length} categories · ${activeCircular ? `Current pricing from ${activeCircular.batch_label}` : "No pricing set"}`}
        action={
          <div className="flex gap-2 flex-wrap">
            <Button variant="outline" onClick={() => setCatsOpen(true)} className="border-slate-300" data-testid="manage-categories-btn">
              <Boxes size={15} className="mr-1.5" /> Manage Categories
            </Button>
            <Button variant="outline" onClick={() => setHistOpen(true)} className="border-slate-300" data-testid="price-history-btn">
              <History size={15} className="mr-1.5" /> Price History
            </Button>
            <ExcelButtons onImported={load} />
            <Button onClick={openNewProduct} disabled={cats.length === 0} variant="outline" className="border-[#c9a227] text-[#8a6600] hover:bg-[#faf6e6]" data-testid="add-product-btn">
              <Plus size={15} className="mr-1.5" /> New Product
            </Button>
            <Button onClick={() => nav("/dms/owner/price-circulars/new")} className="bg-gradient-to-r from-[#c9a227] to-[#a67c00] hover:from-[#b8931f] hover:to-[#8a6600] text-white shadow-sm" data-testid="update-prices-btn">
              <IndianRupee size={15} className="mr-1.5" /> Update Prices
            </Button>
          </div>
        }
      />

      {cats.length === 0 && (
        <Card className="p-4 mb-4 bg-[#faf6e6] border-[#c9a227]/40 text-[#8a6600] text-sm flex items-center justify-between">
          <span>No categories yet. Click <b>Manage Categories</b> to add your first category, then add products.</span>
          <Button size="sm" onClick={() => setCatsOpen(true)} className="bg-[#c9a227] hover:bg-[#a67c00] text-white">Manage Categories</Button>
        </Card>
      )}

      <div className="flex flex-wrap gap-2 mb-4">
        <div className="flex-1 min-w-[220px]"><Input placeholder="Search Material / Grade / Pack…" value={q} onChange={e => setQ(e.target.value)} data-testid="prod-search-input" /></div>
        <div className="w-64">
          <Select value={catFilter} onValueChange={setCatFilter}>
            <SelectTrigger data-testid="prod-cat-filter"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Categories ({cats.length})</SelectItem>
              {cats.map(c => <SelectItem key={c.id} value={c.id}>{c.name}</SelectItem>)}
            </SelectContent>
          </Select>
        </div>
      </div>

      {loading && <div className="p-8 text-center text-sm text-slate-500">Loading…</div>}

      {!loading && catOrder.length === 0 && list.length > 0 && (
        <div className="p-8 text-center text-sm text-slate-500">No products match your filter</div>
      )}

      {!loading && catOrder.map((catName) => {
        const rows = grouped[catName];
        return (
          <Card key={catName} className="mb-4 overflow-hidden border-[#c9a227]/15 shadow-sm">
            <div className="px-4 py-2.5 bg-gradient-to-r from-[#faf6e6] to-white border-b border-[#c9a227]/20 flex items-center justify-between">
              <div className="font-display font-bold text-[#8a6600] text-sm uppercase tracking-wide">{catName}</div>
              <div className="text-xs text-slate-500">{rows.length} SKU{rows.length !== 1 ? "s" : ""}</div>
            </div>
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow className="bg-slate-50/60">
                    <TableHead className="min-w-[220px]">Material Description</TableHead>
                    <TableHead>Grade / Specs</TableHead>
                    <TableHead>Pack Size</TableHead>
                    <TableHead className="text-right">MRP</TableHead>
                    <TableHead className="text-right">DLP (current)</TableHead>
                    <TableHead>Margin %</TableHead>
                    <TableHead>Cash Coupon</TableHead>
                    <TableHead>FOC</TableHead>
                    <TableHead>Monthly Gift</TableHead>
                    <TableHead>Trade Disc.</TableHead>
                    <TableHead className="w-12 text-right"></TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {rows.map(p => {
                    const line = activeLines[p.id];
                    const dlp = line?.dlp ?? p.unit_price;
                    const prev = p.previous_price;
                    return (
                      <TableRow key={p.id} className="hover:bg-[#faf6e6]/40">
                        <TableCell className="font-medium text-slate-900">{p.material_description || p.name}</TableCell>
                        <TableCell><span className="text-xs bg-slate-100 text-slate-700 px-2 py-0.5 rounded font-mono">{p.grade_specs || "-"}</span></TableCell>
                        <TableCell className="text-slate-700 font-medium">{p.pack_size || "-"}</TableCell>
                        <TableCell className="text-right text-slate-700">{line?.mrp ? inr(line.mrp) : "—"}</TableCell>
                        <TableCell className="text-right">
                          <div className="font-bold text-[#8a6600]">{dlp ? inr(dlp) : "—"}</div>
                          {prev && prev !== dlp && (
                            <div className="text-[10px] text-slate-400 line-through">{inr(prev)}</div>
                          )}
                        </TableCell>
                        <TableCell>{line?.distributor_margin_pct ? <span className="text-xs bg-emerald-50 text-emerald-700 px-2 py-0.5 rounded font-semibold">{line.distributor_margin_pct}%</span> : "—"}</TableCell>
                        <TableCell className="text-xs text-slate-600 max-w-[110px] truncate" title={line?.cash_coupon}>{line?.cash_coupon || "—"}</TableCell>
                        <TableCell className="text-xs text-slate-600">{line?.foc_benefits || "—"}</TableCell>
                        <TableCell className="text-xs text-slate-600">{line?.monthly_gift || "—"}</TableCell>
                        <TableCell className="text-xs">{line?.trade_discount ? <span className="bg-blue-50 text-blue-700 px-2 py-0.5 rounded font-semibold">{line.trade_discount}</span> : "—"}</TableCell>
                        <TableCell className="text-right">
                          <button onClick={() => openEditProduct(p)} className="p-1.5 hover:bg-[#faf6e6] rounded" data-testid={`edit-prod-${p.id}`} title="Edit product info"><Edit size={14} className="text-[#a67c00]" /></button>
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            </div>
          </Card>
        );
      })}

      {/* ── Product create/edit modal ── */}
      <Dialog open={prodOpen} onOpenChange={setProdOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader><DialogTitle>{editingProd ? "Edit Product" : "New Product"}</DialogTitle></DialogHeader>
          <div className="grid grid-cols-2 gap-3">
            <div className="col-span-2"><Label>Material Description *</Label><Input value={form.material_description} onChange={e => setForm({ ...form, material_description: e.target.value })} data-testid="prod-name-input" placeholder="e.g. POWER 4T 20W40" /></div>
            <div><Label>Grade / Specs</Label><Input value={form.grade_specs} onChange={e => setForm({ ...form, grade_specs: e.target.value })} placeholder="e.g. SN, GL5" /></div>
            <div><Label>Pack Size *</Label><Input value={form.pack_size} onChange={e => setForm({ ...form, pack_size: e.target.value })} placeholder="e.g. 1 L / 5 kg" /></div>
            <div><Label>Category *</Label>
              <Select value={form.category_id} onValueChange={v => setForm({ ...form, category_id: v })}>
                <SelectTrigger data-testid="prod-cat-select"><SelectValue placeholder="Select" /></SelectTrigger>
                <SelectContent>{cats.map(c => <SelectItem key={c.id} value={c.id}>{c.name}</SelectItem>)}</SelectContent>
              </Select>
            </div>
            <div><Label>SKU Code *</Label><Input value={form.sku_code} onChange={e => setForm({ ...form, sku_code: e.target.value })} disabled={!!editingProd} data-testid="prod-sku-input" /></div>
            <div className="col-span-2 text-xs bg-[#faf6e6] border border-[#c9a227]/30 text-[#8a6600] rounded-lg p-3 mt-2">
              💡 To set MRP / DLP / margin / coupons for this product, click <b>Update Prices</b> on the main page — it publishes a new pricing batch and preserves history.
            </div>
          </div>
          <DialogFooter><Button onClick={saveProduct} className="bg-gradient-to-r from-[#c9a227] to-[#a67c00] hover:from-[#b8931f] hover:to-[#8a6600] text-white" data-testid="save-prod-btn">{editingProd ? "Update" : "Create"}</Button></DialogFooter>
        </DialogContent>
      </Dialog>

      {/* ── Manage categories modal ── */}
      <ManageCategoriesModal open={catsOpen} onOpenChange={setCatsOpen} onChanged={load} />

      {/* ── Price history / batches modal ── */}
      <PriceHistoryModal open={histOpen} onOpenChange={setHistOpen} circulars={circulars} />
    </div>
  );
}

// ── Inline: Categories management modal ──
function ManageCategoriesModal({ open, onOpenChange, onChanged }) {
  const [list, setList] = useState([]);
  const [name, setName] = useState("");
  const [desc, setDesc] = useState("");
  const [editing, setEditing] = useState(null);

  const load = () => dms.listCategories().then(d => setList(d.data || []));
  useEffect(() => { if (open) load(); }, [open]);

  const submit = async () => {
    if (!name.trim()) { toast.error("Name required"); return; }
    try {
      if (editing) { await dms.updateCategory(editing.id, { name, description: desc }); toast.success("Updated"); }
      else { await dms.createCategory({ name, description: desc }); toast.success("Created"); }
      setName(""); setDesc(""); setEditing(null); load(); onChanged?.();
    } catch (e) { toast.error(e.response?.data?.detail || "Failed"); }
  };
  const del = async (c) => {
    if (!window.confirm(`Delete "${c.name}"? Products in this category will be unassigned.`)) return;
    try { await dms.deleteCategory(c.id); toast.success("Deleted"); load(); onChanged?.(); }
    catch (e) { toast.error(e.response?.data?.detail || "Failed"); }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogHeader><DialogTitle>Manage Categories</DialogTitle></DialogHeader>
        <div className="grid grid-cols-3 gap-2 mb-3 items-end">
          <div className="col-span-1"><Label>Category Name</Label><Input value={name} onChange={e => setName(e.target.value)} placeholder="e.g. MCO — Synthetic Blend" data-testid="cat-name-input" /></div>
          <div className="col-span-1"><Label>Description</Label><Input value={desc} onChange={e => setDesc(e.target.value)} placeholder="optional" /></div>
          <div><Button onClick={submit} className="bg-gradient-to-r from-[#c9a227] to-[#a67c00] hover:from-[#b8931f] hover:to-[#8a6600] text-white w-full" data-testid="save-cat-btn">{editing ? "Update" : "Add"}</Button></div>
        </div>
        {editing && <div className="text-xs text-slate-500 mb-2">Editing "{editing.name}" — <button className="text-[#a67c00] underline" onClick={() => { setEditing(null); setName(""); setDesc(""); }}>cancel</button></div>}
        <Card className="max-h-[420px] overflow-y-auto">
          <Table>
            <TableHeader><TableRow><TableHead>Name</TableHead><TableHead>Description</TableHead><TableHead className="w-24 text-right"></TableHead></TableRow></TableHeader>
            <TableBody>
              {list.map(c => (
                <TableRow key={c.id} className="hover:bg-slate-50">
                  <TableCell className="font-medium">{c.name}</TableCell>
                  <TableCell className="text-slate-600 text-sm">{c.description || "—"}</TableCell>
                  <TableCell className="text-right">
                    <button onClick={() => { setEditing(c); setName(c.name); setDesc(c.description || ""); }} className="p-1.5 hover:bg-[#faf6e6] rounded" data-testid={`edit-cat-${c.id}`}><Edit size={14} className="text-[#a67c00]" /></button>
                    <button onClick={() => del(c)} className="p-1.5 hover:bg-rose-50 text-rose-600 rounded ml-1"><Trash2 size={14} /></button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
          {list.length === 0 && <div className="p-6 text-center text-sm text-slate-500">No categories yet</div>}
        </Card>
      </DialogContent>
    </Dialog>
  );
}

// ── Inline: Price history modal (batch list) ──
function PriceHistoryModal({ open, onOpenChange, circulars }) {
  const nav = useNavigate();
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogHeader><DialogTitle>Price History — All Batches</DialogTitle></DialogHeader>
        <div className="space-y-2 max-h-[500px] overflow-y-auto">
          {circulars.length === 0 && <div className="p-6 text-center text-sm text-slate-500">No price batches yet. Click <b>Update Prices</b> to publish the first one.</div>}
          {circulars.map(c => (
            <button key={c.id} onClick={() => { onOpenChange(false); nav(`/dms/owner/price-circulars/${c.id}`); }}
                    className="w-full text-left p-4 rounded-lg border border-[#c9a227]/15 hover:border-[#c9a227] hover:bg-[#faf6e6]/40 transition flex items-center justify-between">
              <div>
                <div className="flex items-center gap-2">
                  <div className="font-display font-bold text-slate-900">{c.title}</div>
                  {c.is_active && <span className="text-[10px] uppercase font-bold bg-[#c9a227] text-white px-2 py-0.5 rounded">Active</span>}
                </div>
                <div className="text-xs text-slate-500 mt-1">Effective {c.effective_date} · {c.lines_count || 0} products · {c.batch_label}</div>
              </div>
              <ChevronRight size={18} className="text-slate-400" />
            </button>
          ))}
        </div>
      </DialogContent>
    </Dialog>
  );
}

// ============================================================================
// Owner — Distributors list + detail with KYC + visibility
// ============================================================================
export function DistributorsPage() {
  const [list, setList] = useState([]);
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({});
  const nav = useNavigate();

  const load = () => dms.listDistributors().then(d => setList(d.data));
  useEffect(() => { load(); }, []);

  const openNew = () => { setForm({ name: "", email: "", password: "Demo@2026", phone: "", address: "", region: "", gstin: "", pan: "", shop_license: "", bank_name: "", bank_account: "", bank_ifsc: "", credit_limit: 500000 }); setOpen(true); };

  const save = async () => {
    try {
      await dms.createDistributor(form);
      toast.success("Distributor onboarded");
      setOpen(false); load();
    } catch (e) { toast.error(e.response?.data?.detail || "Failed"); }
  };

  return (
    <div>
      <PageHeader
        title="Distributors"
        subtitle="Onboard distributors and manage KYC + product visibility"
        action={<Button onClick={openNew} className="bg-gradient-to-r from-[#c9a227] to-[#a67c00] hover:from-[#b8931f] hover:to-[#8a6600] text-white" data-testid="add-dist-btn"><Plus size={16} className="mr-1" /> New Distributor</Button>}
      />
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
        {list.map(d => (
          <Card key={d.id} className="p-4 hover:shadow-md transition cursor-pointer" onClick={() => nav(`/dms/owner/distributors/${d.id}`)} data-testid={`dist-card-${d.id}`}>
            <div className="flex items-start justify-between">
              <div>
                <div className="font-semibold text-slate-900">{d.name}</div>
                <div className="text-xs text-slate-500 mt-0.5">{d.email}</div>
                <div className="text-xs text-slate-500">{d.phone}</div>
              </div>
              <span className="text-[10px] uppercase tracking-wider bg-[#faf6e6] text-[#a67c00] px-2 py-1 rounded">{d.region || "—"}</span>
            </div>
            <div className="mt-3 pt-3 border-t border-slate-100 flex items-center justify-between text-xs">
              <span className="text-slate-500">Credit Limit</span>
              <span className="font-semibold text-slate-800">{inr(d.credit_limit)}</span>
            </div>
            <div className="mt-1 flex items-center justify-between text-xs">
              <span className="text-slate-500">GSTIN</span>
              <span className="font-mono text-slate-700">{d.kyc?.gstin || "—"}</span>
            </div>
            <div className="mt-3 text-[#a67c00] text-xs font-medium flex items-center">Manage → <ChevronRight size={14} /></div>
          </Card>
        ))}
      </div>
      {list.length === 0 && <EmptyState icon={Handshake} title="No distributors yet" description="Create your first distributor to start receiving orders" />}

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="max-w-3xl max-h-[85vh] overflow-y-auto">
          <DialogHeader><DialogTitle>New Distributor + KYC</DialogTitle></DialogHeader>
          <div className="space-y-4">
            <div>
              <div className="text-xs uppercase tracking-wider font-semibold text-slate-500 mb-2">Basic Info</div>
              <div className="grid grid-cols-2 gap-3">
                <div><Label>Business Name *</Label><Input value={form.name || ""} onChange={e => setForm({ ...form, name: e.target.value })} data-testid="d-name" /></div>
                <div><Label>Phone *</Label><Input value={form.phone || ""} onChange={e => setForm({ ...form, phone: e.target.value })} /></div>
                <div><Label>Login Email *</Label><Input type="email" value={form.email || ""} onChange={e => setForm({ ...form, email: e.target.value })} data-testid="d-email" /></div>
                <div><Label>Login Password *</Label><Input value={form.password || ""} onChange={e => setForm({ ...form, password: e.target.value })} /></div>
                <div className="col-span-2"><Label>Address *</Label><Textarea rows={2} value={form.address || ""} onChange={e => setForm({ ...form, address: e.target.value })} /></div>
                <div><Label>Region</Label><Input value={form.region || ""} onChange={e => setForm({ ...form, region: e.target.value })} /></div>
                <div><Label>Credit Limit (₹)</Label><Input type="number" value={form.credit_limit || ""} onChange={e => setForm({ ...form, credit_limit: Number(e.target.value) })} /></div>
              </div>
            </div>
            <div>
              <div className="text-xs uppercase tracking-wider font-semibold text-slate-500 mb-2 flex items-center gap-1"><IdCard size={14} /> KYC Details</div>
              <div className="grid grid-cols-2 gap-3">
                <div><Label>GSTIN</Label><Input value={form.gstin || ""} onChange={e => setForm({ ...form, gstin: e.target.value })} /></div>
                <div><Label>PAN</Label><Input value={form.pan || ""} onChange={e => setForm({ ...form, pan: e.target.value })} /></div>
                <div><Label>Shop / Trade License</Label><Input value={form.shop_license || ""} onChange={e => setForm({ ...form, shop_license: e.target.value })} /></div>
                <div><Label>Bank Name</Label><Input value={form.bank_name || ""} onChange={e => setForm({ ...form, bank_name: e.target.value })} /></div>
                <div><Label>Bank Account</Label><Input value={form.bank_account || ""} onChange={e => setForm({ ...form, bank_account: e.target.value })} /></div>
                <div><Label>IFSC</Label><Input value={form.bank_ifsc || ""} onChange={e => setForm({ ...form, bank_ifsc: e.target.value })} /></div>
              </div>
            </div>
            <LocationDocumentsBlock
              lat={form.gps_lat ?? ""}
              lng={form.gps_lng ?? ""}
              locationLink={form.location_link || ""}
              onLat={(v) => setForm(f => ({ ...f, gps_lat: v === "" ? null : Number(v) }))}
              onLng={(v) => setForm(f => ({ ...f, gps_lng: v === "" ? null : Number(v) }))}
              onLocationLink={(v) => setForm(f => ({ ...f, location_link: v }))}
              documents={form.documents || []}
              onDocuments={(docs) => setForm(f => ({ ...f, documents: docs }))}
              helpText="After the distributor logs in, they can update their exact Latitude / Longitude from their profile if needed."
            />
          </div>
          <DialogFooter><Button onClick={save} className="bg-gradient-to-r from-[#c9a227] to-[#a67c00] hover:from-[#b8931f] hover:to-[#8a6600] text-white" data-testid="save-dist-btn">Create Distributor</Button></DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

export function DistributorDetailPage() {
  const { id } = useParams();
  const [d, setD] = useState(null);
  const [vis, setVis] = useState([]);
  const [tab, setTab] = useState("kyc");
  const [editKyc, setEditKyc] = useState(false);
  const [form, setForm] = useState({});

  const load = async () => {
    const [dd, vv] = await Promise.all([dms.getDistributor(id), dms.getDistVisibility(id)]);
    setD(dd); setVis(vv.data);
    setForm({ ...dd, ...(dd.kyc || {}) });
  };
  useEffect(() => { load(); }, [id]);

  const saveKyc = async () => {
    try {
      const kyc = ["gstin", "pan", "aadhaar", "shop_license", "bank_name", "bank_account", "bank_ifsc", "notes"].reduce((a, k) => (a[k] = form[k] || "", a), {});
      await dms.updateDistributor(id, {
        name: form.name, phone: form.phone, address: form.address, region: form.region, credit_limit: Number(form.credit_limit || 0), kyc,
      });
      toast.success("Updated"); setEditKyc(false); load();
    } catch (e) { toast.error(e.response?.data?.detail || "Failed"); }
  };

  const toggleVisibility = async (pid, visible) => {
    try { await dms.setDistVisibility(id, { product_id: pid, visible }); setVis(vis.map(v => v.product_id === pid ? { ...v, visible } : v)); }
    catch (e) { toast.error("Failed"); }
  };

  if (!d) return <div className="p-8 text-center text-slate-500">Loading…</div>;

  return (
    <div>
      <PageHeader
        title={d.name}
        subtitle={`${d.email} • ${d.region || "—"} • Credit ${inr(d.credit_limit)}`}
        back="/dms/owner/distributors"
      />
      <div className="flex gap-2 mb-4 border-b border-slate-200">
        {[
          { k: "kyc", label: "KYC & Profile" },
          { k: "visibility", label: "Product Visibility" },
        ].map(t => (
          <button key={t.k} onClick={() => setTab(t.k)} className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px ${tab === t.k ? "border-[#a67c00] text-[#a67c00]" : "border-transparent text-slate-500 hover:text-slate-700"}`} data-testid={`tab-${t.k}`}>{t.label}</button>
        ))}
      </div>

      {tab === "kyc" && (
        <Card className="p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold">KYC Documents & Profile</h3>
            {!editKyc && <Button variant="outline" size="sm" onClick={() => setEditKyc(true)} data-testid="edit-kyc-btn"><Edit size={14} className="mr-1" /> Edit</Button>}
          </div>
          {!editKyc ? (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-x-8 gap-y-3 text-sm">
              {[
                ["Business Name", d.name], ["Phone", d.phone], ["Email", d.email],
                ["Address", d.address], ["Region", d.region], ["Credit Limit", inr(d.credit_limit)],
                ["GSTIN", d.kyc?.gstin], ["PAN", d.kyc?.pan], ["Shop License", d.kyc?.shop_license],
                ["Bank Name", d.kyc?.bank_name], ["Account No.", d.kyc?.bank_account], ["IFSC", d.kyc?.bank_ifsc],
              ].map(([k, v]) => (
                <div key={k} className="flex justify-between border-b border-slate-100 py-1.5">
                  <span className="text-slate-500">{k}</span>
                  <span className="text-slate-900 font-medium">{v || "—"}</span>
                </div>
              ))}
            </div>
          ) : (
            <div className="grid grid-cols-2 gap-3">
              {["name", "phone", "address", "region", "credit_limit", "gstin", "pan", "shop_license", "bank_name", "bank_account", "bank_ifsc"].map(k => (
                <div key={k} className={k === "address" ? "col-span-2" : ""}><Label className="capitalize">{k.replace(/_/g, " ")}</Label><Input value={form[k] || ""} onChange={e => setForm({ ...form, [k]: e.target.value })} /></div>
              ))}
              <div className="col-span-2 flex justify-end gap-2 mt-3">
                <Button variant="outline" onClick={() => setEditKyc(false)}>Cancel</Button>
                <Button onClick={saveKyc} className="bg-gradient-to-r from-[#c9a227] to-[#a67c00] hover:from-[#b8931f] hover:to-[#8a6600] text-white" data-testid="save-kyc-btn">Save</Button>
              </div>
            </div>
          )}
        </Card>
      )}

      {tab === "visibility" && (
        <Card>
          <div className="p-4 border-b border-slate-100">
            <div className="text-sm text-slate-600">Toggle products this distributor is allowed to see. Turning OFF a product hides it from their catalog immediately.</div>
          </div>
          <Table>
            <TableHeader><TableRow><TableHead>SKU</TableHead><TableHead>Product</TableHead><TableHead className="text-right">Visible</TableHead></TableRow></TableHeader>
            <TableBody>
              {vis.map(v => (
                <TableRow key={v.product_id}>
                  <TableCell className="font-mono text-xs">{v.sku_code}</TableCell>
                  <TableCell>{v.product_name}</TableCell>
                  <TableCell className="text-right"><Switch checked={v.visible} onCheckedChange={c => toggleVisibility(v.product_id, c)} data-testid={`vis-${v.product_id}`} /></TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Card>
      )}
    </div>
  );
}

// ============================================================================
// Owner — Primary Orders list + detail (fulfillment)
// ============================================================================
export function OwnerPrimaryOrdersPage() {
  const [list, setList] = useState([]);
  const [filter, setFilter] = useState("");
  const nav = useNavigate();
  useEffect(() => { dms.listOrders(filter || undefined).then(d => setList(d.data)); }, [filter]);

  return (
    <div>
      <PageHeader title="Primary Orders" subtitle="Orders from distributors — fulfill and dispatch" />
      <div className="flex gap-2 mb-4 flex-wrap">
        {[{ k: "", label: "All" }, { k: "pending", label: "Pending" }, { k: "partially_fulfilled", label: "Partial" }, { k: "fulfilled", label: "Fulfilled" }, { k: "ready_to_go", label: "Ready" }, { k: "received", label: "Received" }].map(f => (
          <button key={f.k} onClick={() => setFilter(f.k)} className={`px-3 py-1.5 text-xs rounded-full border ${filter === f.k ? "bg-[#c9a227] text-white border-[#a67c00]" : "bg-white border-slate-200 text-slate-700 hover:border-slate-300"}`} data-testid={`filter-${f.k || "all"}`}>{f.label}</button>
        ))}
      </div>
      <Card>
        <Table>
          <TableHeader><TableRow>
            <TableHead>Order #</TableHead><TableHead>Distributor</TableHead><TableHead>Items</TableHead>
            <TableHead>Total</TableHead><TableHead>Fulfillment</TableHead><TableHead>Status</TableHead><TableHead>Placed</TableHead>
          </TableRow></TableHeader>
          <TableBody>
            {list.map(o => (
              <TableRow key={o.id} className="cursor-pointer hover:bg-slate-50" onClick={() => nav(`/dms/owner/primary-orders/${o.id}`)} data-testid={`ord-row-${o.id}`}>
                <TableCell className="font-mono text-sm">{o.order_no}</TableCell>
                <TableCell className="font-medium">{o.distributor_name}</TableCell>
                <TableCell className="text-sm text-slate-600">{o.items.length}</TableCell>
                <TableCell className="font-semibold">{inr(o.total)}</TableCell>
                <TableCell><div className="flex items-center gap-2 min-w-[100px]"><div className="w-16 h-1.5 bg-slate-100 rounded overflow-hidden"><div className="h-full bg-[#faf6e6]0" style={{ width: `${o.fulfillment_pct}%` }} /></div><span className="text-xs text-slate-600">{o.fulfillment_pct}%</span></div></TableCell>
                <TableCell><span className={`text-xs px-2 py-1 rounded-full border ${statusPill(o.status)}`}>{o.status.replace(/_/g, " ")}</span></TableCell>
                <TableCell className="text-xs text-slate-500">{niceDate(o.created_at)}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
        {list.length === 0 && <div className="p-8 text-center text-sm text-slate-500">No orders</div>}
      </Card>
    </div>
  );
}

export function OwnerOrderDetailPage() {
  const { id } = useParams();
  const [order, setOrder] = useState(null);
  const [busy, setBusy] = useState(false);
  const [attachUrl, setAttachUrl] = useState("");
  const [attachName, setAttachName] = useState("");

  const load = () => dms.getOrder(id).then(setOrder);
  useEffect(() => { load(); }, [id]);

  const setLine = async (pid, qty) => {
    setBusy(true);
    try { await dms.fulfillLine(id, { product_id: pid, qty_boxes_fulfilled: Number(qty) }); await load(); }
    catch (e) { toast.error(e.response?.data?.detail || "Failed"); }
    setBusy(false);
  };

  const ready = async () => {
    if (!window.confirm("Mark this order Ready to Go? This will generate the e-Bill and reduce your inventory.")) return;
    setBusy(true);
    try { await dms.markReady(id); toast.success("Order marked Ready to Go — e-Bill generated"); await load(); }
    catch (e) { toast.error(e.response?.data?.detail || "Failed"); }
    setBusy(false);
  };

  const uploadAttachment = async () => {
    if (!attachUrl) return;
    try { await dms.addAttachment({ reference_id: id, kind: "invoice", name: attachName || "Invoice", url: attachUrl }); setAttachUrl(""); setAttachName(""); load(); toast.success("Attached"); }
    catch { toast.error("Failed"); }
  };

  if (!order) return <div className="p-8 text-center text-slate-500">Loading…</div>;

  const canFulfill = order.status !== "received" && order.status !== "ready_to_go";
  const canReady = ["pending", "partially_fulfilled", "fulfilled"].includes(order.status) && order.items.some(it => it.qty_boxes_fulfilled > 0);

  return (
    <div>
      <PageHeader
        title={order.order_no}
        subtitle={`${order.distributor_name} • Placed ${niceDate(order.created_at)}`}
        back="/dms/owner/primary-orders"
        action={<div className="flex gap-2">
          <Button variant="outline" onClick={() => window.open(`/dms/print/purchase-order/${order.id}`, "_blank")} data-testid="print-po-btn"><span className="mr-1">🖨</span> Print PO</Button>
          {order.ebill_id && <Button variant="outline" onClick={() => window.open(`/dms/print/ebill/${order.ebill_id}`, "_blank")} data-testid="print-ebill-btn"><span className="mr-1">🖨</span> Print e-Bill</Button>}
          {canReady && <Button onClick={ready} disabled={busy} className="bg-gradient-to-r from-[#c9a227] to-[#a67c00] hover:from-[#b8931f] hover:to-[#8a6600] text-white" data-testid="mark-ready-btn"><Truck size={16} className="mr-1" /> Mark Ready to Go</Button>}
        </div>}
      />
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-4">
        <Card className="p-4"><div className="text-xs text-slate-500 uppercase tracking-wider">Status</div><div className="mt-1"><span className={`text-sm px-2.5 py-1 rounded-full border ${statusPill(order.status)}`}>{order.status.replace(/_/g, " ")}</span></div></Card>
        <Card className="p-4"><div className="text-xs text-slate-500 uppercase tracking-wider">Fulfillment</div><div className="mt-1 flex items-center gap-3"><div className="flex-1 h-2 bg-slate-100 rounded overflow-hidden"><div className="h-full bg-[#faf6e6]0 transition-all" style={{ width: `${order.fulfillment_pct}%` }} /></div><span className="font-bold text-slate-900">{order.fulfillment_pct}%</span></div></Card>
        <Card className="p-4"><div className="text-xs text-slate-500 uppercase tracking-wider">Order Total</div><div className="mt-1 font-bold text-lg text-slate-900">{inr(order.total)}</div><div className="text-xs text-slate-500">Sub {inr(order.subtotal)} + GST {inr(order.gst_total)}</div></Card>
      </div>

      <Card className="mb-4">
        <div className="p-4 border-b border-slate-100 font-semibold">Line Items — set fulfillment quantity</div>
        <Table>
          <TableHeader><TableRow><TableHead>Product</TableHead><TableHead>Price</TableHead><TableHead>Ordered</TableHead><TableHead>Fulfilled</TableHead><TableHead>Line Total</TableHead></TableRow></TableHeader>
          <TableBody>
            {order.items.map(it => (
              <TableRow key={it.product_id}>
                <TableCell><div className="font-medium">{it.product_name}</div><div className="text-xs font-mono text-slate-500">{it.sku_code}</div></TableCell>
                <TableCell>{inr(it.unit_price)}</TableCell>
                <TableCell>{it.qty_boxes_ordered} boxes</TableCell>
                <TableCell>
                  {canFulfill ? (
                    <Input type="number" min={0} max={it.qty_boxes_ordered} defaultValue={it.qty_boxes_fulfilled}
                      onBlur={e => setLine(it.product_id, e.target.value)} className="w-24" disabled={busy} data-testid={`fill-${it.product_id}`} />
                  ) : (
                    <span className="font-semibold">{it.qty_boxes_fulfilled} boxes</span>
                  )}
                </TableCell>
                <TableCell className="font-medium">{inr(it.line_total)}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Card>

      {order.ebill && (
        <Card className="mb-4 p-4">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2"><Receipt size={18} className="text-[#a67c00]" /><div className="font-semibold">e-Bill</div><span className="font-mono text-sm text-slate-600">{order.ebill.ebill_no}</span></div>
            <div className="text-right"><div className="font-bold text-lg">{inr(order.ebill.total)}</div><div className="text-xs text-slate-500">{niceDate(order.ebill.created_at)}</div></div>
          </div>
          <div className="text-sm text-slate-600">Subtotal {inr(order.ebill.subtotal)} • GST {inr(order.ebill.gst_total)} • {order.ebill.items.length} line items dispatched</div>
        </Card>
      )}

      {order.ebill && (
        <Card className="mb-4">
          <div className="p-4 border-b border-slate-100 flex items-center gap-2"><Paperclip size={16} /><div className="font-semibold">Supporting Documents</div></div>
          <div className="p-4">
            {(order.attachments || []).length > 0 && (
              <div className="space-y-2 mb-3">
                {order.attachments.map(a => (
                  <a key={a.id} href={a.url} target="_blank" rel="noreferrer" className="flex items-center gap-2 text-sm text-[#a67c00] hover:underline"><Paperclip size={14} /> {a.name}</a>
                ))}
              </div>
            )}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
              <Input placeholder="Document name" value={attachName} onChange={e => setAttachName(e.target.value)} />
              <Input placeholder="Paste public URL (image/PDF)" className="md:col-span-1" value={attachUrl} onChange={e => setAttachUrl(e.target.value)} />
              <Button onClick={uploadAttachment} variant="outline" data-testid="add-attachment-btn"><Paperclip size={14} className="mr-1" />Attach</Button>
            </div>
          </div>
        </Card>
      )}
    </div>
  );
}

// ============================================================================
// Owner — Inventory
// ============================================================================
export function OwnerInventoryPage() {
  const [inv, setInv] = useState({ data: [], total_value: 0 });
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ product_id: "", delta_boxes: 0, reason: "stock_in" });
  const [prods, setProds] = useState([]);

  const load = () => Promise.all([dms.ownerInventory(), dms.listProducts()]).then(([i, p]) => { setInv(i); setProds(p.data); });
  useEffect(() => { load(); }, []);

  const save = async () => {
    try { await dms.ownerInvAdjust({ ...form, delta_boxes: Number(form.delta_boxes) }); toast.success("Stock updated"); setOpen(false); setForm({ product_id: "", delta_boxes: 0, reason: "stock_in" }); load(); }
    catch (e) { toast.error(e.response?.data?.detail || "Failed"); }
  };

  return (
    <div>
      <PageHeader
        title="Owner Inventory"
        subtitle={`Total value: ${inr(inv.total_value)}`}
        action={<Button onClick={() => setOpen(true)} className="bg-gradient-to-r from-[#c9a227] to-[#a67c00] hover:from-[#b8931f] hover:to-[#8a6600] text-white" data-testid="stock-in-btn"><Plus size={16} className="mr-1" /> Stock Adjustment</Button>}
      />
      <Card>
        <Table>
          <TableHeader><TableRow><TableHead>SKU</TableHead><TableHead>Product</TableHead><TableHead>Boxes</TableHead><TableHead>Bottles/Box</TableHead><TableHead>Price / Box</TableHead><TableHead>Total Value</TableHead></TableRow></TableHeader>
          <TableBody>
            {inv.data.map(r => (
              <TableRow key={r.id}>
                <TableCell className="font-mono text-xs">{r.sku_code}</TableCell>
                <TableCell className="font-medium">{r.product_name}</TableCell>
                <TableCell className="font-bold text-slate-900">{r.qty_boxes}</TableCell>
                <TableCell>{r.box_qty}</TableCell>
                <TableCell>{inr(r.unit_price)}</TableCell>
                <TableCell className="font-semibold">{inr(r.value)}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
        {inv.data.length === 0 && <div className="p-8 text-center text-sm text-slate-500">No inventory</div>}
      </Card>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent>
          <DialogHeader><DialogTitle>Stock Adjustment</DialogTitle></DialogHeader>
          <div className="space-y-3">
            <div><Label>Product *</Label>
              <Select value={form.product_id} onValueChange={v => setForm({ ...form, product_id: v })}>
                <SelectTrigger data-testid="adj-prod-select"><SelectValue placeholder="Select product" /></SelectTrigger>
                <SelectContent>{prods.map(p => <SelectItem key={p.id} value={p.id}>{p.name} ({p.sku_code})</SelectItem>)}</SelectContent>
              </Select>
            </div>
            <div><Label>Change in Boxes (+/-) *</Label><Input type="number" value={form.delta_boxes} onChange={e => setForm({ ...form, delta_boxes: e.target.value })} data-testid="adj-qty" /></div>
            <div><Label>Reason</Label><Input value={form.reason} onChange={e => setForm({ ...form, reason: e.target.value })} /></div>
          </div>
          <DialogFooter><Button onClick={save} className="bg-gradient-to-r from-[#c9a227] to-[#a67c00] hover:from-[#b8931f] hover:to-[#8a6600] text-white" data-testid="save-adj-btn">Save</Button></DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

// ============================================================================
// Owner — Primary Ledger (also used by owner accountant + distributor)
// ============================================================================
export function PrimaryLedgerPage() {
  const [data, setData] = useState({ entries: [], summary: [] });
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ distributor_id: "", amount: "", method: "bank_transfer", description: "" });
  const [dists, setDists] = useState([]);
  const load = () => Promise.all([dms.primaryLedger(), dms.listDistributors()]).then(([l, d]) => { setData(l); setDists(d.data); });
  useEffect(() => { load(); }, []);

  const save = async () => {
    try { await dms.recordPrimaryPayment({ ...form, amount: Number(form.amount) }); toast.success("Payment recorded"); setOpen(false); setForm({ distributor_id: "", amount: "", method: "bank_transfer", description: "" }); load(); }
    catch (e) { toast.error(e.response?.data?.detail || "Failed"); }
  };

  return (
    <div>
      <PageHeader
        title="Primary Sales Ledger"
        subtitle="Owner ↔ Distributor transactions"
        action={<Button onClick={() => setOpen(true)} className="bg-gradient-to-r from-[#c9a227] to-[#a67c00] hover:from-[#b8931f] hover:to-[#8a6600] text-white" data-testid="record-payment-btn"><IndianRupee size={16} className="mr-1" /> Record Payment</Button>}
      />
      <div className="mb-4">
        <h3 className="text-sm font-semibold text-slate-700 mb-2">Outstanding by Distributor</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {data.summary.map(s => (
            <Card key={s.distributor_id} className="p-4">
              <div className="text-sm font-semibold">{s.distributor_name}</div>
              <div className="mt-2 grid grid-cols-3 gap-2 text-center">
                <div><div className="text-[10px] uppercase tracking-wider text-slate-500">Billed</div><div className="font-semibold text-slate-900 text-sm">{inr(s.billed)}</div></div>
                <div><div className="text-[10px] uppercase tracking-wider text-slate-500">Paid</div><div className="font-semibold text-emerald-700 text-sm">{inr(s.paid)}</div></div>
                <div><div className="text-[10px] uppercase tracking-wider text-slate-500">Due</div><div className="font-bold text-rose-700 text-sm">{inr(s.outstanding)}</div></div>
              </div>
            </Card>
          ))}
          {data.summary.length === 0 && <Card className="p-6 col-span-full text-center text-sm text-slate-500">No transactions yet</Card>}
        </div>
      </div>
      <Card>
        <div className="p-4 border-b border-slate-100 font-semibold">Ledger Entries</div>
        <Table>
          <TableHeader><TableRow><TableHead>Date</TableHead><TableHead>Distributor</TableHead><TableHead>Reference</TableHead><TableHead>Type</TableHead><TableHead className="text-right">Amount</TableHead></TableRow></TableHeader>
          <TableBody>
            {data.entries.map(e => {
              const dName = dists.find(d => d.id === e.distributor_id)?.name || e.distributor_id;
              return (
                <TableRow key={e.id}>
                  <TableCell className="text-xs text-slate-500">{niceDate(e.at)}</TableCell>
                  <TableCell className="font-medium">{dName}</TableCell>
                  <TableCell className="font-mono text-xs">{e.reference_no}</TableCell>
                  <TableCell><span className={`text-xs px-2 py-0.5 rounded ${e.kind === "invoice" ? "bg-rose-50 text-rose-700" : "bg-emerald-50 text-emerald-700"}`}>{e.kind}</span></TableCell>
                  <TableCell className={`text-right font-semibold ${e.kind === "invoice" ? "text-rose-700" : "text-emerald-700"}`}>{e.kind === "invoice" ? "+" : "-"}{inr(e.amount)}</TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
        {data.entries.length === 0 && <div className="p-8 text-center text-sm text-slate-500">No entries yet</div>}
      </Card>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent>
          <DialogHeader><DialogTitle>Record Payment from Distributor</DialogTitle></DialogHeader>
          <div className="space-y-3">
            <div><Label>Distributor *</Label>
              <Select value={form.distributor_id} onValueChange={v => setForm({ ...form, distributor_id: v })}>
                <SelectTrigger data-testid="pay-dist"><SelectValue placeholder="Select" /></SelectTrigger>
                <SelectContent>{dists.map(d => <SelectItem key={d.id} value={d.id}>{d.name}</SelectItem>)}</SelectContent>
              </Select>
            </div>
            <div><Label>Amount (₹) *</Label><Input type="number" value={form.amount} onChange={e => setForm({ ...form, amount: e.target.value })} data-testid="pay-amt" /></div>
            <div><Label>Method</Label>
              <Select value={form.method} onValueChange={v => setForm({ ...form, method: v })}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="bank_transfer">Bank Transfer</SelectItem>
                  <SelectItem value="upi">UPI</SelectItem>
                  <SelectItem value="cash">Cash</SelectItem>
                  <SelectItem value="cheque">Cheque</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div><Label>Note</Label><Input value={form.description} onChange={e => setForm({ ...form, description: e.target.value })} /></div>
          </div>
          <DialogFooter><Button onClick={save} className="bg-gradient-to-r from-[#c9a227] to-[#a67c00] hover:from-[#b8931f] hover:to-[#8a6600] text-white" data-testid="save-payment-btn">Save</Button></DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}


// ============================================================================
// Excel Import / Export for Products (small toolbar buttons)
// ============================================================================
import { FileDown, FileUp } from "lucide-react";
export function ExcelButtons({ onImported }) {
  const inputRef = React.useRef(null);
  const [busy, setBusy] = useState(false);
  const doExport = async () => {
    setBusy(true);
    try { await dms.exportProducts(); toast.success("Products exported"); }
    catch (e) { toast.error(e?.response?.data?.detail || "Export failed"); }
    finally { setBusy(false); }
  };
  const doImport = async (e) => {
    const f = e.target.files?.[0];
    if (!f) return;
    setBusy(true);
    try {
      const r = await dms.importProducts(f);
      toast.success(`Imported: +${r.created} created, ${r.updated} updated, ${r.skipped} skipped`);
      if (r.errors?.length) toast.warning(`Some rows skipped:\n${r.errors.slice(0, 3).join("\n")}`);
      onImported?.();
    } catch (err) { toast.error(err?.response?.data?.detail || "Import failed"); }
    finally { setBusy(false); e.target.value = ""; }
  };
  return (
    <>
      <input ref={inputRef} type="file" accept=".xlsx" className="hidden" onChange={doImport} data-testid="import-file-input" />
      <Button variant="outline" onClick={doExport} disabled={busy} data-testid="export-products-btn"><FileDown size={14} className="mr-1" /> Export</Button>
      <Button variant="outline" onClick={() => inputRef.current?.click()} disabled={busy} data-testid="import-products-btn"><FileUp size={14} className="mr-1" /> Import</Button>
    </>
  );
}

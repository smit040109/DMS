import React, { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { dms, inr, niceDate, statusPill } from "./api";
import { PageHeader, EmptyState } from "./OwnerPages";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Card } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { toast } from "sonner";
import { ShoppingCart, Package, Warehouse, TrendingUp, ScrollText, CheckCircle2, ChevronRight, Plus, Minus, Receipt, ClipboardList, Truck, Paperclip } from "lucide-react";

// ============================================================================
// Distributor Dashboard
// ============================================================================
export function DistributorDashboardPage() {
  const [kpis, setKpis] = useState(null);
  const [recent, setRecent] = useState([]);
  const nav = useNavigate();
  useEffect(() => {
    dms.distributorDashboard().then(d => setKpis(d.kpis)).catch(() => {});
    dms.listOrders().then(d => setRecent((d.data || []).slice(0, 5))).catch(() => {});
  }, []);
  const cards = [
    { label: "Current Stock",            value: kpis ? `${kpis.stock_boxes} boxes` : "—",  icon: Warehouse,    color: "teal" },
    { label: "Stock Value",              value: kpis ? inr(kpis.stock_value) : "—",       icon: Package,      color: "indigo" },
    { label: "Payable to Owner",         value: kpis ? inr(kpis.payable_to_owner) : "—",  icon: ScrollText,   color: "rose" },
    { label: "Pending Primary Orders",   value: kpis?.pending_primary_orders ?? "—",       icon: ShoppingCart, color: "amber" },
    { label: "Ready to Receive",         value: kpis?.ready_to_receive ?? "—",             icon: Truck,        color: "blue" },
    { label: "Sales MTD",                value: kpis ? inr(kpis.revenue_mtd) : "—",       icon: TrendingUp,   color: "emerald" },
  ];
  const colorMap = {
    teal: "bg-[#faf6e6] text-[#a67c00]", indigo: "bg-indigo-50 text-indigo-700",
    amber: "bg-amber-50 text-amber-700", blue: "bg-blue-50 text-blue-700",
    emerald: "bg-emerald-50 text-emerald-700", rose: "bg-rose-50 text-rose-700",
  };
  return (
    <div>
      <PageHeader title="Distributor Dashboard" subtitle="Your business at a glance"
        action={<Button onClick={() => nav("/dms/distributor/browse")} className="bg-gradient-to-r from-[#c9a227] to-[#a67c00] hover:from-[#b8931f] hover:to-[#8a6600] text-white" data-testid="place-order-cta"><ShoppingCart size={16} className="mr-1" /> Place New Order</Button>}
      />
      <div className="grid grid-cols-2 md:grid-cols-3 gap-3 mb-6">
        {cards.map(c => (
          <Card key={c.label} className="p-4">
            <div className={`h-9 w-9 rounded-lg flex items-center justify-center ${colorMap[c.color]}`}><c.icon size={18} /></div>
            <div className="mt-3 text-xs text-slate-500 uppercase tracking-wider">{c.label}</div>
            <div className="mt-1 text-xl font-bold text-slate-900">{c.value}</div>
          </Card>
        ))}
      </div>
      <div className="flex items-center justify-between mb-3">
        <h3 className="font-semibold text-slate-900">Recent Orders</h3>
        <button onClick={() => nav("/dms/distributor/my-orders")} className="text-sm text-[#a67c00] hover:underline">View all →</button>
      </div>
      <Card>
        {recent.length === 0 ? (
          <div className="p-6 text-center text-sm text-slate-500">No orders yet</div>
        ) : (
          <Table>
            <TableHeader><TableRow><TableHead>Order #</TableHead><TableHead>Items</TableHead><TableHead>Total</TableHead><TableHead>Fulfillment</TableHead><TableHead>Status</TableHead><TableHead>Placed</TableHead></TableRow></TableHeader>
            <TableBody>
              {recent.map(o => (
                <TableRow key={o.id} className="cursor-pointer hover:bg-slate-50" onClick={() => nav(`/dms/distributor/my-orders/${o.id}`)}>
                  <TableCell className="font-mono text-sm">{o.order_no}</TableCell>
                  <TableCell>{o.items.length}</TableCell>
                  <TableCell className="font-medium">{inr(o.total)}</TableCell>
                  <TableCell><div className="flex items-center gap-2"><div className="w-16 h-1.5 bg-slate-100 rounded overflow-hidden"><div className="h-full bg-[#faf6e6]0" style={{ width: `${o.fulfillment_pct}%` }} /></div><span className="text-xs">{o.fulfillment_pct}%</span></div></TableCell>
                  <TableCell><span className={`text-xs px-2 py-1 rounded-full border ${statusPill(o.status)}`}>{o.status.replace(/_/g, " ")}</span></TableCell>
                  <TableCell className="text-xs text-slate-500">{niceDate(o.created_at)}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </Card>
    </div>
  );
}

// ============================================================================
// Distributor — Browse & Place Order
// ============================================================================
export function DistributorBrowsePage() {
  const [products, setProducts] = useState([]);
  const [cart, setCart] = useState({});  // { product_id: qty }
  const [notes, setNotes] = useState("");
  const [busy, setBusy] = useState(false);
  const [openCategory, setOpenCategory] = useState(null);
  const nav = useNavigate();

  useEffect(() => { dms.browseProducts().then(d => setProducts(d.data)).catch(() => {}); }, []);

  const setQty = (pid, delta) => setCart(prev => ({ ...prev, [pid]: Math.max(0, (prev[pid] || 0) + delta) }));
  const setQtyDirect = (pid, val) => setCart(prev => ({ ...prev, [pid]: Math.max(0, Number(val) || 0) }));

  // All price maths use unit_price (new price). previous_price is display-only.
  const subtotal = products.reduce((s, p) => s + (cart[p.id] || 0) * p.unit_price, 0);
  const gstTotal = products.reduce((s, p) => s + (cart[p.id] || 0) * p.unit_price * (p.gst_pct / 100), 0);
  const total = subtotal + gstTotal;
  const itemsCount = Object.values(cart).filter(v => v > 0).length;

  const place = async () => {
    const items = Object.entries(cart).filter(([, q]) => q > 0).map(([product_id, qty_boxes]) => ({ product_id, qty_boxes }));
    if (items.length === 0) return toast.error("Add at least one product");
    setBusy(true);
    try {
      const o = await dms.placeOrder({ items, notes });
      toast.success(`Order ${o.order_no} placed!`);
      nav(`/dms/distributor/my-orders/${o.id}`);
    } catch (e) { toast.error(e.response?.data?.detail || "Failed"); }
    setBusy(false);
  };

  // Group by category with counts & totals
  const grouped = {};
  products.forEach(p => { (grouped[p.category_name || "Uncategorised"] ||= []).push(p); });
  const categoryList = Object.entries(grouped).map(([name, prods]) => {
    const inCart = prods.reduce((n, p) => n + (cart[p.id] > 0 ? 1 : 0), 0);
    return { name, count: prods.length, inCart };
  });

  return (
    <div className="pb-32">
      <PageHeader
        title={openCategory ? openCategory : "Browse & Order"}
        subtitle={openCategory ? "Tap + / − to set quantity per product" : "Pick a category to see products"}
        back={openCategory ? undefined : undefined}
        action={openCategory && (
          <Button variant="outline" onClick={() => setOpenCategory(null)} data-testid="back-to-cats"><ChevronRight className="rotate-180 mr-1" size={16} /> All Categories</Button>
        )}
      />

      {/* STEP 1 — category grid */}
      {!openCategory && (
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
          {categoryList.length === 0 && <EmptyState icon={Package} title="No products available" description="Owner hasn't given you visibility yet." />}
          {categoryList.map(c => (
            <button
              key={c.name}
              onClick={() => setOpenCategory(c.name)}
              className="text-left bg-white border border-slate-200 hover:border-[#c9a227] hover:shadow-md transition rounded-2xl p-5 relative"
              data-testid={`cat-tile-${c.name}`}
            >
              <div className="h-10 w-10 rounded-xl bg-[#faf6e6] text-[#a67c00] flex items-center justify-center mb-3"><Package size={20} /></div>
              <div className="font-semibold text-slate-900">{c.name}</div>
              <div className="text-xs text-slate-500 mt-0.5">{c.count} product{c.count !== 1 ? "s" : ""}</div>
              {c.inCart > 0 && (
                <span className="absolute top-3 right-3 bg-[#c9a227] text-white text-[10px] font-bold rounded-full px-2 py-0.5">{c.inCart} in cart</span>
              )}
              <div className="mt-4 text-[#a67c00] text-xs font-medium flex items-center">Open <ChevronRight size={12} className="ml-0.5" /></div>
            </button>
          ))}
        </div>
      )}

      {/* STEP 2 — product list inside category */}
      {openCategory && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {(grouped[openCategory] || []).map(p => {
            const q = cart[p.id] || 0;
            const priceChanged = p.previous_price && p.previous_price !== p.unit_price;
            return (
              <Card key={p.id} className="p-4 flex flex-col" data-testid={`product-card-${p.id}`}>
                <div className="flex-1">
                  <div className="flex items-start justify-between gap-2 mb-1">
                    <div className="font-semibold text-slate-900 leading-tight">{p.name}</div>
                    {priceChanged && <span className="text-[10px] uppercase font-bold bg-amber-100 text-amber-800 px-1.5 py-0.5 rounded shrink-0">Price ↑</span>}
                  </div>
                  <div className="text-xs font-mono text-slate-500 mb-2">{p.sku_code} • {p.box_qty} bottles/box</div>
                  <div className="flex items-baseline gap-2 mt-2">
                    <span className="text-lg font-bold text-[#a67c00]">{inr(p.unit_price)}</span>
                    {priceChanged && (
                      <>
                        <span className="text-xs text-slate-500 line-through">{inr(p.previous_price)}</span>
                        <span className="text-[10px] text-amber-700 font-semibold">(old)</span>
                      </>
                    )}
                    <span className="text-xs text-slate-500">/ box (NEW)</span>
                  </div>
                  <div className="text-xs text-slate-500 mt-1">+{p.gst_pct}% GST • Owner stock: {p.owner_stock_boxes} boxes</div>
                </div>
                <div className="mt-3 flex items-center justify-between">
                  <div className="flex items-center gap-1">
                    <button onClick={() => setQty(p.id, -1)} className="h-9 w-9 rounded-lg border border-slate-200 hover:bg-slate-50 flex items-center justify-center" data-testid={`minus-${p.id}`}><Minus size={16} /></button>
                    <input type="number" min={0} value={q} onChange={e => setQtyDirect(p.id, e.target.value)} className="w-14 h-9 text-center border border-slate-200 rounded-lg text-sm font-semibold" data-testid={`qty-input-${p.id}`} />
                    <button onClick={() => setQty(p.id, 1)} className="h-9 w-9 rounded-lg border border-slate-200 hover:bg-slate-50 flex items-center justify-center bg-[#faf6e6] text-[#a67c00]" data-testid={`plus-${p.id}`}><Plus size={16} /></button>
                  </div>
                  <div className="text-sm font-semibold text-slate-900">{q > 0 ? inr(q * p.unit_price) : ""}</div>
                </div>
              </Card>
            );
          })}
        </div>
      )}

      {/* Sticky cart footer */}
      <div className="fixed bottom-0 left-0 lg:left-60 right-0 bg-white border-t border-slate-200 shadow-lg z-40">
        <div className="p-4 flex items-center gap-4">
          <div className="flex-1">
            <div className="text-xs text-slate-500">{itemsCount} items • Subtotal {inr(subtotal)} + GST {inr(gstTotal)} <span className="ml-1 text-[10px] uppercase font-semibold text-[#a67c00]">using NEW price</span></div>
            <div className="text-xl font-bold text-slate-900">{inr(total)}</div>
          </div>
          <div className="hidden md:block flex-1 max-w-sm"><Input placeholder="Notes for owner (optional)" value={notes} onChange={e => setNotes(e.target.value)} /></div>
          <Button disabled={itemsCount === 0 || busy} onClick={place} className="bg-gradient-to-r from-[#c9a227] to-[#a67c00] hover:from-[#b8931f] hover:to-[#8a6600] text-white h-11 px-6" data-testid="place-order-btn">
            <ShoppingCart size={16} className="mr-2" /> Place Order
          </Button>
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// Distributor — My Primary Orders + Detail
// ============================================================================
export function DistributorOrdersPage() {
  const [list, setList] = useState([]);
  const nav = useNavigate();
  useEffect(() => { dms.listOrders().then(d => setList(d.data)); }, []);
  return (
    <div>
      <PageHeader title="My Primary Orders" subtitle="Orders you've placed with the owner" />
      <Card>
        <Table>
          <TableHeader><TableRow><TableHead>Order #</TableHead><TableHead>Items</TableHead><TableHead>Total</TableHead><TableHead>Fulfillment</TableHead><TableHead>Status</TableHead><TableHead>Placed</TableHead></TableRow></TableHeader>
          <TableBody>
            {list.map(o => (
              <TableRow key={o.id} className="cursor-pointer hover:bg-slate-50" onClick={() => nav(`/dms/distributor/my-orders/${o.id}`)} data-testid={`my-ord-${o.id}`}>
                <TableCell className="font-mono text-sm">{o.order_no}</TableCell>
                <TableCell>{o.items.length}</TableCell>
                <TableCell className="font-medium">{inr(o.total)}</TableCell>
                <TableCell><div className="flex items-center gap-2 min-w-[100px]"><div className="w-16 h-1.5 bg-slate-100 rounded overflow-hidden"><div className="h-full bg-[#faf6e6]0" style={{ width: `${o.fulfillment_pct}%` }} /></div><span className="text-xs">{o.fulfillment_pct}%</span></div></TableCell>
                <TableCell><span className={`text-xs px-2 py-1 rounded-full border ${statusPill(o.status)}`}>{o.status.replace(/_/g, " ")}</span></TableCell>
                <TableCell className="text-xs text-slate-500">{niceDate(o.created_at)}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
        {list.length === 0 && <div className="p-8 text-center text-sm text-slate-500">No orders yet</div>}
      </Card>
    </div>
  );
}

export function DistributorOrderDetailPage() {
  const { id } = useParams();
  const [order, setOrder] = useState(null);
  const [busy, setBusy] = useState(false);
  const load = () => dms.getOrder(id).then(setOrder);
  useEffect(() => { load(); }, [id]);

  const receive = async () => {
    if (!window.confirm("Confirm you have physically received this shipment?")) return;
    setBusy(true);
    try { await dms.markReceived(id); toast.success("Marked as Received"); await load(); }
    catch (e) { toast.error(e.response?.data?.detail || "Failed"); }
    setBusy(false);
  };

  if (!order) return <div className="p-8 text-center text-slate-500">Loading…</div>;

  return (
    <div>
      <PageHeader
        title={order.order_no}
        subtitle={`Placed ${niceDate(order.created_at)}`}
        back="/dms/distributor/my-orders"
        action={<div className="flex gap-2">
          {order.ebill && <Button variant="outline" onClick={() => window.open(`/dms/print/ebill/${order.ebill.id}`, "_blank")} data-testid="dist-print-ebill"><span className="mr-1">🖨</span> Print e-Bill</Button>}
          {order.status === "ready_to_go" && <Button onClick={receive} disabled={busy} className="bg-emerald-700 hover:bg-emerald-800" data-testid="mark-received-btn"><CheckCircle2 size={16} className="mr-1" /> Mark Received</Button>}
        </div>}
      />
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-4">
        <Card className="p-4"><div className="text-xs text-slate-500 uppercase tracking-wider">Status</div><div className="mt-1"><span className={`text-sm px-2.5 py-1 rounded-full border ${statusPill(order.status)}`}>{order.status.replace(/_/g, " ")}</span></div></Card>
        <Card className="p-4"><div className="text-xs text-slate-500 uppercase tracking-wider">Fulfillment</div><div className="mt-1 flex items-center gap-3"><div className="flex-1 h-2 bg-slate-100 rounded overflow-hidden"><div className="h-full bg-[#faf6e6]0 transition-all" style={{ width: `${order.fulfillment_pct}%` }} /></div><span className="font-bold">{order.fulfillment_pct}%</span></div></Card>
        <Card className="p-4"><div className="text-xs text-slate-500 uppercase tracking-wider">Total</div><div className="mt-1 font-bold text-lg">{inr(order.total)}</div></Card>
      </div>
      <Card className="mb-4">
        <div className="p-4 border-b border-slate-100 font-semibold">Items</div>
        <Table>
          <TableHeader><TableRow><TableHead>Product</TableHead><TableHead>Price</TableHead><TableHead>Ordered</TableHead><TableHead>Being Delivered</TableHead><TableHead>Total</TableHead></TableRow></TableHeader>
          <TableBody>
            {order.items.map(it => (
              <TableRow key={it.product_id}>
                <TableCell><div className="font-medium">{it.product_name}</div><div className="text-xs font-mono text-slate-500">{it.sku_code}</div></TableCell>
                <TableCell>
                  <div>{inr(it.unit_price)}</div>
                  {it.previous_price && it.previous_price !== it.unit_price && (
                    <div className="text-xs text-slate-500 line-through">was {inr(it.previous_price)}</div>
                  )}
                </TableCell>
                <TableCell>{it.qty_boxes_ordered} boxes</TableCell>
                <TableCell><span className="font-semibold">{it.qty_boxes_fulfilled}</span> {it.qty_boxes_fulfilled < it.qty_boxes_ordered && <span className="text-xs text-amber-700 ml-1">(partial)</span>}</TableCell>
                <TableCell className="font-medium">{inr(it.line_total)}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Card>
      {order.ebill && (
        <Card className="mb-4 p-4">
          <div className="flex items-center gap-2 mb-2"><Receipt size={18} className="text-[#a67c00]" /><div className="font-semibold">e-Bill Generated</div></div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
            <div><div className="text-slate-500">Bill #</div><div className="font-mono">{order.ebill.ebill_no}</div></div>
            <div><div className="text-slate-500">Subtotal</div><div>{inr(order.ebill.subtotal)}</div></div>
            <div><div className="text-slate-500">GST</div><div>{inr(order.ebill.gst_total)}</div></div>
            <div><div className="text-slate-500">Total</div><div className="font-bold">{inr(order.ebill.total)}</div></div>
          </div>
          {(order.attachments || []).length > 0 && (
            <div className="mt-3 pt-3 border-t border-slate-100">
              <div className="text-xs text-slate-500 mb-2">Attachments:</div>
              {order.attachments.map(a => (
                <a key={a.id} href={a.url} target="_blank" rel="noreferrer" className="flex items-center gap-2 text-sm text-[#a67c00] hover:underline"><Paperclip size={14} /> {a.name}</a>
              ))}
            </div>
          )}
        </Card>
      )}
    </div>
  );
}

// ============================================================================
// Distributor — My Stock (received inventory)
// ============================================================================
export function DistributorStockPage() {
  const [stock, setStock] = useState({ kpis: null });
  useEffect(() => { dms.distributorDashboard().then(setStock); }, []);
  // Simpler: fetch via a dedicated call — but we can just render orders received.
  // For iteration 1 we'll show distributor's inventory pulled from dashboard kpi.
  return (
    <div>
      <PageHeader title="My Stock" subtitle="Received inventory" />
      <Card className="p-6 text-center">
        <Warehouse size={32} className="mx-auto text-slate-400 mb-2" />
        <div className="text-lg font-semibold text-slate-900">{stock.kpis?.stock_boxes || 0} boxes</div>
        <div className="text-sm text-slate-500">Total stock value {inr(stock.kpis?.stock_value || 0)}</div>
        <div className="mt-4 text-xs text-slate-500">Item-level view will appear here once Secondary Sales (Iteration 2) is enabled.</div>
      </Card>
    </div>
  );
}

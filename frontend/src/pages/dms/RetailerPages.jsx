import React, { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { dms, inr, niceDate, statusPill } from "./api";
import { PageHeader, EmptyState } from "./OwnerPages";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { toast } from "sonner";
import { ShoppingCart, Package, TrendingUp, Plus, Minus, Truck, Receipt, Printer, ChevronRight } from "lucide-react";

export function RetailerDashboardPage() {
  const [kpis, setKpis] = useState(null);
  const [orders, setOrders] = useState([]);
  const nav = useNavigate();
  useEffect(() => {
    dms.retailerDashboard().then(d => setKpis(d.kpis)).catch(() => {});
    dms.listSecondaryOrders().then(d => setOrders((d.data || []).slice(0, 6))).catch(() => {});
  }, []);
  const cards = [
    { label: "Total Orders", value: kpis?.total_orders ?? "—", icon: ShoppingCart, color: "teal" },
    { label: "In Transit", value: kpis?.in_transit ?? "—", icon: Truck, color: "blue" },
    { label: "Outstanding", value: kpis ? inr(kpis.outstanding) : "—", icon: TrendingUp, color: "rose" },
    { label: "Pending Items", value: kpis?.pending_items ?? "—", icon: Package, color: "amber" },
  ];
  const colorMap = { teal: "bg-teal-50 text-teal-700", blue: "bg-blue-50 text-blue-700", rose: "bg-rose-50 text-rose-700", amber: "bg-amber-50 text-amber-700" };
  return (
    <div>
      <PageHeader title="Retailer Dashboard" subtitle="Your orders & outstanding"
        action={<Button onClick={() => nav("/dms/retailer/browse")} className="bg-teal-700 hover:bg-teal-800" data-testid="place-order-cta"><ShoppingCart size={16} className="mr-1" /> Place New Order</Button>} />
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
        {cards.map(c => (
          <Card key={c.label} className="p-4">
            <div className={`h-9 w-9 rounded-lg flex items-center justify-center ${colorMap[c.color]}`}><c.icon size={18} /></div>
            <div className="mt-3 text-xs text-slate-500 uppercase tracking-wider">{c.label}</div>
            <div className="mt-1 text-xl font-bold text-slate-900">{c.value}</div>
          </Card>
        ))}
      </div>
      <h3 className="font-semibold text-slate-900 mb-3">Recent Orders</h3>
      <Card>
        {orders.length === 0 ? <div className="p-6 text-center text-sm text-slate-500">No orders yet</div> : (
          <Table><TableHeader><TableRow><TableHead>Order #</TableHead><TableHead>Items</TableHead><TableHead>Total</TableHead><TableHead>Status</TableHead><TableHead>Placed</TableHead></TableRow></TableHeader><TableBody>
            {orders.map(o => (
              <TableRow key={o.id} className="cursor-pointer hover:bg-slate-50" onClick={() => nav(`/dms/retailer/my-orders/${o.id}`)}>
                <TableCell className="font-mono text-sm">{o.order_no}</TableCell>
                <TableCell>{o.items.length}</TableCell>
                <TableCell className="font-medium">{inr(o.total)}</TableCell>
                <TableCell><span className={`text-xs px-2 py-1 rounded-full border ${statusPill(o.status)}`}>{o.status.replace(/_/g, " ")}</span></TableCell>
                <TableCell className="text-xs text-slate-500">{niceDate(o.created_at)}</TableCell>
              </TableRow>
            ))}
          </TableBody></Table>
        )}
      </Card>
    </div>
  );
}

export function RetailerBrowsePage() {
  const [data, setData] = useState({ data: [], mode: "box", pending: [] });
  const [cart, setCart] = useState({}); // { pid: { boxes, pcs } }
  const [includePending, setIncludePending] = useState(true);
  const [busy, setBusy] = useState(false);
  const [openCategory, setOpenCategory] = useState(null);
  const nav = useNavigate();

  useEffect(() => { dms.retailerBrowse().then(setData); }, []);

  const setQty = (pid, field, delta) => setCart(prev => {
    const cur = prev[pid] || { boxes: 0, pcs: 0 };
    return { ...prev, [pid]: { ...cur, [field]: Math.max(0, (cur[field] || 0) + delta) } };
  });

  const items = Object.entries(cart).filter(([, q]) => (q.boxes || 0) + (q.pcs || 0) > 0);
  const subtotal = items.reduce((s, [pid, q]) => {
    const p = data.data.find(x => x.id === pid);
    if (!p) return s;
    const box_price = p.selling_price;
    const pcs_price = box_price / (p.box_qty || 1);
    return s + (q.boxes || 0) * box_price + (q.pcs || 0) * pcs_price;
  }, 0);
  const gst = items.reduce((s, [pid, q]) => {
    const p = data.data.find(x => x.id === pid);
    if (!p) return s;
    const box_price = p.selling_price; const pcs_price = box_price / (p.box_qty || 1);
    return s + ((q.boxes || 0) * box_price + (q.pcs || 0) * pcs_price) * (p.gst_pct / 100);
  }, 0);
  const total = subtotal + gst;

  const place = async () => {
    if (items.length === 0 && !(includePending && data.pending.length > 0)) return toast.error("Add items or include pending");
    setBusy(true);
    try {
      const body = {
        items: items.map(([product_id, q]) => ({ product_id, qty_boxes: q.boxes || 0, qty_pcs: q.pcs || 0 })),
        include_pending: includePending,
      };
      const o = await dms.placeSecondaryOrder(body);
      toast.success(`Order ${o.order_no} placed!`);
      nav(`/dms/retailer/my-orders/${o.id}`);
    } catch (e) { toast.error(e.response?.data?.detail || "Failed"); }
    setBusy(false);
  };

  const grouped = {};
  data.data.forEach(p => { (grouped[p.category_name || "Uncategorised"] ||= []).push(p); });
  const cats = Object.entries(grouped).map(([name, prods]) => {
    const inCart = prods.reduce((n, p) => n + ((cart[p.id]?.boxes || 0) + (cart[p.id]?.pcs || 0) > 0 ? 1 : 0), 0);
    return { name, count: prods.length, inCart };
  });

  return (
    <div className="pb-32">
      <PageHeader
        title={openCategory ? openCategory : "Browse & Order"}
        subtitle={openCategory ? "Tap + / − to set boxes (and pcs)" : `Selling mode: ${data.mode === "box_pcs" ? "Box + PCS" : "Box only"} · Pick a category`}
        action={openCategory && (<Button variant="outline" onClick={() => setOpenCategory(null)}><ChevronRight className="rotate-180 mr-1" size={16} /> All Categories</Button>)}
      />

      {data.pending.length > 0 && !openCategory && (
        <Card className="p-4 mb-4 bg-amber-50 border-amber-200">
          <div className="font-semibold text-amber-900 mb-2">Previous Pending Items</div>
          <div className="text-sm text-amber-800 space-y-1">
            {data.pending.map((pd, i) => (
              <div key={i}>• <b>{pd.product_name}</b> — {pd.pending_qty_boxes} boxes {pd.pending_qty_pcs > 0 && `+ ${pd.pending_qty_pcs} pcs`}</div>
            ))}
          </div>
          <label className="mt-3 flex items-center gap-2 text-sm text-amber-900 cursor-pointer">
            <input type="checkbox" checked={includePending} onChange={e => setIncludePending(e.target.checked)} data-testid="include-pending" />
            Deliver these along with my new order
          </label>
        </Card>
      )}

      {/* STEP 1 — categories */}
      {!openCategory && (
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
          {cats.length === 0 && <EmptyState icon={Package} title="No products available" description="Your distributor hasn't given you any visibility yet." />}
          {cats.map(c => (
            <button
              key={c.name}
              onClick={() => setOpenCategory(c.name)}
              className="text-left bg-white border border-slate-200 hover:border-teal-400 hover:shadow-md transition rounded-2xl p-5 relative"
              data-testid={`ret-cat-${c.name}`}
            >
              <div className="h-10 w-10 rounded-xl bg-teal-50 text-teal-700 flex items-center justify-center mb-3"><Package size={20} /></div>
              <div className="font-semibold text-slate-900">{c.name}</div>
              <div className="text-xs text-slate-500 mt-0.5">{c.count} product{c.count !== 1 ? "s" : ""}</div>
              {c.inCart > 0 && (<span className="absolute top-3 right-3 bg-teal-700 text-white text-[10px] font-bold rounded-full px-2 py-0.5">{c.inCart} in cart</span>)}
              <div className="mt-4 text-teal-700 text-xs font-medium flex items-center">Open <ChevronRight size={12} className="ml-0.5" /></div>
            </button>
          ))}
        </div>
      )}

      {/* STEP 2 — products in category */}
      {openCategory && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {(grouped[openCategory] || []).map(p => {
            const q = cart[p.id] || { boxes: 0, pcs: 0 };
            const priceChanged = p.previous_selling_price && p.previous_selling_price !== p.selling_price;
            return (
              <Card key={p.id} className="p-4" data-testid={`ret-product-${p.id}`}>
                <div className="flex items-start justify-between gap-2">
                  <div className="font-semibold text-slate-900">{p.name}</div>
                  {priceChanged && <span className="text-[10px] uppercase font-bold bg-amber-100 text-amber-800 px-1.5 py-0.5 rounded">Price ↑</span>}
                </div>
                <div className="text-xs font-mono text-slate-500">{p.sku_code} • {p.box_qty} bottles/box</div>
                <div className="mt-2 flex items-baseline gap-2">
                  <span className="text-lg font-bold text-teal-700">{inr(p.selling_price)}</span>
                  {priceChanged && (
                    <><span className="text-xs text-slate-500 line-through">{inr(p.previous_selling_price)}</span>
                      <span className="text-[10px] text-amber-700 font-semibold">(old)</span></>
                  )}
                  <span className="text-xs text-slate-500">/ box (NEW)</span>
                </div>
                <div className="text-xs text-slate-500 mt-1">+{p.gst_pct}% GST • Distributor stock: {p.distributor_stock_boxes} boxes</div>
                <div className="mt-3 space-y-2">
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-xs text-slate-600 w-12">Boxes</span>
                    <button onClick={() => setQty(p.id, "boxes", -1)} className="h-9 w-9 rounded-lg border border-slate-200 hover:bg-slate-50 flex items-center justify-center" data-testid={`ret-minus-box-${p.id}`}><Minus size={16} /></button>
                    <div className="w-12 text-center font-semibold text-lg">{q.boxes || 0}</div>
                    <button onClick={() => setQty(p.id, "boxes", 1)} className="h-9 w-9 rounded-lg border border-slate-200 bg-teal-50 text-teal-700 hover:bg-teal-100 flex items-center justify-center" data-testid={`ret-plus-box-${p.id}`}><Plus size={16} /></button>
                  </div>
                  {data.mode === "box_pcs" && (
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-xs text-slate-600 w-12">PCS</span>
                      <button onClick={() => setQty(p.id, "pcs", -1)} className="h-9 w-9 rounded-lg border border-slate-200 hover:bg-slate-50 flex items-center justify-center"><Minus size={16} /></button>
                      <div className="w-12 text-center font-semibold text-lg">{q.pcs || 0}</div>
                      <button onClick={() => setQty(p.id, "pcs", 1)} className="h-9 w-9 rounded-lg border border-slate-200 bg-teal-50 text-teal-700 hover:bg-teal-100 flex items-center justify-center"><Plus size={16} /></button>
                    </div>
                  )}
                </div>
              </Card>
            );
          })}
        </div>
      )}

      <div className="fixed bottom-0 left-0 lg:left-60 right-0 bg-white border-t border-slate-200 shadow-lg z-40">
        <div className="p-4 flex items-center gap-4">
          <div className="flex-1"><div className="text-xs text-slate-500">{items.length} items • Sub {inr(subtotal)} + GST {inr(gst)} <span className="ml-1 text-[10px] uppercase font-semibold text-teal-700">using NEW price</span></div><div className="text-xl font-bold text-slate-900">{inr(total)}</div></div>
          <Button disabled={busy || (items.length === 0 && !(includePending && data.pending.length > 0))} onClick={place} className="bg-teal-700 hover:bg-teal-800 h-11 px-6" data-testid="ret-place-order"><ShoppingCart size={16} className="mr-2" /> Place Order</Button>
        </div>
      </div>
    </div>
  );
}

export function RetailerOrdersPage() {
  const [list, setList] = useState([]);
  const nav = useNavigate();
  useEffect(() => { dms.listSecondaryOrders().then(d => setList(d.data)); }, []);
  return (
    <div>
      <PageHeader title="My Orders" subtitle="Orders you placed with your distributor" />
      <Card>
        <Table>
          <TableHeader><TableRow><TableHead>Order #</TableHead><TableHead>Items</TableHead><TableHead>Total</TableHead><TableHead>Status</TableHead><TableHead>Placed</TableHead></TableRow></TableHeader>
          <TableBody>
            {list.map(o => (
              <TableRow key={o.id} className="cursor-pointer hover:bg-slate-50" onClick={() => nav(`/dms/retailer/my-orders/${o.id}`)}>
                <TableCell className="font-mono text-sm">{o.order_no}</TableCell>
                <TableCell>{o.items.length}</TableCell>
                <TableCell className="font-medium">{inr(o.total)}</TableCell>
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

export function RetailerOrderDetailPage() {
  const { id } = useParams();
  const [order, setOrder] = useState(null);
  useEffect(() => { dms.getSecondaryOrder(id).then(setOrder); }, [id]);
  if (!order) return <div className="p-8 text-center text-slate-500">Loading…</div>;
  return (
    <div>
      <PageHeader title={order.order_no} subtitle={`Placed ${niceDate(order.created_at)}`} back="/dms/retailer/my-orders"
        action={order.bill_id && <Button variant="outline" onClick={() => window.open(`/dms/print/retailer-bill/${order.bill_id}`, "_blank")}><Printer size={14} className="mr-1" /> Print Bill</Button>} />
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-4">
        <Card className="p-4"><div className="text-xs text-slate-500 uppercase tracking-wider">Status</div><div className="mt-1"><span className={`text-sm px-2.5 py-1 rounded-full border ${statusPill(order.status)}`}>{order.status.replace(/_/g, " ")}</span></div></Card>
        <Card className="p-4"><div className="text-xs text-slate-500 uppercase tracking-wider">Fulfillment</div><div className="mt-1 flex items-center gap-2"><div className="flex-1 h-2 bg-slate-100 rounded overflow-hidden"><div className="h-full bg-teal-500" style={{ width: `${order.fulfillment_pct}%` }} /></div><span className="font-bold">{order.fulfillment_pct}%</span></div></Card>
        <Card className="p-4"><div className="text-xs text-slate-500 uppercase tracking-wider">Total</div><div className="mt-1 font-bold text-lg">{inr(order.total)}</div></Card>
      </div>
      <Card>
        <div className="p-4 border-b border-slate-100 font-semibold">Line Items</div>
        <Table><TableHeader><TableRow><TableHead>Product</TableHead><TableHead>Ordered</TableHead><TableHead>Dispatched</TableHead><TableHead>Line Total</TableHead></TableRow></TableHeader>
          <TableBody>
            {order.items.map(it => (
              <TableRow key={it.product_id}>
                <TableCell><div className="font-medium">{it.product_name}</div>{it.carried_pending && <span className="text-[10px] uppercase bg-amber-100 text-amber-800 px-1.5 py-0.5 rounded">Carried from pending</span>}</TableCell>
                <TableCell>{it.qty_boxes_ordered} boxes {it.qty_pcs_ordered > 0 && `+ ${it.qty_pcs_ordered} pcs`}</TableCell>
                <TableCell>{it.qty_boxes_dispatched} boxes {it.qty_pcs_dispatched > 0 && `+ ${it.qty_pcs_dispatched} pcs`}</TableCell>
                <TableCell className="font-medium">{inr(it.line_total)}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Card>
    </div>
  );
}

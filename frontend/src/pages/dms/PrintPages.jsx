import React, { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { dms, inr, niceDate } from "./api";
import { Button } from "@/components/ui/button";
import { Printer, X } from "lucide-react";

function PrintFrame({ children, title }) {
  return (
    <div className="min-h-screen bg-slate-100 p-6 print:p-0 print:bg-white">
      <div className="max-w-3xl mx-auto">
        <div className="flex items-center justify-between mb-4 print:hidden">
          <div className="font-semibold">{title}</div>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" onClick={() => window.close()}><X size={14} className="mr-1" /> Close</Button>
            <Button onClick={() => window.print()} className="bg-gradient-to-r from-[#c9a227] to-[#a67c00] hover:from-[#b8931f] hover:to-[#8a6600] text-white" size="sm" data-testid="print-btn"><Printer size={14} className="mr-1" /> Print / Save PDF</Button>
          </div>
        </div>
        <div className="bg-white shadow-lg rounded-lg print:shadow-none print:rounded-none p-8 print:p-6">{children}</div>
      </div>
    </div>
  );
}

function Row({ label, value }) {
  return <div className="flex justify-between text-sm py-1"><span className="text-slate-500">{label}</span><span className="text-slate-900 font-medium text-right">{value}</span></div>;
}

// ─────────────────────────────────────────────────────────────────────────
// Vyapar-style Tax Invoice (shared by Primary e-Bill, Retailer bill, Direct sale)
// Renders from backend `invoice` object.
// ─────────────────────────────────────────────────────────────────────────
function PartyBlock({ title, party }) {
  if (!party) return null;
  return (
    <div>
      <div className="text-[10px] uppercase tracking-wider text-slate-500 mb-1 font-semibold">{title}</div>
      <div className="font-semibold text-slate-900">{party.name || "—"}</div>
      {party.address && <div className="text-xs text-slate-600 whitespace-pre-wrap">{party.address}</div>}
      {party.gstin && <div className="text-xs text-slate-600">GSTIN: <span className="font-mono">{party.gstin}</span></div>}
      {(party.state || party.state_code) && <div className="text-xs text-slate-600">State: {party.state}{party.state_code ? ` (${party.state_code})` : ""}</div>}
      {party.phone && <div className="text-xs text-slate-600">Ph: {party.phone}</div>}
    </div>
  );
}

export function VyaparInvoice({ inv }) {
  if (!inv) return null;
  const t = inv.totals || {};
  const seller = inv.seller || {};
  const transport = inv.transport || {};
  const hasTransport = transport && (transport.mode || transport.vehicle_no || transport.transporter || transport.lr_no);
  return (
    <div className="text-slate-900" data-testid="vyapar-invoice">
      {/* Header */}
      <div className="border-2 border-slate-800">
        <div className="flex items-stretch">
          <div className="flex-1 p-4 flex items-center gap-3">
            {seller.logo_url ? (
              <img src={seller.logo_url} alt="logo" className="h-14 w-14 object-contain" />
            ) : (
              <div className="h-14 w-14 rounded-full bg-gradient-to-br from-[#c9a227] to-[#8a6600] flex items-center justify-center text-white font-bold text-lg">GO</div>
            )}
            <div>
              <div className="text-xl font-extrabold tracking-tight">{seller.name}</div>
              {seller.address && <div className="text-xs text-slate-600 whitespace-pre-wrap">{seller.address}</div>}
              <div className="text-xs text-slate-600">
                {seller.phone && <span>Ph: {seller.phone} </span>}
                {seller.email && <span>· {seller.email}</span>}
              </div>
              {seller.gstin && <div className="text-xs font-semibold text-slate-700">GSTIN: <span className="font-mono">{seller.gstin}</span></div>}
            </div>
          </div>
          <div className="w-48 border-l-2 border-slate-800 p-4 flex flex-col items-center justify-center bg-slate-50">
            <div className="text-lg font-extrabold">{inv.doc_title || "TAX INVOICE"}</div>
            <div className="text-[10px] text-slate-500 mt-1">ORIGINAL FOR RECIPIENT</div>
          </div>
        </div>
        {/* Invoice meta */}
        <div className="grid grid-cols-2 border-t-2 border-slate-800">
          <div className="p-3 border-r-2 border-slate-800">
            <PartyBlock title="Bill To" party={inv.bill_to} />
          </div>
          <div className="p-3">
            <PartyBlock title="Ship To" party={inv.ship_to} />
          </div>
        </div>
        <div className="grid grid-cols-3 border-t-2 border-slate-800 text-xs">
          <div className="p-2 border-r border-slate-300"><span className="text-slate-500">Invoice No: </span><span className="font-semibold">{inv.doc_no}</span></div>
          <div className="p-2 border-r border-slate-300"><span className="text-slate-500">Date: </span><span className="font-semibold">{niceDate(inv.date)}</span></div>
          <div className="p-2"><span className="text-slate-500">Place of Supply: </span><span className="font-semibold">{(inv.bill_to && (inv.bill_to.state || inv.bill_to.state_code)) || "—"}</span></div>
        </div>
        {hasTransport && (
          <div className="grid grid-cols-4 border-t border-slate-300 text-xs">
            <div className="p-2 border-r border-slate-300"><span className="text-slate-500">Transport: </span>{transport.mode || "—"}</div>
            <div className="p-2 border-r border-slate-300"><span className="text-slate-500">Vehicle: </span>{transport.vehicle_no || "—"}</div>
            <div className="p-2 border-r border-slate-300"><span className="text-slate-500">Transporter: </span>{transport.transporter || "—"}</div>
            <div className="p-2"><span className="text-slate-500">LR No: </span>{transport.lr_no || "—"}</div>
          </div>
        )}
      </div>

      {/* Items */}
      <table className="w-full text-xs border-2 border-t-0 border-slate-800">
        <thead>
          <tr className="bg-slate-800 text-white text-left">
            <th className="p-2 w-8">#</th>
            <th className="p-2">Item</th>
            <th className="p-2">HSN/SAC</th>
            <th className="p-2 text-right">Qty</th>
            <th className="p-2 text-right">Rate</th>
            <th className="p-2 text-right">Taxable</th>
            <th className="p-2 text-right">GST</th>
            <th className="p-2 text-right">Amount</th>
          </tr>
        </thead>
        <tbody>
          {(inv.items || []).map((it, i) => (
            <tr key={i} className="border-t border-slate-200">
              <td className="p-2">{i + 1}</td>
              <td className="p-2"><div className="font-medium">{it.name}</div>{it.sku_code && <div className="font-mono text-[10px] text-slate-500">{it.sku_code}</div>}</td>
              <td className="p-2">{it.hsn}</td>
              <td className="p-2 text-right">{it.qty_label}</td>
              <td className="p-2 text-right">{inr(it.rate)}</td>
              <td className="p-2 text-right">{inr(it.taxable)}</td>
              <td className="p-2 text-right">{inr(it.gst_amt)}<div className="text-[10px] text-slate-400">{it.gst_pct}%</div></td>
              <td className="p-2 text-right font-semibold">{inr(it.amount)}</td>
            </tr>
          ))}
          {(inv.items || []).length === 0 && <tr><td colSpan={8} className="p-4 text-center text-slate-400">No items</td></tr>}
        </tbody>
      </table>

      {/* Totals + amount in words */}
      <div className="grid grid-cols-2 border-2 border-t-0 border-slate-800">
        <div className="p-3 border-r-2 border-slate-800">
          <div className="text-[10px] uppercase tracking-wider text-slate-500 font-semibold">Amount in Words</div>
          <div className="text-sm font-semibold mt-1">{inv.amount_in_words}</div>
        </div>
        <div className="p-3">
          <Row label="Taxable Amount" value={inr(t.subtotal)} />
          {t.is_interstate ? (
            <Row label="IGST" value={inr(t.igst)} />
          ) : (
            <>
              <Row label="SGST" value={inr(t.sgst)} />
              <Row label="CGST" value={inr(t.cgst)} />
            </>
          )}
          {Math.abs(t.round_off || 0) > 0.001 && <Row label="Round Off" value={inr(t.round_off)} />}
          <div className="border-t-2 border-slate-800 mt-2 pt-2">
            <Row label={<span className="font-bold">Grand Total</span>} value={<span className="text-lg font-extrabold text-[#a67c00]">{inr(t.grand_total)}</span>} />
          </div>
        </div>
      </div>

      {/* Pay-To + QR + Signatory */}
      <div className="grid grid-cols-3 border-2 border-t-0 border-slate-800">
        <div className="p-3 border-r border-slate-300 col-span-1">
          <div className="text-[10px] uppercase tracking-wider text-slate-500 font-semibold mb-1">Pay To</div>
          {seller.bank_name && <div className="text-xs">Bank: <span className="font-medium">{seller.bank_name}</span></div>}
          {seller.bank_account && <div className="text-xs">A/c: <span className="font-mono">{seller.bank_account}</span></div>}
          {seller.bank_ifsc && <div className="text-xs">IFSC: <span className="font-mono">{seller.bank_ifsc}</span></div>}
          {seller.bank_branch && <div className="text-xs">Branch: {seller.bank_branch}</div>}
          {seller.upi_id && <div className="text-xs mt-1">UPI: <span className="font-mono">{seller.upi_id}</span></div>}
        </div>
        <div className="p-3 border-r border-slate-300 flex flex-col items-center justify-center">
          {inv.upi_qr ? (
            <>
              <img src={inv.upi_qr} alt="UPI QR" className="h-24 w-24 object-contain" data-testid="invoice-upi-qr" />
              <div className="text-[10px] text-slate-500 mt-1">Scan &amp; Pay via UPI</div>
            </>
          ) : (
            <div className="text-[10px] text-slate-400 text-center">UPI QR<br />not configured</div>
          )}
        </div>
        <div className="p-3 flex flex-col justify-between">
          <div className="text-[10px] text-slate-500">For {seller.name}</div>
          <div className="mt-10 border-t border-slate-400 pt-1 text-center text-xs font-medium">{inv.signatory || "Authorized Signatory"}</div>
        </div>
      </div>

      {/* Message + Terms */}
      {inv.message && (
        <div className="mt-4 p-3 rounded-lg bg-[#faf6e6] border border-[#c9a227]/30 text-sm text-slate-700">{inv.message}</div>
      )}
      {inv.terms && (
        <div className="mt-3 border-t border-slate-200 pt-2">
          <div className="text-[10px] uppercase tracking-wider text-slate-500 mb-1 font-semibold">Terms &amp; Conditions</div>
          <div className="text-xs text-slate-600 whitespace-pre-wrap">{inv.terms}</div>
        </div>
      )}

      {/* Acknowledgement (optional — owner toggle) */}
      {inv.acknowledgement_enabled && (
        <div className="mt-6 border-2 border-dashed border-slate-400 p-3" data-testid="invoice-acknowledgement">
          <div className="text-[10px] uppercase tracking-wider text-slate-500 font-semibold mb-2">Acknowledgement</div>
          <div className="grid grid-cols-2 gap-4 text-xs">
            <div>
              <div>{seller.name}</div>
              <div className="text-slate-500 mt-1">Invoice No: <span className="font-semibold text-slate-800">{inv.doc_no}</span></div>
              <div className="text-slate-500">Date: <span className="font-semibold text-slate-800">{niceDate(inv.date)}</span></div>
              <div className="text-slate-500">Invoice Amount: <span className="font-semibold text-slate-800">{inr(t.grand_total)}</span></div>
            </div>
            <div className="flex flex-col justify-end">
              <div className="mt-10 border-t border-slate-400 pt-1 text-center">Receiver&apos;s Seal &amp; Sign</div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export function PrintEbillPage() {
  const { id } = useParams();
  const [eb, setEb] = useState(null);
  useEffect(() => { dms.printEbill(id).then(setEb); }, [id]);
  if (!eb) return <div className="p-8 text-center text-slate-500">Loading…</div>;
  return (
    <PrintFrame title={`e-Bill ${eb.ebill_no}`}>
      <VyaparInvoice inv={eb.invoice} />
    </PrintFrame>
  );
}

export function PrintRetailerBillPage() {
  const { id } = useParams();
  const [b, setB] = useState(null);
  useEffect(() => { dms.printRetailerBill(id).then(setB); }, [id]);
  if (!b) return <div className="p-8 text-center text-slate-500">Loading…</div>;
  return (
    <PrintFrame title={`Bill ${b.bill_no}`}>
      <VyaparInvoice inv={b.invoice} />
    </PrintFrame>
  );
}

export function PrintChallanPage() {
  const { id } = useParams();
  const [c, setC] = useState(null);
  useEffect(() => { dms.printChallan(id).then(setC).catch(() => setC(false)); }, [id]);
  if (c === false) return <div className="p-8 text-center text-rose-500">Challan not found</div>;
  if (!c) return <div className="p-8 text-center text-slate-500">Loading…</div>;
  const items = c.items || [];
  return (
    <PrintFrame title={`Delivery Challan ${c.challan_no}`}>
      <div className="border-b-2 border-[#a67c00] pb-4 mb-6">
        <div className="flex items-start justify-between">
          <div>
            <div className="text-2xl font-bold text-slate-900">DELIVERY CHALLAN</div>
            <div className="text-sm text-slate-500">Not a Tax Invoice</div>
          </div>
          <div className="text-right">
            <div className="text-lg font-bold text-[#a67c00]">{c.distributor?.name || c.company_name}</div>
            <div className="text-xs text-slate-500">{c.distributor?.address}</div>
            {c.distributor?.kyc?.gstin && <div className="text-xs text-slate-500">GSTIN: {c.distributor.kyc.gstin}</div>}
          </div>
        </div>
      </div>
      <div className="grid grid-cols-2 gap-8 mb-6">
        <div>
          <div className="text-[10px] uppercase tracking-wider text-slate-500 mb-1">Deliver To</div>
          <div className="font-semibold text-slate-900">{c.retailer?.name}</div>
          <div className="text-xs text-slate-600">{c.retailer?.address}</div>
          <div className="text-xs text-slate-600">Ph: {c.retailer?.phone}</div>
        </div>
        <div>
          <Row label="Challan #" value={c.challan_no} />
          <Row label="Date" value={niceDate(c.created_at)} />
          <Row label="Order Ref" value={c.order_no} />
          {c.invoice_no && <Row label="Invoice #" value={c.invoice_no} />}
        </div>
      </div>
      <table className="w-full text-sm border border-slate-200 mb-6">
        <thead><tr className="bg-slate-50 text-left"><th className="p-2">#</th><th className="p-2">Product</th><th className="p-2 text-right">Boxes</th><th className="p-2 text-right">Pcs</th></tr></thead>
        <tbody>
          {items.map((it, i) => (
            <tr key={i} className="border-t border-slate-100">
              <td className="p-2">{i + 1}</td>
              <td className="p-2"><div className="font-medium">{it.product_name}</div><div className="text-xs font-mono text-slate-500">{it.sku_code}</div></td>
              <td className="p-2 text-right">{it.qty_boxes || 0}</td>
              <td className="p-2 text-right">{it.qty_pcs || 0}</td>
            </tr>
          ))}
          {items.length === 0 && <tr><td colSpan={4} className="p-4 text-center text-slate-400">No items</td></tr>}
        </tbody>
      </table>
      <div className="grid grid-cols-2 gap-8 mt-12 text-xs text-slate-500">
        <div className="border-t border-slate-300 pt-2 text-center">Received By</div>
        <div className="border-t border-slate-300 pt-2 text-center">Authorised Signatory</div>
      </div>
    </PrintFrame>
  );
}



export function PrintPurchaseOrderPage() {
  const { id } = useParams();
  const [o, setO] = useState(null);
  useEffect(() => { dms.printPurchaseOrder(id).then(setO); }, [id]);
  if (!o) return <div className="p-8 text-center text-slate-500">Loading…</div>;
  return (
    <PrintFrame title={`Purchase Order ${o.order_no}`}>
      <div className="border-b-2 border-[#a67c00] pb-4 mb-6 flex items-start justify-between">
        <div>
          <div className="text-2xl font-bold text-slate-900">PURCHASE ORDER</div>
          <div className="text-sm text-slate-500">For Supplier</div>
        </div>
        <div className="text-right">
          <div className="text-lg font-bold text-[#a67c00]">{o.company_name}</div>
        </div>
      </div>
      <div className="grid grid-cols-2 gap-8 mb-6">
        <div>
          <div className="text-[10px] uppercase tracking-wider text-slate-500 mb-1">Buyer (Distributor)</div>
          <div className="font-semibold text-slate-900">{o.distributor?.name}</div>
          <div className="text-xs text-slate-600">{o.distributor?.address}</div>
          <div className="text-xs text-slate-600">Ph: {o.distributor?.phone}</div>
        </div>
        <div>
          <Row label="PO #" value={o.order_no} />
          <Row label="Date" value={niceDate(o.created_at)} />
          <Row label="Status" value={o.status?.replace(/_/g, " ")} />
        </div>
      </div>
      <table className="w-full text-sm border border-slate-200 mb-6">
        <thead><tr className="bg-slate-50 text-left"><th className="p-2">#</th><th className="p-2">Product</th><th className="p-2 text-right">Qty (Boxes)</th><th className="p-2 text-right">Rate</th><th className="p-2 text-right">Amount</th></tr></thead>
        <tbody>{(o.items || []).map((it, i) => (
          <tr key={i} className="border-t border-slate-100">
            <td className="p-2">{i + 1}</td>
            <td className="p-2"><div className="font-medium">{it.product_name}</div><div className="text-xs font-mono text-slate-500">{it.sku_code}</div></td>
            <td className="p-2 text-right">{it.qty_boxes_ordered}</td>
            <td className="p-2 text-right">{inr(it.unit_price)}</td>
            <td className="p-2 text-right font-semibold">{inr(it.line_total)}</td>
          </tr>
        ))}</tbody>
      </table>
      <div className="flex justify-end">
        <div className="w-64">
          <Row label="Subtotal" value={inr(o.subtotal)} />
          <Row label="GST" value={inr(o.gst_total)} />
          <div className="border-t border-slate-200 mt-2 pt-2"><Row label="Grand Total" value={<span className="text-lg font-bold text-[#a67c00]">{inr(o.total)}</span>} /></div>
        </div>
      </div>
      {o.invoice_message && <div className="mt-6 p-3 rounded-lg bg-[#faf6e6] border border-[#c9a227]/30 text-sm text-slate-700">{o.invoice_message}</div>}
      {o.invoice_terms && <div className="mt-4 border-t border-slate-200 pt-3"><div className="text-[10px] uppercase tracking-wider text-slate-500 mb-1 font-semibold">Terms &amp; Conditions</div><div className="text-xs text-slate-600 whitespace-pre-wrap">{o.invoice_terms}</div></div>}
    </PrintFrame>
  );
}

export function PrintDocumentPage() {
  const { id } = useParams();
  const [d, setD] = useState(null);
  useEffect(() => { dms.printDocument(id).then(setD); }, [id]);
  if (!d) return <div className="p-8 text-center text-slate-500">Loading…</div>;

  const DOC_STYLES = {
    estimate:         { color: "#3b82f6", bg: "bg-blue-50",    border: "border-blue-500",    text: "text-blue-700",    tag: "PROPOSAL" },
    delivery_challan: { color: "#059669", bg: "bg-emerald-50", border: "border-emerald-600", text: "text-emerald-700", tag: "DISPATCH" },
    sale_return:      { color: "#e11d48", bg: "bg-rose-50",    border: "border-rose-600",    text: "text-rose-700",    tag: "RETURN" },
    credit_note:      { color: "#7c3aed", bg: "bg-violet-50",  border: "border-violet-600",  text: "text-violet-700",  tag: "CR NOTE" },
    debit_note:       { color: "#ea580c", bg: "bg-orange-50",  border: "border-orange-600",  text: "text-orange-700",  tag: "DR NOTE" },
  };
  const s = DOC_STYLES[d.type] || { color: "#a67c00", bg: "bg-amber-50", border: "border-amber-600", text: "text-amber-700", tag: "DOCUMENT" };

  return (
    <PrintFrame title={`${d.doc_type_label} ${d.doc_no}`}>
      <div className={`border-b-2 ${s.border} pb-4 mb-6 flex items-start justify-between`}>
        <div>
          <div className={`text-2xl font-bold uppercase ${s.text}`}>{d.doc_type_label}</div>
          <div className="mt-1">
            <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold tracking-widest ${s.bg} ${s.text} border ${s.border}`} data-testid={`doc-tag-${d.type}`}>
              {s.tag}
            </span>
            <span className="ml-2 text-xs text-slate-500">Not a Tax Invoice</span>
          </div>
        </div>
        <div className="text-right">
          <div className={`text-lg font-bold ${s.text}`}>{d.company_name}</div>
          <div className="text-xs text-slate-500 mt-1">{d.doc_type_label} No: <span className="font-mono">{d.doc_no}</span></div>
          <div className="text-xs text-slate-500">Date: {d.date}</div>
        </div>
      </div>
      <div className={`grid grid-cols-2 gap-8 mb-6 p-3 rounded-lg ${s.bg} border ${s.border}`}>
        <div>
          <div className="text-[10px] uppercase tracking-wider text-slate-500 mb-1">Party</div>
          <div className="font-semibold text-slate-900">{d.party_name}</div>
          {d.party?.address && <div className="text-xs text-slate-600">{d.party.address}</div>}
          {d.party?.phone && <div className="text-xs text-slate-600">Ph: {d.party.phone}</div>}
          {d.party?.gstin && <div className="text-xs text-slate-600">GSTIN: {d.party.gstin}</div>}
        </div>
        <div>
          <Row label="Doc No" value={d.doc_no} />
          <Row label="Date" value={d.date} />
        </div>
      </div>
      <table className="w-full text-sm border border-slate-200 mb-6">
        <thead><tr className={`${s.bg} text-left`}><th className="p-2">#</th><th className="p-2">Description</th><th className="p-2 text-right">Qty</th><th className="p-2 text-right">Rate</th><th className="p-2 text-right">Amount</th></tr></thead>
        <tbody>{(d.items || []).map((it, i) => (
          <tr key={i} className="border-t border-slate-100">
            <td className="p-2">{i + 1}</td><td className="p-2">{it.description}</td>
            <td className="p-2 text-right">{it.qty}</td>
            <td className="p-2 text-right">{inr(it.rate)}</td>
            <td className="p-2 text-right font-semibold">{inr(it.amount)}</td>
          </tr>
        ))}</tbody>
      </table>
      <div className="flex justify-end">
        <div className="w-64">
          <Row label="Subtotal" value={inr(d.subtotal)} />
          <Row label={`GST (${d.gst_pct}%)`} value={inr(d.gst_total)} />
          <div className="border-t border-slate-200 mt-2 pt-2"><Row label="Grand Total" value={<span className={`text-lg font-bold ${s.text}`}>{inr(d.total)}</span>} /></div>
        </div>
      </div>
      {d.notes && <div className="mt-6 p-3 rounded-lg bg-slate-50 text-sm text-slate-700"><strong>Notes:</strong> {d.notes}</div>}
      {d.invoice_message && <div className={`mt-4 p-3 rounded-lg ${s.bg} border ${s.border} text-sm text-slate-700`}>{d.invoice_message}</div>}
      {d.invoice_terms && <div className="mt-4 border-t border-slate-200 pt-3"><div className="text-[10px] uppercase tracking-wider text-slate-500 mb-1 font-semibold">Terms &amp; Conditions</div><div className="text-xs text-slate-600 whitespace-pre-wrap">{d.invoice_terms}</div></div>}
    </PrintFrame>
  );
}

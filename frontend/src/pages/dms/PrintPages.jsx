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

export function PrintEbillPage() {
  const { id } = useParams();
  const [eb, setEb] = useState(null);
  useEffect(() => { dms.printEbill(id).then(setEb); }, [id]);
  if (!eb) return <div className="p-8 text-center text-slate-500">Loading…</div>;
  return (
    <PrintFrame title={`e-Bill ${eb.ebill_no}`}>
      <div className="border-b-2 border-[#a67c00] pb-4 mb-6">
        <div className="flex items-start justify-between">
          <div>
            <div className="text-2xl font-bold text-slate-900">TAX INVOICE</div>
            <div className="text-sm text-slate-500">Original for Recipient</div>
          </div>
          <div className="text-right">
            <div className="text-lg font-bold text-[#a67c00]">Bharat Oil</div>
            <div className="text-xs text-slate-500">Distribution Management</div>
          </div>
        </div>
      </div>
      <div className="grid grid-cols-2 gap-8 mb-6">
        <div>
          <div className="text-[10px] uppercase tracking-wider text-slate-500 mb-1">Bill To</div>
          <div className="font-semibold text-slate-900">{eb.distributor?.name}</div>
          <div className="text-xs text-slate-600">{eb.distributor?.address}</div>
          {eb.distributor?.kyc?.gstin && <div className="text-xs text-slate-600">GSTIN: {eb.distributor.kyc.gstin}</div>}
          <div className="text-xs text-slate-600">Ph: {eb.distributor?.phone}</div>
        </div>
        <div>
          <Row label="Invoice #" value={eb.ebill_no} />
          <Row label="Date" value={niceDate(eb.created_at)} />
          <Row label="Order Ref" value={eb.order_no} />
        </div>
      </div>
      <table className="w-full text-sm border border-slate-200 mb-6">
        <thead><tr className="bg-slate-50 text-left"><th className="p-2">#</th><th className="p-2">Product</th><th className="p-2 text-right">Qty</th><th className="p-2 text-right">Rate</th><th className="p-2 text-right">GST%</th><th className="p-2 text-right">Amount</th></tr></thead>
        <tbody>
          {eb.items.map((it, i) => (
            <tr key={i} className="border-t border-slate-100">
              <td className="p-2">{i + 1}</td>
              <td className="p-2"><div className="font-medium">{it.product_name}</div><div className="text-xs font-mono text-slate-500">{it.sku_code}</div></td>
              <td className="p-2 text-right">{it.billed_qty_boxes} boxes</td>
              <td className="p-2 text-right">{inr(it.unit_price)}</td>
              <td className="p-2 text-right">{it.gst_pct}%</td>
              <td className="p-2 text-right font-semibold">{inr(it.line_total)}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <div className="flex justify-end">
        <div className="w-64">
          <Row label="Subtotal" value={inr(eb.subtotal)} />
          <Row label="GST" value={inr(eb.gst_total)} />
          <div className="border-t border-slate-200 mt-2 pt-2"><Row label="Grand Total" value={<span className="text-lg font-bold text-[#a67c00]">{inr(eb.total)}</span>} /></div>
        </div>
      </div>
      {eb.invoice_message && (
        <div className="mt-6 p-3 rounded-lg bg-[#faf6e6] border border-[#c9a227]/30 text-sm text-slate-700">
          {eb.invoice_message}
        </div>
      )}
      {eb.invoice_terms && (
        <div className="mt-4 border-t border-slate-200 pt-3">
          <div className="text-[10px] uppercase tracking-wider text-slate-500 mb-1 font-semibold">Terms &amp; Conditions</div>
          <div className="text-xs text-slate-600 whitespace-pre-wrap">{eb.invoice_terms}</div>
        </div>
      )}
      <div className="mt-8 text-center text-xs text-slate-500">Thank you for your business!</div>
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
      <div className="border-b-2 border-[#a67c00] pb-4 mb-6">
        <div className="flex items-start justify-between">
          <div><div className="text-2xl font-bold text-slate-900">RETAIL INVOICE</div><div className="text-sm text-slate-500">Original for Recipient</div></div>
          <div className="text-right"><div className="text-lg font-bold text-[#a67c00]">{b.distributor?.name}</div><div className="text-xs text-slate-500">{b.distributor?.address}</div>{b.distributor?.kyc?.gstin && <div className="text-xs text-slate-500">GSTIN: {b.distributor.kyc.gstin}</div>}</div>
        </div>
      </div>
      <div className="grid grid-cols-2 gap-8 mb-6">
        <div>
          <div className="text-[10px] uppercase tracking-wider text-slate-500 mb-1">Bill To</div>
          <div className="font-semibold">{b.retailer?.name}</div>
          <div className="text-xs text-slate-600">{b.retailer?.address}</div>
          <div className="text-xs text-slate-600">Ph: {b.retailer?.phone}</div>
        </div>
        <div>
          <Row label="Bill #" value={b.bill_no} />
          <Row label="Date" value={niceDate(b.created_at)} />
          <Row label="Order Ref" value={b.order_no} />
        </div>
      </div>
      <table className="w-full text-sm border border-slate-200 mb-6">
        <thead><tr className="bg-slate-50 text-left"><th className="p-2">#</th><th className="p-2">Product</th><th className="p-2 text-right">Qty</th><th className="p-2 text-right">Rate</th><th className="p-2 text-right">Amount</th></tr></thead>
        <tbody>
          {b.items.map((it, i) => (
            <tr key={i} className="border-t border-slate-100">
              <td className="p-2">{i + 1}</td>
              <td className="p-2"><div className="font-medium">{it.product_name}</div><div className="text-xs font-mono text-slate-500">{it.sku_code}</div></td>
              <td className="p-2 text-right">{it.dispatched_qty_boxes} boxes {it.dispatched_qty_pcs > 0 && `+ ${it.dispatched_qty_pcs} pcs`}</td>
              <td className="p-2 text-right">{inr(it.box_price)}/box</td>
              <td className="p-2 text-right font-semibold">{inr(it.line_total)}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <div className="flex justify-end">
        <div className="w-64">
          <Row label="Subtotal" value={inr(b.subtotal)} />
          <Row label="GST" value={inr(b.gst_total)} />
          <div className="border-t border-slate-200 mt-2 pt-2"><Row label="Grand Total" value={<span className="text-lg font-bold text-[#a67c00]">{inr(b.total)}</span>} /></div>
        </div>
      </div>
      {b.invoice_message && (
        <div className="mt-6 p-3 rounded-lg bg-[#faf6e6] border border-[#c9a227]/30 text-sm text-slate-700">
          {b.invoice_message}
        </div>
      )}
      {b.invoice_terms && (
        <div className="mt-4 border-t border-slate-200 pt-3">
          <div className="text-[10px] uppercase tracking-wider text-slate-500 mb-1 font-semibold">Terms &amp; Conditions</div>
          <div className="text-xs text-slate-600 whitespace-pre-wrap">{b.invoice_terms}</div>
        </div>
      )}
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
  return (
    <PrintFrame title={`${d.doc_type_label} ${d.doc_no}`}>
      <div className="border-b-2 border-[#a67c00] pb-4 mb-6 flex items-start justify-between">
        <div>
          <div className="text-2xl font-bold text-slate-900 uppercase">{d.doc_type_label}</div>
          <div className="text-sm text-slate-500">Not a Tax Invoice</div>
        </div>
        <div className="text-right"><div className="text-lg font-bold text-[#a67c00]">{d.company_name}</div></div>
      </div>
      <div className="grid grid-cols-2 gap-8 mb-6">
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
        <thead><tr className="bg-slate-50 text-left"><th className="p-2">#</th><th className="p-2">Description</th><th className="p-2 text-right">Qty</th><th className="p-2 text-right">Rate</th><th className="p-2 text-right">Amount</th></tr></thead>
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
          <div className="border-t border-slate-200 mt-2 pt-2"><Row label="Grand Total" value={<span className="text-lg font-bold text-[#a67c00]">{inr(d.total)}</span>} /></div>
        </div>
      </div>
      {d.notes && <div className="mt-6 p-3 rounded-lg bg-slate-50 text-sm text-slate-700"><strong>Notes:</strong> {d.notes}</div>}
      {d.invoice_message && <div className="mt-4 p-3 rounded-lg bg-[#faf6e6] border border-[#c9a227]/30 text-sm text-slate-700">{d.invoice_message}</div>}
      {d.invoice_terms && <div className="mt-4 border-t border-slate-200 pt-3"><div className="text-[10px] uppercase tracking-wider text-slate-500 mb-1 font-semibold">Terms &amp; Conditions</div><div className="text-xs text-slate-600 whitespace-pre-wrap">{d.invoice_terms}</div></div>}
    </PrintFrame>
  );
}

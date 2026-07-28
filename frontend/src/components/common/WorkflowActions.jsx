import React from "react";
import api from "@/lib/api";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu, DropdownMenuTrigger, DropdownMenuContent, DropdownMenuItem, DropdownMenuSeparator,
} from "@/components/ui/dropdown-menu";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { MoreHorizontal, CheckCircle2, XCircle, Truck, PackageCheck, PackagePlus, Loader2, GitBranch } from "lucide-react";

/**
 * Row-level workflow actions.
 * `entity` is one of: 'batch' | 'primary-order' | 'secondary-order' | 'invoice' | 'dispatch'
 */
export default function WorkflowActions({ entity, row, onDone }) {
  const [busy, setBusy] = React.useState(false);
  const [dispatchOpen, setDispatchOpen] = React.useState(false);
  const [receiveOpen, setReceiveOpen] = React.useState(false);
  const [form, setForm] = React.useState({ vehicle_no: "LG-142-KL", driver: "Musa A.", lr_no: "LR" + Date.now(), transporter: "GO OIL Logistics", route: "Lagos → Abuja" });

  const run = async (fn, successMsg) => {
    setBusy(true);
    try {
      const r = await fn();
      toast.success(successMsg || "Action completed");
      onDone?.(r?.data);
    } catch (e) {
      toast.error(e.response?.data?.detail || e.message);
    } finally { setBusy(false); }
  };

  // ============ Batch actions ============
  if (entity === "batch") {
    return (
      <div className="flex items-center gap-1">
        {!row.stocked_in && (
          <Button size="sm" variant="outline" className="h-8 border-gold/40 text-gold-dark hover:bg-gold/10"
            disabled={busy}
            onClick={() => run(() => api.post(`/workflow/batches/${row.id}/stock-in`), "Batch stocked in — Company Inventory updated")}
            data-testid={`batch-stock-in-${row.id}`}>
            {busy ? <Loader2 size={13} className="animate-spin" /> : <><PackagePlus size={13} className="mr-1" /> Stock In</>}
          </Button>
        )}
        {row.stocked_in && <span className="text-xs text-emerald-700">Stocked in ✓</span>}
      </div>
    );
  }

  // ============ Primary / Secondary order actions ============
  if (entity === "primary-order" || entity === "secondary-order") {
    const isPending = ["pending_approval", "backorder", "draft"].includes(row.status);
    const kind = entity === "primary-order" ? "primary-orders" : "secondary-orders";
    return (
      <div className="flex items-center gap-1">
        {isPending && (
          <>
            <Button size="sm" className="h-8 bg-emerald-600 hover:bg-emerald-700 text-white"
              disabled={busy}
              onClick={() => run(() => api.post(`/workflow/${kind}/${row.id}/approve`), "Order approved → Invoice generated → Stock reserved")}
              data-testid={`approve-${row.id}`}>
              <CheckCircle2 size={13} className="mr-1" /> Approve
            </Button>
            <Button size="sm" variant="outline" className="h-8 border-rose-200 text-rose-700 hover:bg-rose-50"
              disabled={busy}
              onClick={() => run(() => api.post(`/workflow/${kind}/${row.id}/reject`, { reason: "Rejected by manager" }), "Order rejected")}
              data-testid={`reject-${row.id}`}>
              <XCircle size={13} className="mr-1" /> Reject
            </Button>
          </>
        )}
        {!isPending && <span className="text-xs text-ink-muted">—</span>}
      </div>
    );
  }

  // ============ Invoice actions ============
  if (entity === "invoice") {
    const canDispatch = row.status === "issued";
    return (
      <>
        {canDispatch ? (
          <Button size="sm" variant="outline" className="h-8 border-gold/40 text-gold-dark hover:bg-gold/10"
            onClick={() => setDispatchOpen(true)} data-testid={`dispatch-${row.id}`}>
            <Truck size={13} className="mr-1" /> Dispatch
          </Button>
        ) : <span className="text-xs text-ink-muted">—</span>}

        <Dialog open={dispatchOpen} onOpenChange={setDispatchOpen}>
          <DialogContent className="sm:max-w-md">
            <DialogHeader>
              <DialogTitle>Create Dispatch</DialogTitle>
              <DialogDescription>Vehicle, driver & LR for invoice <b>{row.invoice_no}</b></DialogDescription>
            </DialogHeader>
            <div className="space-y-3">
              <div><Label>Vehicle No</Label><Input value={form.vehicle_no} onChange={(e) => setForm({ ...form, vehicle_no: e.target.value })} data-testid="disp-vehicle" /></div>
              <div><Label>Driver</Label><Input value={form.driver} onChange={(e) => setForm({ ...form, driver: e.target.value })} data-testid="disp-driver" /></div>
              <div><Label>LR Number</Label><Input value={form.lr_no} onChange={(e) => setForm({ ...form, lr_no: e.target.value })} data-testid="disp-lr" /></div>
              <div><Label>Transporter</Label><Input value={form.transporter} onChange={(e) => setForm({ ...form, transporter: e.target.value })} data-testid="disp-transporter" /></div>
              <div><Label>Route</Label><Input value={form.route} onChange={(e) => setForm({ ...form, route: e.target.value })} data-testid="disp-route" /></div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setDispatchOpen(false)}>Cancel</Button>
              <Button className="bg-gold hover:bg-gold-dark text-white"
                disabled={busy}
                onClick={async () => {
                  await run(() => api.post(`/workflow/invoices/${row.id}/dispatch`, form), "Dispatched → stock moved to Goods In Transit");
                  setDispatchOpen(false);
                }}
                data-testid="disp-confirm">
                {busy ? <Loader2 size={14} className="animate-spin" /> : "Create Dispatch"}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </>
    );
  }

  // ============ Dispatch (GRN) actions ============
  if (entity === "dispatch") {
    const canReceive = row.status === "in_transit" || row.status === "prepared";
    return (
      <>
        {canReceive ? (
          <Button size="sm" className="h-8 bg-gold hover:bg-gold-dark text-white"
            disabled={busy}
            onClick={() => run(() => api.post(`/workflow/dispatches/${row.id}/receive`, {}), "GRN created → partner inventory updated")}
            data-testid={`receive-${row.id}`}>
            <PackageCheck size={13} className="mr-1" /> Receive
          </Button>
        ) : <span className="text-xs text-ink-muted">—</span>}
      </>
    );
  }

  return null;
}

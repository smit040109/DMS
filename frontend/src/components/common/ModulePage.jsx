import React, { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "@/lib/api";
import PageHeader from "@/components/common/PageHeader";
import DataTable from "@/components/common/DataTable";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Switch } from "@/components/ui/switch";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from "@/components/ui/dialog";
import { toast } from "sonner";
import { Plus, Sparkles } from "lucide-react";

/**
 * Derive form fields from column metadata.
 * Skips display-only columns like "actions", "utilization", "status" (auto-set).
 */
function fieldsFromColumns(columns) {
  const skip = new Set(["actions", "utilization", "status", "id", "_id", "tenant_id", "created_at", "updated_at"]);
  const auto = new Set([
    "outstanding", "cashback_earned", "ltv", "orders_count", "usage", "occupied",
    "line_items", "subtotal", "tax", "total", "paid", "balance", "variance",
  ]);
  return columns
    .filter((c) => c.key && !skip.has(c.key) && !auto.has(c.key))
    .map((c) => {
      let type = "text";
      if (c.type === "currency") type = "number";
      else if (c.type === "date") type = "date";
      else if (c.type === "chip") type = "text";
      else if (["credit_limit", "credit_days", "capacity", "reorder_level",
                 "on_hand", "reserved", "cost", "mrp", "trade_price", "gst_rate",
                 "rating", "amount", "value", "limit", "quantity", "batch_quantity",
                 "distance_km"].includes(c.key)) type = "number";
      else if (["notes", "description", "address", "narration"].includes(c.key)) type = "textarea";
      return {
        name: c.key,
        label: c.label || c.key,
        type,
        required: ["name", "code", "sku_code", "batch_no", "invoice_no", "order_no", "payment_no"].includes(c.key),
      };
    });
}

function makeDefaults(fields) {
  const o = {};
  for (const f of fields) {
    o[f.name] = f.type === "number" ? 0 : (f.type === "date" ? "" : "");
  }
  return o;
}

function CreateDialog({ open, onOpenChange, resource, title, fields, onDone }) {
  const [form, setForm] = useState(() => makeDefaults(fields));
  const [busy, setBusy] = useState(false);

  // Reset when opening
  useEffect(() => {
    if (open) setForm(makeDefaults(fields));
  }, [open, fields]);

  const setField = (name, value) => setForm((f) => ({ ...f, [name]: value }));

  const submit = async () => {
    // Validate required
    for (const f of fields) {
      if (f.required && !String(form[f.name] ?? "").trim()) {
        toast.error(`${f.label} is required`);
        return;
      }
    }
    setBusy(true);
    try {
      // Cast numbers
      const payload = { ...form };
      for (const f of fields) {
        if (f.type === "number") payload[f.name] = payload[f.name] === "" ? 0 : Number(payload[f.name]);
      }
      const { data } = await api.post(`/collections/${resource}`, payload);
      toast.success(`${title.slice(0, -1) || "Record"} created`);
      onOpenChange(false);
      onDone?.(data);
    } catch (e) {
      toast.error(e.response?.data?.detail || e.message || "Failed to create");
    } finally { setBusy(false); }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>New {title?.replace(/s$/, "") || "record"}</DialogTitle>
          <DialogDescription>Fill the fields below to create a new record.</DialogDescription>
        </DialogHeader>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 py-2 max-h-[60vh] overflow-y-auto pr-1">
          {fields.map((f) => (
            <div key={f.name} className={f.type === "textarea" ? "md:col-span-2" : ""}>
              <Label className="text-xs">{f.label}{f.required && <span className="text-rose-500"> *</span>}</Label>
              {f.type === "textarea" ? (
                <Textarea
                  value={form[f.name] ?? ""}
                  onChange={(e) => setField(f.name, e.target.value)}
                  rows={2}
                  className="mt-1.5"
                  data-testid={`create-field-${f.name}`}
                />
              ) : (
                <Input
                  type={f.type === "number" ? "number" : (f.type === "date" ? "date" : "text")}
                  value={form[f.name] ?? ""}
                  onChange={(e) => setField(f.name, e.target.value)}
                  className="mt-1.5"
                  data-testid={`create-field-${f.name}`}
                />
              )}
            </div>
          ))}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={busy}>Cancel</Button>
          <Button onClick={submit} disabled={busy} className="bg-gold hover:bg-gold-dark text-white" data-testid="create-submit">
            {busy ? "Creating..." : "Create"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

/**
 * Generic module page. Renders a page header + a reusable data table.
 * Fetches from /api/collections/<resource>.
 *
 * Now with WORKING create dialog + Ask AI navigation.
 */
export default function ModulePage({
  resource,
  title,
  subtitle,
  crumbs = ["Dashboard"],
  columns = [],
  emptyLabel,
  primaryAction = { label: "Create record", icon: Plus },
  extraContent,
  disableCreate = false,
}) {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [reload, setReload] = useState(0);
  const [dialogOpen, setDialogOpen] = useState(false);
  const nav = useNavigate();

  const fields = useMemo(() => fieldsFromColumns(columns), [columns]);

  useEffect(() => {
    let mounted = true;
    setLoading(true);
    api
      .get(`/collections/${resource}`)
      .then((r) => mounted && setData(r.data.data || []))
      .catch(() => mounted && setData([]))
      .finally(() => mounted && setLoading(false));
    return () => { mounted = false; };
  }, [resource, reload]);

  const askAi = () => {
    // Store context for the AI page then navigate
    try {
      sessionStorage.setItem("ai:context", JSON.stringify({
        resource, title, sample: data.slice(0, 3),
      }));
    } catch { /* ignore */ }
    nav("/app/ai-assistant");
  };

  return (
    <div className="animate-in-fade">
      <PageHeader
        crumbs={[...crumbs, title]}
        title={title}
        subtitle={subtitle}
        actions={
          <>
            <Button variant="outline" className="border-[#E5E7EB] h-10" data-testid={`${resource}-ai`} onClick={askAi}>
              <Sparkles size={15} className="mr-2 text-gold" /> Ask AI
            </Button>
            {!disableCreate && (
              <Button
                className="bg-gold hover:bg-gold-dark text-white h-10"
                data-testid={`${resource}-primary-action`}
                onClick={() => setDialogOpen(true)}
              >
                <primaryAction.icon size={15} className="mr-2" /> {primaryAction.label}
              </Button>
            )}
          </>
        }
      />
      {extraContent}
      <DataTable
        data={data}
        columns={columns}
        loading={loading}
        emptyLabel={emptyLabel}
        testId={`${resource}-table`}
      />

      <CreateDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        resource={resource}
        title={title}
        fields={fields}
        onDone={() => setReload((v) => v + 1)}
      />
    </div>
  );
}

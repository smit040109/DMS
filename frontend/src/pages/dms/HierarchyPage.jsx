import React, { useEffect, useState, useCallback } from "react";
import { dms } from "./api";
import { PageHeader } from "./OwnerPages";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import { Users, Store, UserCog, Network, Plus, X, ChevronRight } from "lucide-react";

const GOLD_BTN = "bg-[#a67c00] hover:bg-[#8a6800] text-white";

function Picker({ label, options, value, onChange }) {
  return (
    <select
      value={value}
      onChange={e => onChange(e.target.value)}
      className="border border-slate-300 rounded-md px-2 py-1.5 text-sm bg-white min-w-[150px]"
    >
      <option value="">{label}</option>
      {options.map(o => <option key={o.id} value={o.id}>{o.name || o.email || o.id}</option>)}
    </select>
  );
}

function DistCard({ node, tlId, onUnassignTlDist, onUnassignDistSp }) {
  return (
    <div className="ml-4 mt-2 border-l-2 border-amber-200 pl-3">
      <div className="flex items-center gap-2">
        <Store size={14} className="text-[#a67c00]" />
        <span className="font-semibold text-slate-800 text-sm">{node.name}</span>
        {node.region && <span className="text-[11px] text-slate-400">{node.region}</span>}
        {tlId && (
          <button onClick={() => onUnassignTlDist(tlId, node.id)} title="Remove from Team Leader"
            className="ml-1 text-slate-300 hover:text-rose-500"><X size={13} /></button>
        )}
      </div>
      <div className="ml-5 mt-1 flex flex-wrap gap-1.5">
        {(node.salespersons || []).length === 0 && <span className="text-[11px] text-slate-400">No salesperson assigned</span>}
        {(node.salespersons || []).map(sp => (
          <span key={sp.id} className="inline-flex items-center gap-1 text-[11px] bg-sky-50 text-sky-700 border border-sky-200 rounded-full px-2 py-0.5">
            <UserCog size={11} /> {sp.name}
            <button onClick={() => onUnassignDistSp(sp.id, node.id)} className="hover:text-rose-500"><X size={11} /></button>
          </span>
        ))}
      </div>
      <div className="ml-5 mt-1 flex flex-wrap gap-1.5">
        {(node.retailers || []).length === 0 && <span className="text-[11px] text-slate-400">No retailers</span>}
        {(node.retailers || []).map(r => (
          <span key={r.id} className="inline-flex items-center gap-1 text-[11px] bg-emerald-50 text-emerald-700 border border-emerald-200 rounded-full px-2 py-0.5">
            <Users size={11} /> {r.name}
          </span>
        ))}
      </div>
    </div>
  );
}

export function OwnerHierarchyPage() {
  const [data, setData] = useState(null);
  const [busy, setBusy] = useState(false);

  // assignment form state
  const [rmTl, setRmTl] = useState({ rm: "", tl: "" });
  const [tlDist, setTlDist] = useState({ tl: "", dist: "" });
  const [distSp, setDistSp] = useState({ dist: "", sp: "" });
  const [retailers, setRetailers] = useState([]);
  const [selRet, setSelRet] = useState({});
  const [moveDist, setMoveDist] = useState("");

  const load = useCallback(async () => {
    setBusy(true);
    try {
      const [h, rl] = await Promise.all([dms.ownerHierarchy(), dms.listRetailers().catch(() => ({ data: [] }))]);
      setData(h);
      setRetailers(rl.data || []);
    }
    catch (e) { toast.error(e?.response?.data?.detail || "Failed to load hierarchy"); }
    finally { setBusy(false); }
  }, []);
  useEffect(() => { load(); }, [load]);

  const all = data?.all || { regional_managers: [], team_leaders: [], salespersons: [], distributors: [] };

  const doAssignRmTl = async () => {
    if (!rmTl.rm || !rmTl.tl) return toast.error("Select RM and Team Leader");
    try { await dms.assignRmTl({ regional_manager_id: rmTl.rm, team_leader_id: rmTl.tl }); toast.success("Team Leader assigned to RM"); setRmTl({ rm: "", tl: "" }); load(); }
    catch (e) { toast.error(e?.response?.data?.detail || "Failed"); }
  };
  const doAssignTlDist = async () => {
    if (!tlDist.tl || !tlDist.dist) return toast.error("Select Team Leader and Distributor");
    try { await dms.assignTlDist({ team_leader_id: tlDist.tl, distributor_id: tlDist.dist }); toast.success("Distributor assigned to Team Leader"); setTlDist({ tl: "", dist: "" }); load(); }
    catch (e) { toast.error(e?.response?.data?.detail || "Failed"); }
  };
  const doAssignDistSp = async () => {
    if (!distSp.dist || !distSp.sp) return toast.error("Select Distributor and Salesperson");
    try { await dms.assignSpDist({ salesperson_id: distSp.sp, distributor_id: distSp.dist }); toast.success("Salesperson assigned to Distributor"); setDistSp({ dist: "", sp: "" }); load(); }
    catch (e) { toast.error(e?.response?.data?.detail || "Failed"); }
  };
  const unassignTlDist = async (tl, did) => {
    try { await dms.unassignTlDist(tl, did); toast.success("Removed"); load(); }
    catch (e) { toast.error(e?.response?.data?.detail || "Failed"); }
  };
  const unassignDistSp = async (sp, did) => {
    try { await dms.unassignSpDist(sp, did); toast.success("Removed"); load(); }
    catch (e) { toast.error(e?.response?.data?.detail || "Failed"); }
  };
  const selectedRetailerIds = Object.keys(selRet).filter(k => selRet[k]);
  const doBulkMove = async () => {
    if (selectedRetailerIds.length === 0) return toast.error("Select at least one retailer");
    if (!moveDist) return toast.error("Select the target distributor");
    try {
      const r = await dms.bulkAssignRetailers(selectedRetailerIds, moveDist);
      toast.success(`Moved ${r.moved} retailer(s)`);
      setSelRet({}); setMoveDist(""); load();
    } catch (e) { toast.error(e?.response?.data?.detail || "Move failed"); }
  };

  const renderDist = (node, tlId) => (
    <DistCard key={node.id} node={node} tlId={tlId}
      onUnassignTlDist={unassignTlDist} onUnassignDistSp={unassignDistSp} />
  );

  return (
    <div>
      <PageHeader title="Organization Hierarchy"
        subtitle="Set who reports to whom — Regional Manager → Team Leaders → Distributors → Salespersons & Retailers"
        action={<Button variant="outline" onClick={load} disabled={busy}>Refresh</Button>} />

      {/* Assignment panels */}
      <div className="grid md:grid-cols-3 gap-3 mb-5">
        <Card className="p-4">
          <div className="text-xs font-bold text-slate-500 uppercase mb-2">RM → Team Leader</div>
          <div className="flex flex-col gap-2">
            <Picker label="Regional Manager" options={all.regional_managers} value={rmTl.rm} onChange={v => setRmTl(s => ({ ...s, rm: v }))} />
            <Picker label="Team Leader" options={all.team_leaders} value={rmTl.tl} onChange={v => setRmTl(s => ({ ...s, tl: v }))} />
            <Button className={GOLD_BTN} size="sm" onClick={doAssignRmTl}><Plus size={14} className="mr-1" /> Assign</Button>
          </div>
        </Card>
        <Card className="p-4">
          <div className="text-xs font-bold text-slate-500 uppercase mb-2">Team Leader → Distributor</div>
          <div className="flex flex-col gap-2">
            <Picker label="Team Leader" options={all.team_leaders} value={tlDist.tl} onChange={v => setTlDist(s => ({ ...s, tl: v }))} />
            <Picker label="Distributor" options={all.distributors} value={tlDist.dist} onChange={v => setTlDist(s => ({ ...s, dist: v }))} />
            <Button className={GOLD_BTN} size="sm" onClick={doAssignTlDist}><Plus size={14} className="mr-1" /> Assign</Button>
          </div>
        </Card>
        <Card className="p-4">
          <div className="text-xs font-bold text-slate-500 uppercase mb-2">Distributor → Salesperson</div>
          <div className="flex flex-col gap-2">
            <Picker label="Distributor" options={all.distributors} value={distSp.dist} onChange={v => setDistSp(s => ({ ...s, dist: v }))} />
            <Picker label="Salesperson" options={all.salespersons} value={distSp.sp} onChange={v => setDistSp(s => ({ ...s, sp: v }))} />
            <Button className={GOLD_BTN} size="sm" onClick={doAssignDistSp}><Plus size={14} className="mr-1" /> Assign</Button>
          </div>
        </Card>
      </div>

      {/* Bulk move retailers to another distributor */}
      <Card className="p-4 mb-5">
        <div className="flex items-center justify-between flex-wrap gap-2 mb-3">
          <div className="text-xs font-bold text-slate-500 uppercase flex items-center gap-1">
            <Store size={14} className="text-[#a67c00]" /> Bulk Move Retailers
          </div>
          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-500">{selectedRetailerIds.length} selected →</span>
            <Picker label="Target Distributor" options={all.distributors} value={moveDist} onChange={setMoveDist} />
            <Button className={GOLD_BTN} size="sm" onClick={doBulkMove} disabled={selectedRetailerIds.length === 0 || !moveDist}>
              Move
            </Button>
          </div>
        </div>
        {retailers.length === 0 ? (
          <div className="text-xs text-slate-400">No retailers yet.</div>
        ) : (
          <div className="grid sm:grid-cols-2 md:grid-cols-3 gap-2 max-h-64 overflow-y-auto">
            {retailers.map(r => (
              <label key={r.id} className="flex items-center gap-2 text-sm border border-slate-200 rounded-md px-2 py-1.5 cursor-pointer hover:bg-amber-50/40">
                <input type="checkbox" checked={!!selRet[r.id]}
                  onChange={e => setSelRet(s => ({ ...s, [r.id]: e.target.checked }))} />
                <span className="truncate">{r.name}</span>
                <span className="ml-auto text-[10px] text-slate-400 truncate">{r.distributor_name || ""}</span>
              </label>
            ))}
          </div>
        )}
      </Card>

      {/* Tree */}
      <Card className="p-4">
        <div className="flex items-center gap-2 mb-3">
          <Network size={16} className="text-[#a67c00]" />
          <h3 className="font-bold text-slate-900">Hierarchy Tree</h3>
        </div>

        {(data?.tree || []).map(rm => (
          <div key={rm.id} className="mb-4">
            <div className="flex items-center gap-2 font-bold text-slate-900">
              <span className="px-2 py-0.5 rounded bg-purple-100 text-purple-700 text-xs">RM</span> {rm.name}
            </div>
            {(rm.team_leaders || []).length === 0 && <div className="ml-4 text-xs text-slate-400">No team leaders</div>}
            {(rm.team_leaders || []).map(tl => (
              <div key={tl.id} className="ml-4 mt-2 border-l-2 border-purple-200 pl-3">
                <div className="flex items-center gap-2 font-semibold text-slate-800 text-sm">
                  <span className="px-1.5 py-0.5 rounded bg-indigo-100 text-indigo-700 text-[10px]">TL</span> {tl.name}
                </div>
                {(tl.distributors || []).map(d => renderDist(d, tl.id))}
              </div>
            ))}
          </div>
        ))}

        {(data?.unassigned_team_leaders || []).length > 0 && (
          <div className="mt-4 pt-3 border-t">
            <div className="text-xs font-bold text-slate-500 uppercase mb-2 flex items-center gap-1"><ChevronRight size={12} /> Team Leaders (no RM)</div>
            {data.unassigned_team_leaders.map(tl => (
              <div key={tl.id} className="ml-2 mt-2">
                <div className="flex items-center gap-2 font-semibold text-slate-800 text-sm">
                  <span className="px-1.5 py-0.5 rounded bg-indigo-100 text-indigo-700 text-[10px]">TL</span> {tl.name}
                </div>
                {(tl.distributors || []).map(d => renderDist(d, tl.id))}
              </div>
            ))}
          </div>
        )}

        {(data?.unassigned_distributors || []).length > 0 && (
          <div className="mt-4 pt-3 border-t">
            <div className="text-xs font-bold text-slate-500 uppercase mb-2 flex items-center gap-1"><ChevronRight size={12} /> Distributors (no Team Leader)</div>
            {data.unassigned_distributors.map(d => renderDist(d, null))}
          </div>
        )}
      </Card>
    </div>
  );
}

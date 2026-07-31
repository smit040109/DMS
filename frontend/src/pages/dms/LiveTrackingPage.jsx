import React, { useEffect, useMemo, useState, useCallback, useRef } from "react";
import { MapContainer, TileLayer, Marker, Popup, Polyline, useMap } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { dms, niceDate } from "./api";
import { PageHeader } from "./OwnerPages";
import { useAuth } from "@/context/AuthContext";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { toast } from "sonner";
import { Users, Store, Handshake, MapPin, LogIn, LogOut, Clock, Route as RouteIcon, RefreshCw, Calendar } from "lucide-react";

// ── Fix default marker icons (leaflet + webpack) ────────────────────────
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
  iconUrl:       "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
  shadowUrl:     "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
});

// Custom icons using divIcon (color coded)
const makeIcon = (color, glyph) => L.divIcon({
  className: "",
  html: `<div style="background:${color};width:28px;height:28px;border-radius:50% 50% 50% 0;transform:rotate(-45deg);border:2px solid white;box-shadow:0 2px 6px rgba(0,0,0,.3);display:flex;align-items:center;justify-content:center;">
    <span style="transform:rotate(45deg);color:white;font-size:12px;font-weight:700;">${glyph}</span>
  </div>`,
  iconSize: [28, 28],
  iconAnchor: [14, 28],
  popupAnchor: [0, -28],
});

const ICON_DIST = makeIcon("#0f766e", "D");     // teal
const ICON_RET  = makeIcon("#f59e0b", "R");     // amber
const ICON_SP   = makeIcon("#e11d48", "S");     // rose
const ICON_SP_OFF = makeIcon("#64748b", "S");   // slate for offline

// India centre default
const INDIA_CENTER = [22.5, 79.5];

// Helper — recentre the map when a salesperson is picked
function FlyTo({ target }) {
  const map = useMap();
  useEffect(() => {
    if (target && target[0] && target[1]) {
      map.flyTo(target, 12, { duration: 0.6 });
    }
  }, [target, map]);
  return null;
}

// ============================================================================
// Owner / TL / RM — Live Tracking Map
// ============================================================================
export function LiveTrackingPage() {
  const { user } = useAuth();
  const [live, setLive] = useState({ salespersons: [], distributors: [], retailers: [] });
  const [selectedSp, setSelectedSp] = useState(null);
  const [selectedDate, setSelectedDate] = useState(() => new Date().toISOString().slice(0, 10));
  const [detail, setDetail] = useState(null); // { punch, route, distance_km, visited, working_hours }
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [flyTarget, setFlyTarget] = useState(null);
  const timerRef = useRef();

  const refresh = useCallback(async () => {
    try {
      const d = await dms.trackingLive();
      setLive(d);
    } catch (e) {
      // eslint-disable-next-line no-console
      console.warn("tracking/live failed", e);
    } finally {
      setLoading(false);
    }
  }, []);

  // Poll live positions every 30 seconds
  useEffect(() => {
    refresh();
    timerRef.current = setInterval(refresh, 30000);
    return () => clearInterval(timerRef.current);
  }, [refresh]);

  // Load salesperson detail on select / date change
  useEffect(() => {
    if (!selectedSp) { setDetail(null); setHistory([]); return; }
    let cancelled = false;
    (async () => {
      try {
        const [d, h] = await Promise.all([
          dms.trackingSalesperson(selectedSp, selectedDate),
          dms.trackingHistory(selectedSp, 30),
        ]);
        if (cancelled) return;
        setDetail(d);
        setHistory(h.data || []);
      } catch (e) {
        if (!cancelled) toast.error(e?.response?.data?.detail || "Failed to load route");
      }
    })();
    return () => { cancelled = true; };
  }, [selectedSp, selectedDate]);

  const selectedSpMeta = useMemo(
    () => live.salespersons.find(s => s.id === selectedSp),
    [live.salespersons, selectedSp],
  );

  const polyline = useMemo(() => {
    if (!detail?.route?.length) return [];
    return detail.route.map(p => [p.lat, p.lng]);
  }, [detail]);

  const onSelectSp = (sp) => {
    setSelectedSp(sp.id);
    if (sp.lat && sp.lng) setFlyTarget([sp.lat, sp.lng]);
  };

  return (
    <div>
      <PageHeader
        title="Live Tracking"
        subtitle={
          user?.role === "team_leader"
            ? "Your team on the field — live positions and daily routes"
            : user?.role === "regional_manager"
              ? "Regional field activity — live positions and daily routes"
              : "Real-time positions of salespersons, distributors and retailers"
        }
        action={
          <Button variant="outline" onClick={refresh} data-testid="refresh-live">
            <RefreshCw size={14} className="mr-2" /> Refresh
          </Button>
        }
      />

      <div className="grid lg:grid-cols-[320px_1fr] gap-4">
        {/* Left side — salespersons list + selected detail */}
        <div className="space-y-4">
          <Card className="p-3">
            <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">
              Salespersons ({live.salespersons.length})
            </div>
            {live.salespersons.length === 0 && (
              <div className="text-xs text-slate-400 py-6 text-center">No salespersons visible</div>
            )}
            <div className="space-y-1.5 max-h-72 overflow-y-auto">
              {live.salespersons.map(sp => (
                <button
                  key={sp.id}
                  onClick={() => onSelectSp(sp)}
                  className={`w-full text-left px-3 py-2 rounded-lg text-sm flex items-center gap-2 ${selectedSp === sp.id ? "bg-[#faf6e6] border border-[#c9a227]" : "hover:bg-slate-50 border border-transparent"}`}
                  data-testid={`sp-item-${sp.id}`}
                >
                  <span className={`h-2 w-2 rounded-full ${sp.online ? "bg-emerald-500 animate-pulse" : "bg-slate-300"}`} />
                  <span className="flex-1 truncate">{sp.name}</span>
                  {sp.lat != null && <MapPin size={12} className="text-slate-400" />}
                </button>
              ))}
            </div>
          </Card>

          {selectedSpMeta && (
            <Card className="p-4 space-y-3">
              <div className="flex items-start justify-between">
                <div>
                  <div className="font-semibold text-slate-900">{selectedSpMeta.name}</div>
                  <div className="text-xs text-slate-500">{selectedSpMeta.phone}</div>
                </div>
                <span className={`text-[11px] font-semibold px-2 py-0.5 rounded-full ${selectedSpMeta.online ? "bg-emerald-100 text-emerald-800" : "bg-slate-100 text-slate-600"}`}>
                  {selectedSpMeta.online ? "Online" : "Offline"}
                </span>
              </div>

              {/* Date pick */}
              <div>
                <label className="text-[11px] uppercase tracking-wider text-slate-500 font-semibold">Route for</label>
                <div className="flex gap-2 mt-1">
                  <Input
                    type="date"
                    value={selectedDate}
                    onChange={e => setSelectedDate(e.target.value)}
                    data-testid="route-date"
                  />
                  <Select value={selectedDate} onValueChange={setSelectedDate}>
                    <SelectTrigger className="w-28"><SelectValue placeholder="Quick" /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value={new Date().toISOString().slice(0,10)}>Today</SelectItem>
                      <SelectItem value={new Date(Date.now() - 86400000).toISOString().slice(0,10)}>Yesterday</SelectItem>
                      <SelectItem value={new Date(Date.now() - 7*86400000).toISOString().slice(0,10)}>7 days ago</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>

              {detail && (
                <div className="space-y-2 text-sm">
                  <StatRow icon={LogIn}  label="Punch In"    value={detail.punch?.in_at ? niceDate(detail.punch.in_at) : "—"} />
                  <StatRow icon={LogOut} label="Punch Out"   value={detail.punch?.out_at ? niceDate(detail.punch.out_at) : "—"} />
                  <StatRow icon={Clock}  label="Working Hrs" value={`${detail.working_hours ?? 0} h`} />
                  <StatRow icon={RouteIcon} label="Distance" value={`${detail.distance_km ?? 0} km`} />
                  <StatRow icon={MapPin} label="Visits (Dist/Retailer)" value={`${detail.visited?.distributors?.length || 0} / ${detail.visited?.retailers?.length || 0}`} />
                  <div className="text-[11px] text-slate-500 pt-1">
                    {detail.route?.length || 0} location pings recorded
                  </div>
                </div>
              )}

              {history.length > 0 && (
                <div>
                  <div className="text-[11px] uppercase tracking-wider text-slate-500 font-semibold mb-1 mt-2">Recent 30 days</div>
                  <div className="max-h-32 overflow-y-auto text-xs space-y-1">
                    {history.map(h => (
                      <button
                        key={h.date}
                        onClick={() => setSelectedDate(h.date)}
                        className={`w-full text-left flex items-center justify-between px-2 py-1 rounded ${h.date === selectedDate ? "bg-[#faf6e6] text-[#8a6600]" : "hover:bg-slate-50"}`}
                      >
                        <span className="flex items-center gap-1.5"><Calendar size={10} /> {h.date}</span>
                        <span className="text-slate-500">{h.working_hours} h · {h.pings} pings</span>
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </Card>
          )}

          {/* Legend */}
          <Card className="p-3">
            <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">Legend</div>
            <div className="grid grid-cols-3 gap-2 text-xs">
              <LegendBadge color="#e11d48" glyph="S" label={`Salespersons (${live.salespersons.length})`} />
              <LegendBadge color="#0f766e" glyph="D" label={`Distributors (${live.distributors.length})`} />
              <LegendBadge color="#f59e0b" glyph="R" label={`Retailers (${live.retailers.length})`} />
            </div>
          </Card>
        </div>

        {/* Right side — map */}
        <Card className="overflow-hidden" style={{ height: "calc(100vh - 220px)", minHeight: 500 }}>
          {loading && (
            <div className="h-full flex items-center justify-center text-sm text-slate-400">Loading map…</div>
          )}
          {!loading && (
            <MapContainer center={INDIA_CENTER} zoom={5} style={{ height: "100%", width: "100%" }} scrollWheelZoom>
              <TileLayer
                attribution='&copy; <a href="https://www.openstreetmap.org/">OpenStreetMap</a> contributors'
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
              />
              <FlyTo target={flyTarget} />

              {/* Distributors */}
              {live.distributors.filter(d => d.lat && d.lng).map(d => (
                <Marker key={`d-${d.id}`} position={[d.lat, d.lng]} icon={ICON_DIST}>
                  <Popup>
                    <b>{d.name}</b><br/>
                    <span className="text-xs">Distributor · {d.region}</span><br/>
                    <span className="text-xs">{d.address}</span>
                  </Popup>
                </Marker>
              ))}

              {/* Retailers */}
              {live.retailers.filter(r => r.lat && r.lng).map(r => (
                <Marker key={`r-${r.id}`} position={[r.lat, r.lng]} icon={ICON_RET}>
                  <Popup>
                    <b>{r.name}</b><br/>
                    <span className="text-xs">Retailer</span><br/>
                    <span className="text-xs">{r.address}</span>
                  </Popup>
                </Marker>
              ))}

              {/* Salespersons — live positions */}
              {live.salespersons.filter(s => s.lat && s.lng).map(s => (
                <Marker key={`s-${s.id}`} position={[s.lat, s.lng]} icon={s.online ? ICON_SP : ICON_SP_OFF}
                        eventHandlers={{ click: () => setSelectedSp(s.id) }}>
                  <Popup>
                    <b>{s.name}</b><br/>
                    <span className="text-xs">Salesperson</span><br/>
                    <span className={`text-xs ${s.online ? "text-emerald-700" : "text-slate-500"}`}>
                      {s.online ? "● Online" : "○ Offline"}
                    </span>
                    {s.last_ping_at && <><br/><span className="text-[11px] text-slate-500">Last: {niceDate(s.last_ping_at)}</span></>}
                  </Popup>
                </Marker>
              ))}

              {/* Route polyline for selected salesperson */}
              {polyline.length > 1 && (
                <Polyline positions={polyline} color="#e11d48" weight={4} opacity={0.85} />
              )}
            </MapContainer>
          )}
        </Card>
      </div>
    </div>
  );
}

// ── Small UI helpers ────────────────────────────────────────────────
function StatRow({ icon: Icon, label, value }) {
  return (
    <div className="flex items-center justify-between text-sm">
      <span className="flex items-center gap-2 text-slate-600"><Icon size={14} className="text-slate-400" /> {label}</span>
      <span className="font-semibold text-slate-900">{value}</span>
    </div>
  );
}

function LegendBadge({ color, glyph, label }) {
  return (
    <div className="flex items-center gap-2">
      <div style={{ background: color, transform: "rotate(-45deg)" }}
           className="h-4 w-4 rounded-full rounded-bl-none border border-white shadow flex items-center justify-center">
        <span style={{ transform: "rotate(45deg)", color: "white", fontSize: 8, fontWeight: 700 }}>{glyph}</span>
      </div>
      <span className="text-slate-700">{label}</span>
    </div>
  );
}

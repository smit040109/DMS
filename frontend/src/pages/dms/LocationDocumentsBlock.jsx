import React, { useState, useRef } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { toast } from "sonner";
import { MapPin, Upload, ExternalLink, X, Loader2, FileText } from "lucide-react";

/**
 * Reusable Location + Documents block for creating Distributor / Retailer.
 *
 * Props:
 *   lat, lng, locationLink               → controlled values
 *   onLat, onLng, onLocationLink         → setters
 *   documents (array of {name, url, size, type})
 *   onDocuments                          → setter
 *   maxDocs (default 3)
 *   maxSizeMB (default 20)
 *   helpText                             → optional help note
 */
export default function LocationDocumentsBlock({
  lat, lng, locationLink,
  onLat, onLng, onLocationLink,
  documents = [],
  onDocuments,
  maxDocs = 3,
  maxSizeMB = 20,
  helpText,
}) {
  const [locating, setLocating] = useState(false);
  const fileInputRef = useRef(null);

  const useMyLocation = () => {
    if (!("geolocation" in navigator)) {
      toast.error("Geolocation not supported in this browser");
      return;
    }
    setLocating(true);
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        const la = pos.coords.latitude.toFixed(6);
        const ln = pos.coords.longitude.toFixed(6);
        onLat?.(la);
        onLng?.(ln);
        onLocationLink?.(`https://maps.google.com/?q=${la},${ln}`);
        setLocating(false);
        toast.success("Location captured");
      },
      (err) => {
        setLocating(false);
        toast.error(err.message || "Could not get location — please enable location permissions");
      },
      { enableHighAccuracy: true, timeout: 15000 }
    );
  };

  const mapsLink =
    locationLink ||
    (lat && lng ? `https://maps.google.com/?q=${lat},${lng}` : "");

  const handleFiles = (files) => {
    const arr = Array.from(files);
    const remaining = maxDocs - documents.length;
    if (remaining <= 0) {
      toast.error(`Only ${maxDocs} documents allowed`);
      return;
    }
    const toAdd = arr.slice(0, remaining);
    toAdd.forEach((f) => {
      if (f.size > maxSizeMB * 1024 * 1024) {
        toast.error(`"${f.name}" is larger than ${maxSizeMB} MB`);
        return;
      }
      const reader = new FileReader();
      reader.onload = () => {
        const doc = {
          name: f.name,
          type: f.type || "application/octet-stream",
          size: f.size,
          url: reader.result, // data URL — persisted as-is on the backend
          uploaded_at: new Date().toISOString(),
        };
        onDocuments?.([...(documents || []), doc]);
      };
      reader.onerror = () => toast.error(`Failed to read "${f.name}"`);
      reader.readAsDataURL(f);
    });
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  const removeDoc = (idx) => {
    const next = [...documents];
    next.splice(idx, 1);
    onDocuments?.(next);
  };

  const fmtSize = (bytes) => {
    if (!bytes) return "";
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / 1024 / 1024).toFixed(2)} MB`;
  };

  return (
    <div className="space-y-4 rounded-xl border border-[#c9a227]/30 bg-[#faf6e6]/40 p-4">
      <div className="flex items-center gap-2">
        <MapPin size={16} className="text-[#a67c00]" />
        <div className="font-display font-bold text-slate-900">Location & Documents</div>
      </div>

      {/* GPS */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 items-end">
        <div className="col-span-2 md:col-span-1">
          <Label>Latitude</Label>
          <Input
            value={lat || ""}
            onChange={(e) => onLat?.(e.target.value)}
            placeholder="e.g. 28.6139"
            data-testid="loc-lat-input"
          />
        </div>
        <div className="col-span-2 md:col-span-1">
          <Label>Longitude</Label>
          <Input
            value={lng || ""}
            onChange={(e) => onLng?.(e.target.value)}
            placeholder="e.g. 77.2090"
            data-testid="loc-lng-input"
          />
        </div>
        <div className="col-span-2 md:col-span-2 flex gap-2">
          <Button
            type="button"
            onClick={useMyLocation}
            disabled={locating}
            variant="outline"
            className="flex-1 border-[#c9a227] text-[#8a6600] hover:bg-[#faf6e6]"
            data-testid="use-my-location-btn"
          >
            {locating ? (
              <><Loader2 size={14} className="mr-2 animate-spin" /> Locating…</>
            ) : (
              <><MapPin size={14} className="mr-2" /> Use my current location</>
            )}
          </Button>
          {mapsLink && (
            <a
              href={mapsLink}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-1.5 px-3 py-2 text-sm rounded-lg border border-slate-300 bg-white text-slate-700 hover:bg-slate-50"
            >
              <ExternalLink size={14} /> View on Map
            </a>
          )}
        </div>
      </div>

      <div className="text-xs text-slate-500">
        💡 If exact location isn't picked up, ask the distributor to open their login and paste Latitude &
        Longitude here — the map link will update automatically.
      </div>

      {/* Documents */}
      <div>
        <div className="flex items-center justify-between mb-2">
          <Label>Documents <span className="text-slate-400 font-normal">({documents.length}/{maxDocs} · up to {maxSizeMB} MB each)</span></Label>
          <div>
            <input
              ref={fileInputRef}
              type="file"
              multiple
              className="hidden"
              onChange={(e) => handleFiles(e.target.files)}
              accept="image/*,application/pdf,.doc,.docx,.xls,.xlsx"
              data-testid="loc-file-input"
            />
            <Button
              type="button"
              size="sm"
              variant="outline"
              onClick={() => fileInputRef.current?.click()}
              disabled={documents.length >= maxDocs}
              className="border-[#c9a227] text-[#8a6600] hover:bg-[#faf6e6]"
              data-testid="loc-upload-btn"
            >
              <Upload size={13} className="mr-1.5" /> Upload
            </Button>
          </div>
        </div>

        {documents.length === 0 ? (
          <div className="rounded-lg border border-dashed border-slate-300 bg-white p-4 text-center text-xs text-slate-500">
            Attach GST certificate, PAN card, shop license, ID proof, etc. (Max {maxDocs} files · {maxSizeMB} MB each)
          </div>
        ) : (
          <div className="space-y-2">
            {documents.map((d, i) => (
              <div key={i} className="flex items-center gap-2.5 rounded-lg border border-slate-200 bg-white px-3 py-2">
                <FileText size={16} className="text-[#a67c00] shrink-0" />
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-medium text-slate-900 truncate">{d.name}</div>
                  <div className="text-[11px] text-slate-500">{fmtSize(d.size)} · {d.type?.split("/")[1] || "file"}</div>
                </div>
                {d.url && (
                  <a href={d.url} target="_blank" rel="noreferrer" download={d.name} className="p-1 rounded hover:bg-slate-100" title="View / download">
                    <ExternalLink size={14} className="text-slate-500" />
                  </a>
                )}
                <button type="button" onClick={() => removeDoc(i)} className="p-1 rounded hover:bg-rose-50 text-rose-600" title="Remove">
                  <X size={14} />
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      {helpText && <div className="text-xs text-slate-500 mt-1">{helpText}</div>}
    </div>
  );
}

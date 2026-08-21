import React, { useEffect, useRef, useState } from "react";
import { Html5Qrcode } from "html5-qrcode";
import { X, Camera, AlertTriangle } from "lucide-react";

/**
 * Mobile-friendly live camera QR/barcode scanner (modal).
 *
 * Props:
 *   open       : boolean — whether the modal is shown
 *   onClose    : () => void
 *   onResult   : (decodedText: string) => void  — called once on first decode
 *   title      : optional heading
 *
 * Uses the rear ("environment") camera when available and falls back with a
 * clear message when camera permission is denied / unavailable.
 */
export default function QrScanner({ open, onClose, onResult, title = "Scan Coupon QR" }) {
  const regionId = useRef("qr-region-" + Math.random().toString(36).slice(2, 9));
  const scannerRef = useRef(null);
  const handledRef = useRef(false);
  const [error, setError] = useState("");
  const [starting, setStarting] = useState(true);

  useEffect(() => {
    if (!open) return;
    handledRef.current = false;
    setError("");
    setStarting(true);

    let cancelled = false;
    const html5 = new Html5Qrcode(regionId.current, { verbose: false });
    scannerRef.current = html5;

    const config = { fps: 10, qrbox: { width: 240, height: 240 }, aspectRatio: 1.0 };

    const onSuccess = (decodedText) => {
      if (handledRef.current) return;
      handledRef.current = true;
      // stop then bubble up
      html5.stop().catch(() => {}).finally(() => {
        onResult && onResult(decodedText);
      });
    };

    html5
      .start({ facingMode: "environment" }, config, onSuccess, () => {})
      .then(() => {
        if (cancelled) html5.stop().catch(() => {});
        setStarting(false);
      })
      .catch((err) => {
        // retry with any available camera before failing
        Html5Qrcode.getCameras()
          .then((cams) => {
            if (cams && cams.length) {
              return html5.start({ deviceId: { exact: cams[0].id } }, config, onSuccess, () => {});
            }
            throw err;
          })
          .then(() => setStarting(false))
          .catch(() => {
            setStarting(false);
            setError(
              "Camera unavailable or permission denied. Please allow camera access, or paste/enter the coupon code manually."
            );
          });
      });

    return () => {
      cancelled = true;
      const s = scannerRef.current;
      if (s) {
        s.stop().then(() => s.clear()).catch(() => {
          try { s.clear(); } catch (e) { /* noop */ }
        });
      }
    };
  }, [open]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/70 p-4" data-testid="qr-scanner-modal">
      <div className="w-full max-w-sm rounded-2xl bg-white shadow-2xl overflow-hidden">
        <div className="flex items-center gap-2 px-4 py-3 bg-slate-900 text-white">
          <Camera size={18} />
          <span className="font-semibold text-sm">{title}</span>
          <button className="ml-auto p-1 rounded hover:bg-white/10" onClick={onClose} data-testid="qr-scanner-close">
            <X size={18} />
          </button>
        </div>

        <div className="p-4">
          {error ? (
            <div className="flex items-start gap-2 text-sm text-rose-700 bg-rose-50 border border-rose-200 rounded-lg p-3" data-testid="qr-scanner-error">
              <AlertTriangle size={18} className="mt-0.5 shrink-0" />
              <span>{error}</span>
            </div>
          ) : (
            <>
              <div id={regionId.current} className="w-full rounded-lg overflow-hidden bg-black min-h-[240px]" />
              <p className="text-center text-xs text-slate-500 mt-3">
                {starting ? "Starting camera…" : "Point the camera at the coupon QR code"}
              </p>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

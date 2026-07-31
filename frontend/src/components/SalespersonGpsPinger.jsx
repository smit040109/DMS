import { useEffect, useRef } from "react";
import { useAuth } from "@/context/AuthContext";
import { dms } from "@/pages/dms/api";

/**
 * SalespersonGpsPinger — mounts inside DmsShell.
 * If the current user is a salesperson AND the browser supports geolocation,
 * post the location every 60s so the Owner / TL / RM see them live on the map.
 * Silent on error (no toasts, no console spam).
 */
export default function SalespersonGpsPinger() {
  const { user, impersonation } = useAuth();
  const timerRef = useRef();

  useEffect(() => {
    // Only ping when the *effective* user is a salesperson
    if (!user || user.role !== "salesperson") return;
    // Don't ping while owner is impersonating (their real position would leak)
    if (impersonation) return;
    if (!("geolocation" in navigator)) return;

    let cancelled = false;
    const send = () => {
      navigator.geolocation.getCurrentPosition(
        (pos) => {
          if (cancelled) return;
          const { latitude, longitude, accuracy, speed } = pos.coords;
          dms.trackingPing({ lat: latitude, lng: longitude, accuracy, speed }).catch(() => {});
        },
        () => { /* permission denied / unavailable — ignore */ },
        { enableHighAccuracy: false, maximumAge: 30000, timeout: 8000 },
      );
    };

    // Send immediately on login, then every 60s
    send();
    timerRef.current = setInterval(send, 60_000);
    return () => {
      cancelled = true;
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [user, impersonation]);

  return null;
}

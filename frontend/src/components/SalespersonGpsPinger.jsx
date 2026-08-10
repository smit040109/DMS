import { useEffect, useRef } from "react";
import { useAuth } from "@/context/AuthContext";
import { dms } from "@/pages/dms/api";

/**
 * FieldGpsPinger — mounts inside DmsShell.
 * For EVERY role except the Company Owner: while the user is currently
 * PUNCHED IN, post the location every 60s so the Owner / TL / RM can see them
 * live on the map. Stops pinging once they punch out. Silent on error.
 */
export default function SalespersonGpsPinger() {
  const { user, impersonation } = useAuth();
  const timerRef = useRef();

  useEffect(() => {
    // Only field staff are GPS-tracked. Owner is office-only; distributors and
    // retailers do not punch in/out and are never tracked.
    const FIELD_ROLES = ["salesperson", "team_leader", "regional_manager"];
    if (!user || !FIELD_ROLES.includes(user.role)) return;
    // Don't ping while owner is impersonating (their real position would leak)
    if (impersonation) return;
    if (!("geolocation" in navigator)) return;

    let cancelled = false;
    const send = async () => {
      // Only track between punch-in and punch-out
      let punchedIn = false;
      try {
        const p = await dms.punchToday();
        punchedIn = !!p?.punched_in;
      } catch { punchedIn = false; }
      if (!punchedIn || cancelled) return;
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

    send();
    timerRef.current = setInterval(send, 60_000);
    return () => {
      cancelled = true;
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [user, impersonation]);

  return null;
}

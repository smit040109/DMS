import axios from "axios";

const BASE = process.env.REACT_APP_BACKEND_URL;
export const API_URL = `${BASE}/api`;

const api = axios.create({
  baseURL: API_URL,
  // NOTE: We use JWT Bearer tokens via the Authorization header (see interceptor
  // below), not cookies. `withCredentials: true` is intentionally OFF so that
  // (a) the browser does not enforce the "no wildcard CORS with credentials" rule
  //     when the app is deployed on a different subdomain than the backend, and
  // (b) preflight requests remain simple.
  withCredentials: false,
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("go_oil_token");
  if (token) {
    config.headers = config.headers || {};
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export function formatApiErrorDetail(detail) {
  if (detail == null) return "Something went wrong. Please try again.";
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail))
    return detail
      .map((e) => (e && typeof e.msg === "string" ? e.msg : JSON.stringify(e)))
      .filter(Boolean)
      .join(" ");
  if (detail && typeof detail.msg === "string") return detail.msg;
  return String(detail);
}

export default api;

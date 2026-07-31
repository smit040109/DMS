import api from "@/lib/api";

export const dms = {
  // notifications
  notifications: () => api.get("/dms/notifications").then(r => r.data),
  markRead: (id) => api.post(`/dms/notifications/${id}/read`).then(r => r.data),
  markAllRead: () => api.post(`/dms/notifications/read-all`).then(r => r.data),

  // categories
  listCategories: () => api.get("/dms/categories").then(r => r.data),
  createCategory: (body) => api.post("/dms/categories", body).then(r => r.data),
  updateCategory: (id, body) => api.put(`/dms/categories/${id}`, body).then(r => r.data),
  deleteCategory: (id) => api.delete(`/dms/categories/${id}`).then(r => r.data),

  // products
  listProducts: () => api.get("/dms/products").then(r => r.data),
  createProduct: (body) => api.post("/dms/products", body).then(r => r.data),
  updateProduct: (id, body) => api.put(`/dms/products/${id}`, body).then(r => r.data),
  priceHistory: (id) => api.get(`/dms/products/${id}/price-history`).then(r => r.data),

  // owner inventory
  ownerInventory: () => api.get("/dms/owner/inventory").then(r => r.data),
  ownerInvAdjust: (body) => api.post("/dms/owner/inventory/adjust", body).then(r => r.data),

  // distributors
  listDistributors: () => api.get("/dms/distributors").then(r => r.data),
  createDistributor: (body) => api.post("/dms/distributors", body).then(r => r.data),
  getDistributor: (id) => api.get(`/dms/distributors/${id}`).then(r => r.data),
  updateDistributor: (id, body) => api.put(`/dms/distributors/${id}`, body).then(r => r.data),
  getDistVisibility: (id) => api.get(`/dms/distributors/${id}/visibility`).then(r => r.data),
  setDistVisibility: (id, body) => api.put(`/dms/distributors/${id}/visibility`, body).then(r => r.data),

  // distributor side
  browseProducts: () => api.get("/dms/distributor/browse").then(r => r.data),

  // primary orders
  placeOrder: (body) => api.post("/dms/primary-orders", body).then(r => r.data),
  listOrders: (status) => api.get("/dms/primary-orders", { params: status ? { status } : {} }).then(r => r.data),
  getOrder: (id) => api.get(`/dms/primary-orders/${id}`).then(r => r.data),
  fulfillLine: (oid, body) => api.post(`/dms/primary-orders/${oid}/fulfill-line`, body).then(r => r.data),
  markReady: (oid) => api.post(`/dms/primary-orders/${oid}/ready`).then(r => r.data),
  markReceived: (oid) => api.post(`/dms/primary-orders/${oid}/receive`).then(r => r.data),

  // attachments
  listAttachments: (refId) => api.get(`/dms/attachments`, { params: { reference_id: refId } }).then(r => r.data),
  addAttachment: (body) => api.post(`/dms/attachments`, body).then(r => r.data),

  // primary ledger
  primaryLedger: (distributor_id) => api.get(`/dms/ledger/primary`, { params: distributor_id ? { distributor_id } : {} }).then(r => r.data),
  recordPrimaryPayment: (body) => api.post(`/dms/ledger/primary/payment`, body).then(r => r.data),

  // dashboards
  ownerDashboard: () => api.get("/dms/dashboard/owner").then(r => r.data),
  distributorDashboard: () => api.get("/dms/dashboard/distributor").then(r => r.data),
};

export function inr(n) {
  const v = Number(n || 0);
  return "\u20B9 " + v.toLocaleString("en-IN", { maximumFractionDigits: 0 });
}

export function niceDate(iso) {
  if (!iso) return "—";
  try {
    const d = new Date(iso);
    return d.toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "2-digit" }) +
           " " + d.toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" });
  } catch { return iso; }
}

export function statusPill(status) {
  const map = {
    pending: "bg-amber-100 text-amber-800 border-amber-200",
    partially_fulfilled: "bg-blue-100 text-blue-800 border-blue-200",
    fulfilled: "bg-emerald-100 text-emerald-800 border-emerald-200",
    ready_to_go: "bg-indigo-100 text-indigo-800 border-indigo-200",
    received: "bg-green-100 text-green-800 border-green-200",
  };
  return map[status] || "bg-slate-100 text-slate-700 border-slate-200";
}

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

  // retailer prices (owner/TL sets distributor's selling price to retailer)
  getRetailerPrices: (did) => api.get(`/dms/distributors/${did}/retailer-prices`).then(r => r.data),
  setRetailerPrice: (did, body) => api.put(`/dms/distributors/${did}/retailer-prices`, body).then(r => r.data),

  // distributor browse
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

  // === Iteration 2 ===

  // retailers
  listRetailers: (params = {}) => api.get("/dms/retailers", { params }).then(r => r.data),
  createRetailer: (body) => api.post("/dms/retailers", body).then(r => r.data),
  getRetailer: (id) => api.get(`/dms/retailers/${id}`).then(r => r.data),
  updateRetailer: (id, body) => api.put(`/dms/retailers/${id}`, body).then(r => r.data),
  getRetVisibility: (id) => api.get(`/dms/retailers/${id}/visibility`).then(r => r.data),
  setRetVisibility: (id, body) => api.put(`/dms/retailers/${id}/visibility`, body).then(r => r.data),
  getRetMode: (id) => api.get(`/dms/retailers/${id}/selling-mode`).then(r => r.data),
  setRetMode: (id, body) => api.put(`/dms/retailers/${id}/selling-mode`, body).then(r => r.data),

  // retailer browse & order
  retailerBrowse: (retailer_id) => api.get("/dms/retailer/browse", { params: retailer_id ? { retailer_id } : {} }).then(r => r.data),
  placeSecondaryOrder: (body) => api.post("/dms/secondary-orders", body).then(r => r.data),
  listSecondaryOrders: (status) => api.get("/dms/secondary-orders", { params: status ? { status } : {} }).then(r => r.data),
  getSecondaryOrder: (id) => api.get(`/dms/secondary-orders/${id}`).then(r => r.data),
  dispatchSecondary: (oid, body) => api.post(`/dms/secondary-orders/${oid}/dispatch`, body).then(r => r.data),
  // Phase 1 additions:
  cancelSecondaryOrder: (oid, reason) => api.post(`/dms/secondary-orders/${oid}/cancel`, { reason }).then(r => r.data),
  updateSecondaryOrder: (oid, body) => api.put(`/dms/secondary-orders/${oid}`, body).then(r => r.data),

  // secondary ledger
  secondaryLedger: (retailer_id) => api.get(`/dms/ledger/secondary`, { params: retailer_id ? { retailer_id } : {} }).then(r => r.data),
  recordSecondaryPayment: (body) => api.post(`/dms/ledger/secondary/payment`, body).then(r => r.data),

  // assignments
  listTlDistributors: (params = {}) => api.get("/dms/assignments/tl-distributors", { params }).then(r => r.data),
  assignTlDist: (body) => api.post("/dms/assignments/tl-distributors", body).then(r => r.data),
  unassignTlDist: (tl, did) => api.delete("/dms/assignments/tl-distributors", { params: { team_leader_id: tl, distributor_id: did } }).then(r => r.data),
  listSpDistributors: (params = {}) => api.get("/dms/assignments/sp-distributors", { params }).then(r => r.data),
  assignSpDist: (body) => api.post("/dms/assignments/sp-distributors", body).then(r => r.data),
  unassignSpDist: (sp, did) => api.delete("/dms/assignments/sp-distributors", { params: { salesperson_id: sp, distributor_id: did } }).then(r => r.data),
  listRmTls: (params = {}) => api.get("/dms/assignments/rm-tls", { params }).then(r => r.data),
  assignRmTl: (body) => api.post("/dms/assignments/rm-tls", body).then(r => r.data),

  // users
  listUsers: (role) => api.get("/dms/users", { params: role ? { role } : {} }).then(r => r.data),

  // punch
  punchIn: (body) => api.post("/dms/punch/in", body).then(r => r.data),
  punchOut: (body) => api.post("/dms/punch/out", body).then(r => r.data),
  punchToday: () => api.get("/dms/punch/today").then(r => r.data),

  // dashboards
  ownerDashboard: () => api.get("/dms/dashboard/owner").then(r => r.data),
  distributorDashboard: () => api.get("/dms/dashboard/distributor").then(r => r.data),
  salespersonDashboard: () => api.get("/dms/dashboard/salesperson").then(r => r.data),
  teamLeaderDashboard: () => api.get("/dms/dashboard/team-leader").then(r => r.data),
  regionalManagerDashboard: () => api.get("/dms/dashboard/regional-manager").then(r => r.data),
  retailerDashboard: () => api.get("/dms/dashboard/retailer").then(r => r.data),
  superAdminDashboard: () => api.get("/dms/dashboard/super-admin").then(r => r.data),

  // super admin
  adminUsers: () => api.get("/dms/admin/users").then(r => r.data),
  impersonate: (uid) => api.post(`/dms/admin/impersonate/${uid}`).then(r => r.data),

  // owner — complete user management (Phase 1)
  ownerListUsers: (role) => api.get("/dms/owner/users", { params: role ? { role } : {} }).then(r => r.data),
  ownerCreateUser: (body) => api.post("/dms/owner/users", body).then(r => r.data),
  ownerUpdateUser: (uid, body) => api.patch(`/dms/owner/users/${uid}`, body).then(r => r.data),
  ownerResetPassword: (uid, new_password) => api.post(`/dms/owner/users/${uid}/reset-password`, { new_password }).then(r => r.data),
  ownerImpersonate: (uid) => api.post(`/dms/owner/impersonate/${uid}`).then(r => r.data),

  // live tracking (Phase 2 + 3)
  trackingPing: (body) => api.post("/dms/tracking/ping", body).then(r => r.data),
  trackingLive: () => api.get("/dms/tracking/live").then(r => r.data),
  trackingSalesperson: (sid, date) => api.get(`/dms/tracking/salesperson/${sid}`, { params: date ? { date } : {} }).then(r => r.data),
  trackingHistory: (sid, days = 30) => api.get(`/dms/tracking/salesperson/${sid}/history`, { params: { days } }).then(r => r.data),

  // Team Leader (Phase 4)
  tlDashboard: () => api.get("/dms/dashboard/team-leader").then(r => r.data),
  tlDistributors: () => api.get("/dms/tl/distributors").then(r => r.data),
  tlSalespersons: () => api.get("/dms/tl/salespersons").then(r => r.data),
  tlOrders: (params = {}) => api.get("/dms/tl/orders", { params }).then(r => r.data),
  tlRetailers: () => api.get("/dms/tl/retailers").then(r => r.data),
  tlAttendance: () => api.get("/dms/tl/attendance").then(r => r.data),
  tlPunchIn: (body) => api.post("/dms/tl/punch/in", body).then(r => r.data),
  tlPunchOut: (body) => api.post("/dms/tl/punch/out", body).then(r => r.data),

  // Owner enhancements (Phase 4)
  ownerTlPerformance: () => api.get("/dms/owner/tl-performance").then(r => r.data),
  ownerDistributorSales: (did) => api.get(`/dms/owner/distributor-sales/${did}`).then(r => r.data),

  // Coupons (Phase 7)
  ownerGenerateCoupons: (product_id, count) => api.post("/dms/owner/coupons/generate", { product_id, count }).then(r => r.data),
  ownerListCoupons: (params = {}) => api.get("/dms/owner/coupons", { params }).then(r => r.data),
  ownerCouponBatches: () => api.get("/dms/owner/coupons/batches").then(r => r.data),
  ownerCouponSummary: () => api.get("/dms/owner/coupons/reports/summary").then(r => r.data),
  ownerCouponFraud: () => api.get("/dms/owner/coupons/reports/fraud").then(r => r.data),
  ownerCouponHistory: () => api.get("/dms/owner/coupons/reports/history").then(r => r.data),
  retailerScanCoupon: (coupon_code) => api.post("/dms/retailer/coupons/scan", { coupon_code }).then(r => r.data),
  retailerCouponHistory: () => api.get("/dms/retailer/coupons/my-history").then(r => r.data),

  // Products import/export
  exportProducts: async () => {
    const r = await api.get("/dms/owner/products/export", { responseType: "blob" });
    const url = URL.createObjectURL(new Blob([r.data], { type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" }));
    const a = document.createElement("a"); a.href = url;
    a.download = `products_${new Date().toISOString().slice(0, 10)}.xlsx`;
    document.body.appendChild(a); a.click(); a.remove(); URL.revokeObjectURL(url);
  },
  importProducts: (file) => {
    const fd = new FormData(); fd.append("file", file);
    return api.post("/dms/owner/products/import", fd, { headers: { "Content-Type": "multipart/form-data" } }).then(r => r.data);
  },

  // Regional Manager (Phase 5)
  rmDashboard: () => api.get("/dms/dashboard/regional-manager").then(r => r.data),
  rmTeamLeaders: () => api.get("/dms/rm/team-leaders").then(r => r.data),
  rmDistributors: () => api.get("/dms/rm/distributors").then(r => r.data),
  rmSalespersons: () => api.get("/dms/rm/salespersons").then(r => r.data),
  rmRegionPerformance: () => api.get("/dms/rm/region-performance").then(r => r.data),

  // print
  printEbill: (id) => api.get(`/dms/print/ebill/${id}`).then(r => r.data),
  printRetailerBill: (id) => api.get(`/dms/print/retailer-bill/${id}`).then(r => r.data),

  // settings (global — GST %)
  getSettings: () => api.get("/dms/settings").then(r => r.data),
  updateSettings: (body) => api.put("/dms/settings", body).then(r => r.data),

  // Phase 2A: Financial Year close
  fyClose: (lock_date) => api.post("/dms/finance/fy-close", { lock_date }).then(r => r.data),

  // Phase 2A: Expenses
  listExpenses: (params = {}) => api.get("/dms/expenses", { params }).then(r => r.data),
  createExpense: (body) => api.post("/dms/expenses", body).then(r => r.data),
  updateExpense: (id, body) => api.put(`/dms/expenses/${id}`, body).then(r => r.data),
  deleteExpense: (id) => api.delete(`/dms/expenses/${id}`).then(r => r.data),
  expenseCategories: () => api.get("/dms/expenses/categories").then(r => r.data),

  // Phase 2A: Editable invoice/bill numbers
  updateEbillNumber: (id, ebill_no) => api.put(`/dms/ebills/${id}/number`, { ebill_no }).then(r => r.data),
  updateRetailerBillNumber: (id, bill_no) => api.put(`/dms/retailer-bills/${id}/number`, { bill_no }).then(r => r.data),

  // price circulars
  listPriceCirculars: () => api.get("/dms/price-circulars").then(r => r.data),
  getPriceCircular: (cid) => api.get(`/dms/price-circulars/${cid}`).then(r => r.data),
  createPriceCircular: (body) => api.post("/dms/price-circulars", body).then(r => r.data),
  productCircularHistory: (pid) => api.get(`/dms/products/${pid}/circular-history`).then(r => r.data),

  // coupons — retailer + distributor scan
  scanCouponRetailer: (code) => api.post("/dms/retailer/coupons/scan", { coupon_code: code }).then(r => r.data),
  scanCouponDistributor: (code) => api.post("/dms/distributor/coupons/scan", { coupon_code: code }).then(r => r.data),
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
    dispatched: "bg-indigo-100 text-indigo-800 border-indigo-200",
    completed: "bg-green-100 text-green-800 border-green-200",
    cancelled: "bg-rose-100 text-rose-800 border-rose-200",
    delivered: "bg-emerald-100 text-emerald-800 border-emerald-200",
  };
  return map[status] || "bg-slate-100 text-slate-700 border-slate-200";
}

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

  // ════════════════════════════════════════════════════════════════════════
  // GO OIL — Enterprise Coupon & Reward Engine  (/dms/coupons/*)
  // ════════════════════════════════════════════════════════════════════════
  // Batches
  cpnCreateBatch: (body) => api.post("/dms/coupons/batches", body).then(r => r.data),
  cpnListBatches: (params = {}) => api.get("/dms/coupons/batches", { params }).then(r => r.data),
  cpnGetBatch: (bid) => api.get(`/dms/coupons/batches/${bid}`).then(r => r.data),
  cpnActivateBatch: (bid) => api.post(`/dms/coupons/batches/${bid}/activate`).then(r => r.data),
  cpnMarkPrinted: (bid) => api.post(`/dms/coupons/batches/${bid}/mark-printed`).then(r => r.data),
  cpnIssueToProd: (bid) => api.post(`/dms/coupons/batches/${bid}/issue-to-production`).then(r => r.data),
  cpnDeactivateBatch: (bid) => api.post(`/dms/coupons/batches/${bid}/deactivate`).then(r => r.data),
  cpnExportPdfUrl: (bid) => (process.env.REACT_APP_BACKEND_URL || "") + `/api/dms/coupons/batches/${bid}/export-pdf`,
  cpnExportXlsxUrl: (bid) => (process.env.REACT_APP_BACKEND_URL || "") + `/api/dms/coupons/batches/${bid}/export-xlsx`,
  cpnExportPdf: async (bid, filename) => {
    const r = await api.get(`/dms/coupons/batches/${bid}/export-pdf`, { responseType: "blob" });
    const url = URL.createObjectURL(new Blob([r.data], { type: "application/pdf" }));
    const a = document.createElement("a"); a.href = url; a.download = filename || `batch_${bid}.pdf`;
    document.body.appendChild(a); a.click(); a.remove(); URL.revokeObjectURL(url);
  },
  cpnExportXlsx: async (bid, filename) => {
    const r = await api.get(`/dms/coupons/batches/${bid}/export-xlsx`, { responseType: "blob" });
    const url = URL.createObjectURL(new Blob([r.data], { type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" }));
    const a = document.createElement("a"); a.href = url; a.download = filename || `batch_${bid}.xlsx`;
    document.body.appendChild(a); a.click(); a.remove(); URL.revokeObjectURL(url);
  },
  // Coupons
  cpnListCoupons: (params = {}) => api.get("/dms/coupons", { params }).then(r => r.data),
  cpnGetCoupon: (cid) => api.get(`/dms/coupons/detail/${cid}`).then(r => r.data),
  // Sales Officer (salesperson) scan
  cpnSoRetailers: () => api.get("/dms/coupons/so/retailers").then(r => r.data),
  cpnScan: (body) => api.post("/dms/coupons/scan", body).then(r => r.data),
  // Retailer wallet
  cpnRetailerWallet: () => api.get("/dms/coupons/retailer/wallet").then(r => r.data),
  cpnRetailerTransactions: (wallet_type) => api.get("/dms/coupons/retailer/transactions", { params: wallet_type ? { wallet_type } : {} }).then(r => r.data),
  cpnRetailerCoupons: () => api.get("/dms/coupons/retailer/coupons").then(r => r.data),
  cpnRetailerRedemptions: () => api.get("/dms/coupons/retailer/redemptions").then(r => r.data),
  // Redemptions
  cpnCreateRedemption: (body) => api.post("/dms/coupons/redemptions", body).then(r => r.data),
  cpnListRedemptions: (params = {}) => api.get("/dms/coupons/redemptions", { params }).then(r => r.data),
  cpnApproveRedemption: (rid, body = {}) => api.post(`/dms/coupons/redemptions/${rid}/approve`, body).then(r => r.data),
  cpnRejectRedemption: (rid, reason) => api.post(`/dms/coupons/redemptions/${rid}/reject`, { reason }).then(r => r.data),
  // Distributor
  cpnDistSummary: () => api.get("/dms/coupons/dist/summary").then(r => r.data),
  cpnDistCreditNotes: () => api.get("/dms/coupons/dist/credit-notes").then(r => r.data),
  cpnDistDispatchAdvices: () => api.get("/dms/coupons/dist/dispatch-advices").then(r => r.data),
  // Owner — CN / DA / Audit / Reports
  cpnCreditNotes: () => api.get("/dms/coupons/credit-notes").then(r => r.data),
  cpnDispatchAdvices: () => api.get("/dms/coupons/dispatch-advices").then(r => r.data),
  cpnMarkDispatched: (id) => api.post(`/dms/coupons/dispatch-advices/${id}/mark-dispatched`).then(r => r.data),
  cpnAuditLog: (params = {}) => api.get("/dms/coupons/audit-log", { params }).then(r => r.data),
  cpnReportsSummary: () => api.get("/dms/coupons/reports/summary").then(r => r.data),
  cpnReportsSalesperson: () => api.get("/dms/coupons/reports/salesperson").then(r => r.data),
  cpnReportsFraud: () => api.get("/dms/coupons/reports/fraud").then(r => r.data),
  cpnReportsDuplicate: () => api.get("/dms/coupons/reports/duplicate-scans").then(r => r.data),
  cpnReportsWalletSummary: () => api.get("/dms/coupons/reports/wallet-summary").then(r => r.data),

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

  // Phase 2B: Cash & Bank
  listBankAccounts: () => api.get("/dms/bank-accounts").then(r => r.data),
  createBankAccount: (b) => api.post("/dms/bank-accounts", b).then(r => r.data),
  updateBankAccount: (id, b) => api.put(`/dms/bank-accounts/${id}`, b).then(r => r.data),
  deleteBankAccount: (id) => api.delete(`/dms/bank-accounts/${id}`).then(r => r.data),
  listBankTxns: (params = {}) => api.get("/dms/bank-transactions", { params }).then(r => r.data),
  createBankTxn: (b) => api.post("/dms/bank-transactions", b).then(r => r.data),
  deleteBankTxn: (id) => api.delete(`/dms/bank-transactions/${id}`).then(r => r.data),
  listCashRegister: (params = {}) => api.get("/dms/cash-register", { params }).then(r => r.data),
  createCashEntry: (b) => api.post("/dms/cash-register", b).then(r => r.data),
  deleteCashEntry: (id) => api.delete(`/dms/cash-register/${id}`).then(r => r.data),
  listCheques: (params = {}) => api.get("/dms/cheques", { params }).then(r => r.data),
  createCheque: (b) => api.post("/dms/cheques", b).then(r => r.data),
  updateCheque: (id, b) => api.put(`/dms/cheques/${id}`, b).then(r => r.data),
  deleteCheque: (id) => api.delete(`/dms/cheques/${id}`).then(r => r.data),
  listLoans: () => api.get("/dms/loan-accounts").then(r => r.data),
  createLoan: (b) => api.post("/dms/loan-accounts", b).then(r => r.data),
  updateLoan: (id, b) => api.put(`/dms/loan-accounts/${id}`, b).then(r => r.data),
  deleteLoan: (id) => api.delete(`/dms/loan-accounts/${id}`).then(r => r.data),
  listLoanTxns: (loan_id) => api.get("/dms/loan-transactions", { params: { loan_id } }).then(r => r.data),
  createLoanTxn: (b) => api.post("/dms/loan-transactions", b).then(r => r.data),

  // Phase 2B: Godowns + Stock Transfer
  listGodowns: () => api.get("/dms/godowns").then(r => r.data),
  createGodown: (b) => api.post("/dms/godowns", b).then(r => r.data),
  updateGodown: (id, b) => api.put(`/dms/godowns/${id}`, b).then(r => r.data),
  deleteGodown: (id) => api.delete(`/dms/godowns/${id}`).then(r => r.data),
  godownInventory: (id) => api.get(`/dms/godowns/${id}/inventory`).then(r => r.data),
  listStockTransfers: (params = {}) => api.get("/dms/stock-transfers", { params }).then(r => r.data),
  getStockTransfer: (id) => api.get(`/dms/stock-transfers/${id}`).then(r => r.data),
  createStockTransfer: (b) => api.post("/dms/stock-transfers", b).then(r => r.data),
  toggleStopSale: (enabled) => api.put("/dms/settings/stop-sale", { enabled }).then(r => r.data),

  // Phase 2C: Import/Export
  exportParties: () => api.get("/dms/parties/export", { responseType: "blob" }).then(r => r.data),
  importParties: (file) => {
    const fd = new FormData(); fd.append("file", file);
    return api.post("/dms/parties/import", fd, { headers: { "Content-Type": "multipart/form-data" } }).then(r => r.data);
  },
  exportSaleBills: (params = {}) => api.get("/dms/sale-bills/export", { params, responseType: "blob" }).then(r => r.data),
  exportPayments: (params = {}) => api.get("/dms/payments/export", { params, responseType: "blob" }).then(r => r.data),
  exportProducts: () => api.get("/dms/owner/products/export", { responseType: "blob" }).then(r => r.data),
  importProducts: (file) => {
    const fd = new FormData(); fd.append("file", file);
    return api.post("/dms/owner/products/import", fd, { headers: { "Content-Type": "multipart/form-data" } }).then(r => r.data);
  },

  // Phase 2C: Direct Sales
  createDirectSale: (b) => api.post("/dms/direct-sales", b).then(r => r.data),

  // Phase 2C: Documents (stubs)
  listDocuments: (params = {}) => api.get("/dms/documents", { params }).then(r => r.data),
  getDocument: (id) => api.get(`/dms/documents/${id}`).then(r => r.data),
  createDocument: (b) => api.post("/dms/documents", b).then(r => r.data),
  printDocument: (id) => api.get(`/dms/documents/${id}/print`).then(r => r.data),

  // Phase 2C: PO PDF
  printPurchaseOrder: (oid) => api.get(`/dms/print/purchase-order/${oid}`).then(r => r.data),

  // Phase 2C: Finance snapshot
  financeSnapshot: () => api.get("/dms/dashboard/finance-snapshot").then(r => r.data),

  // Phase 2C: Low-stock + reorder level
  setReorderLevel: (gid, body) => api.put(`/dms/godowns/${gid}/reorder-level`, body).then(r => r.data),
  listLowStock: () => api.get("/dms/godowns/low-stock").then(r => r.data),

  // price circulars
  listPriceCirculars: () => api.get("/dms/price-circulars").then(r => r.data),
  getPriceCircular: (cid) => api.get(`/dms/price-circulars/${cid}`).then(r => r.data),
  createPriceCircular: (body) => api.post("/dms/price-circulars", body).then(r => r.data),
  productCircularHistory: (pid) => api.get(`/dms/products/${pid}/circular-history`).then(r => r.data),

  // coupons — legacy scan endpoints REMOVED (see cpn* namespace below for the new
  // GO OIL enterprise coupon engine).

  // Phase 3: Reports
  reportsCatalog: () => api.get("/dms/reports/catalog").then(r => r.data),
  toggleReportFavorite: (rid) => api.post(`/dms/reports/favorites/toggle/${rid}`).then(r => r.data),
  runSaleReport: (params) => api.get("/dms/reports/sale/run", { params }).then(r => r.data),
  saleReportExportUrl: (params) => {
    const qs = new URLSearchParams(params || {}).toString();
    const base = (process.env.REACT_APP_BACKEND_URL || "") + "/api/dms/reports/sale/export";
    return qs ? `${base}?${qs}` : base;
  },
  runReport: (reportId, params) => api.get(`/dms/reports/${reportId}/run`, { params }).then(r => r.data),
  reportExportUrl: (reportId, params) => {
    const qs = new URLSearchParams(params || {}).toString();
    const base = (process.env.REACT_APP_BACKEND_URL || "") + `/api/dms/reports/${reportId}/export`;
    return qs ? `${base}?${qs}` : base;
  },
  listSavedFilters: (reportId) => api.get(`/dms/reports/saved-filters/${reportId}`).then(r => r.data),
  saveFilter: (reportId, payload) => api.post(`/dms/reports/saved-filters/${reportId}`, payload).then(r => r.data),
  deleteSavedFilter: (id) => api.delete(`/dms/reports/saved-filters/${id}`).then(r => r.data),
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

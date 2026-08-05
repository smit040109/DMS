import React, { Suspense } from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider, useAuth } from "@/context/AuthContext";
import { Toaster } from "@/components/ui/sonner";
import Login from "@/pages/Login";
import DmsShell from "@/pages/dms/DmsShell";
import DmsDashboardRouter from "@/pages/dms/DmsDashboardRouter";
import {
  CategoriesPage, ProductsPage, DistributorsPage, DistributorDetailPage,
  OwnerPrimaryOrdersPage, OwnerOrderDetailPage, OwnerInventoryPage, PrimaryLedgerPage,
} from "@/pages/dms/OwnerPages";
import {
  DistributorBrowsePage, DistributorOrdersPage, DistributorOrderDetailPage, DistributorStockPage,
} from "@/pages/dms/DistributorPages";
import {
  DistRetailersPage, DistRetailerDetailPage, DistSecondaryOrdersPage, DistSecondaryOrderDetailPage, SecondaryLedgerPage,
} from "@/pages/dms/DistributorSecondaryPages";
import {
  RetailerBrowsePage, RetailerOrdersPage, RetailerOrderDetailPage,
} from "@/pages/dms/RetailerPages";
import {
  SpDistributorsPage, SpRetailersPage, SpNewRetailerPage, SpNewOrderPage,
  SpOrdersPage, SpCollectPaymentPage,
  TlDistributorsPage, TlAssignmentsPage,
} from "@/pages/dms/SalesTeamPages";
import { SuperAdminUsersPage } from "@/pages/dms/SuperAdminPages";
import { OwnerUsersPage } from "@/pages/dms/OwnerUsersPage";
import { LiveTrackingPage } from "@/pages/dms/LiveTrackingPage";
import { TlDashboardPage, TlDistributorsMonitoringPage, TlSalespersonsPage, TlOrdersMonitoringPage, TlRetailersPage, TlAttendancePage } from "@/pages/dms/TeamLeaderPages";
import { OwnerTlPerformancePage, OwnerDistributorSalesListPage, OwnerDistributorSalesDetailPage } from "@/pages/dms/OwnerInsightsPages";
import { RmDashboardPage, RmTeamLeadersPage, RmRegionPerformancePage, RmDistributorsPage, RmSalespersonsPage } from "@/pages/dms/RegionalManagerPages";
import {
  OwnerCouponsPage,
  OwnerCouponBatchDetailPage,
  OwnerCouponsListPage,
  OwnerRedemptionsPage,
  OwnerCreditNotesPage,
  OwnerDispatchAdvicesPage,
  OwnerCouponReportsPage,
  OwnerCouponAuditLogPage,
  OwnerFraudDashboardPage,
  SalesOfficerScanPage,
  RetailerWalletPage,
  DistributorCouponsPage,
} from "@/pages/dms/CouponsV2";
import { PrintEbillPage, PrintRetailerBillPage, PrintPurchaseOrderPage, PrintDocumentPage } from "@/pages/dms/PrintPages";
import { ImportExportPage, DirectSalesPage, DocumentsPage } from "@/pages/dms/Phase2CPages";
import { ReportsHubPage, GenericReportPage } from "@/pages/dms/ReportsPages";
import { PriceCircularsPage, PriceCircularDetailPage, NewPriceCircularPage, SettingsPage } from "@/pages/dms/PriceCircularPages";
import { ExpensesPage } from "@/pages/dms/ExpensesPage";
import { BankAccountsPage, BankTransactionsPage, CashRegisterPage, ChequesPage, LoanAccountsPage } from "@/pages/dms/CashBankPages";
import { GodownsPage, StockTransfersPage } from "@/pages/dms/WarehousePages";

function Protected({ children }) {
  const { user } = useAuth();
  if (user === null) {
    return <div className="min-h-screen flex items-center justify-center bg-slate-50"><div className="text-sm text-slate-500">Loading…</div></div>;
  }
  if (!user) return <Navigate to="/login" replace />;
  return children;
}

function DmsPage({ Component }) {
  return (
    <Protected>
      <DmsShell>
        <Suspense fallback={<div className="p-6 text-sm text-slate-500">Loading…</div>}>
          <Component />
        </Suspense>
      </DmsShell>
    </Protected>
  );
}

// Print pages get a bare protected wrapper (no shell)
function PrintPage({ Component }) {
  return (
    <Protected>
      <Component />
    </Protected>
  );
}

function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />

      {/* Dashboard router */}
      <Route path="/dms" element={<DmsPage Component={DmsDashboardRouter} />} />

      {/* Owner */}
      <Route path="/dms/owner/categories"          element={<DmsPage Component={CategoriesPage} />} />
      <Route path="/dms/owner/products"            element={<DmsPage Component={ProductsPage} />} />
      <Route path="/dms/owner/distributors"        element={<DmsPage Component={DistributorsPage} />} />
      <Route path="/dms/owner/distributors/:id"    element={<DmsPage Component={DistributorDetailPage} />} />
      <Route path="/dms/owner/primary-orders"      element={<DmsPage Component={OwnerPrimaryOrdersPage} />} />
      <Route path="/dms/owner/primary-orders/:id"  element={<DmsPage Component={OwnerOrderDetailPage} />} />
      <Route path="/dms/owner/inventory"           element={<DmsPage Component={OwnerInventoryPage} />} />
      <Route path="/dms/owner/ledger"              element={<DmsPage Component={PrimaryLedgerPage} />} />
      <Route path="/dms/owner/retailer-prices"     element={<DmsPage Component={CategoriesPage} />} />
      <Route path="/dms/owner/users"               element={<DmsPage Component={OwnerUsersPage} />} />
      <Route path="/dms/owner/live-tracking"       element={<DmsPage Component={LiveTrackingPage} />} />
      <Route path="/dms/owner/tl-performance"      element={<DmsPage Component={OwnerTlPerformancePage} />} />
      <Route path="/dms/owner/distributor-sales"   element={<DmsPage Component={OwnerDistributorSalesListPage} />} />
      <Route path="/dms/owner/distributor-sales/:id" element={<DmsPage Component={OwnerDistributorSalesDetailPage} />} />
      <Route path="/dms/owner/coupons"                  element={<DmsPage Component={OwnerCouponsPage} />} />
      <Route path="/dms/owner/coupons/all"              element={<DmsPage Component={OwnerCouponsListPage} />} />
      <Route path="/dms/owner/coupons/batches/:bid"     element={<DmsPage Component={OwnerCouponBatchDetailPage} />} />
      <Route path="/dms/owner/coupons/redemptions"      element={<DmsPage Component={OwnerRedemptionsPage} />} />
      <Route path="/dms/owner/coupons/credit-notes"     element={<DmsPage Component={OwnerCreditNotesPage} />} />
      <Route path="/dms/owner/coupons/dispatch-advices" element={<DmsPage Component={OwnerDispatchAdvicesPage} />} />
      <Route path="/dms/owner/coupons/audit-log"        element={<DmsPage Component={OwnerCouponAuditLogPage} />} />
      <Route path="/dms/owner/coupons/fraud"            element={<DmsPage Component={OwnerFraudDashboardPage} />} />
      <Route path="/dms/owner/coupon-reports"           element={<DmsPage Component={OwnerCouponReportsPage} />} />
      <Route path="/dms/owner/price-circulars"     element={<DmsPage Component={PriceCircularsPage} />} />
      <Route path="/dms/owner/price-circulars/new" element={<DmsPage Component={NewPriceCircularPage} />} />
      <Route path="/dms/owner/price-circulars/:id" element={<DmsPage Component={PriceCircularDetailPage} />} />
      <Route path="/dms/owner/settings"            element={<DmsPage Component={SettingsPage} />} />
      <Route path="/dms/expenses"                  element={<DmsPage Component={ExpensesPage} />} />
      {/* Phase 2B — Cash & Bank */}
      <Route path="/dms/finance/bank-accounts"     element={<DmsPage Component={BankAccountsPage} />} />
      <Route path="/dms/finance/bank-transactions" element={<DmsPage Component={BankTransactionsPage} />} />
      <Route path="/dms/finance/cash-register"     element={<DmsPage Component={CashRegisterPage} />} />
      <Route path="/dms/finance/cheques"           element={<DmsPage Component={ChequesPage} />} />
      <Route path="/dms/finance/loans"             element={<DmsPage Component={LoanAccountsPage} />} />
      {/* Phase 2B — Warehouse */}
      <Route path="/dms/warehouse/godowns"         element={<DmsPage Component={GodownsPage} />} />
      <Route path="/dms/warehouse/transfers"       element={<DmsPage Component={StockTransfersPage} />} />
      {/* Phase 2C */}
      <Route path="/dms/import-export"             element={<DmsPage Component={ImportExportPage} />} />
      <Route path="/dms/direct-sales"              element={<DmsPage Component={DirectSalesPage} />} />
      <Route path="/dms/documents"                 element={<DmsPage Component={DocumentsPage} />} />
      {/* Phase 3 — Reports */}
      <Route path="/dms/reports"                   element={<DmsPage Component={ReportsHubPage} />} />
      <Route path="/dms/reports/:reportId"         element={<DmsPage Component={GenericReportPage} />} />
      <Route path="/dms/salesperson/scan"          element={<DmsPage Component={SalesOfficerScanPage} />} />
      <Route path="/dms/retailer/wallet"           element={<DmsPage Component={RetailerWalletPage} />} />
      <Route path="/dms/distributor/coupons"       element={<DmsPage Component={DistributorCouponsPage} />} />
      <Route path="/dms/team-leader/live-tracking" element={<DmsPage Component={LiveTrackingPage} />} />
      <Route path="/dms/team-leader/salespersons"  element={<DmsPage Component={TlSalespersonsPage} />} />
      <Route path="/dms/team-leader/orders"        element={<DmsPage Component={TlOrdersMonitoringPage} />} />
      <Route path="/dms/team-leader/retailers"     element={<DmsPage Component={TlRetailersPage} />} />
      <Route path="/dms/team-leader/attendance"    element={<DmsPage Component={TlAttendancePage} />} />
      <Route path="/dms/regional-manager/live-tracking" element={<DmsPage Component={LiveTrackingPage} />} />
      <Route path="/dms/regional-manager/team-leaders"  element={<DmsPage Component={RmTeamLeadersPage} />} />
      <Route path="/dms/regional-manager/performance"   element={<DmsPage Component={RmRegionPerformancePage} />} />
      <Route path="/dms/regional-manager/distributors"  element={<DmsPage Component={RmDistributorsPage} />} />
      <Route path="/dms/regional-manager/salespersons"  element={<DmsPage Component={RmSalespersonsPage} />} />

      {/* Distributor */}
      <Route path="/dms/distributor/browse"           element={<DmsPage Component={DistributorBrowsePage} />} />
      <Route path="/dms/distributor/my-orders"        element={<DmsPage Component={DistributorOrdersPage} />} />
      <Route path="/dms/distributor/my-orders/:id"    element={<DmsPage Component={DistributorOrderDetailPage} />} />
      <Route path="/dms/distributor/stock"            element={<DmsPage Component={DistributorStockPage} />} />
      <Route path="/dms/distributor/ledger"           element={<DmsPage Component={PrimaryLedgerPage} />} />
      <Route path="/dms/distributor/retailers"        element={<DmsPage Component={DistRetailersPage} />} />
      <Route path="/dms/distributor/retailers/:id"    element={<DmsPage Component={DistRetailerDetailPage} />} />
      <Route path="/dms/distributor/retail-orders"    element={<DmsPage Component={DistSecondaryOrdersPage} />} />
      <Route path="/dms/distributor/retail-orders/:id" element={<DmsPage Component={DistSecondaryOrderDetailPage} />} />
      <Route path="/dms/distributor/sec-ledger"       element={<DmsPage Component={SecondaryLedgerPage} />} />

      {/* Retailer */}
      <Route path="/dms/retailer/browse"        element={<DmsPage Component={RetailerBrowsePage} />} />
      <Route path="/dms/retailer/my-orders"     element={<DmsPage Component={RetailerOrdersPage} />} />
      <Route path="/dms/retailer/my-orders/:id" element={<DmsPage Component={RetailerOrderDetailPage} />} />

      {/* Salesperson */}
      <Route path="/dms/salesperson"                element={<DmsPage Component={DmsDashboardRouter} />} />
      <Route path="/dms/salesperson/distributors"  element={<DmsPage Component={SpDistributorsPage} />} />
      <Route path="/dms/salesperson/retailers"     element={<DmsPage Component={SpRetailersPage} />} />
      <Route path="/dms/salesperson/new-retailer"  element={<DmsPage Component={SpNewRetailerPage} />} />
      <Route path="/dms/salesperson/new-order"     element={<DmsPage Component={SpNewOrderPage} />} />
      <Route path="/dms/salesperson/orders"        element={<DmsPage Component={SpOrdersPage} />} />
      <Route path="/dms/salesperson/collect"       element={<DmsPage Component={SpCollectPaymentPage} />} />

      {/* Team Leader */}
      <Route path="/dms/team-leader/distributors" element={<DmsPage Component={TlDistributorsMonitoringPage} />} />
      <Route path="/dms/team-leader/assignments"  element={<DmsPage Component={TlAssignmentsPage} />} />

      {/* Super Admin */}
      <Route path="/dms/admin/users" element={<DmsPage Component={SuperAdminUsersPage} />} />

      {/* Print pages (no shell) */}
      <Route path="/dms/print/ebill/:id"          element={<PrintPage Component={PrintEbillPage} />} />
      <Route path="/dms/print/retailer-bill/:id"  element={<PrintPage Component={PrintRetailerBillPage} />} />
      <Route path="/dms/print/purchase-order/:id" element={<PrintPage Component={PrintPurchaseOrderPage} />} />
      <Route path="/dms/print/document/:id"       element={<PrintPage Component={PrintDocumentPage} />} />

      <Route path="/" element={<Navigate to="/dms" replace />} />
      <Route path="/app/*" element={<Navigate to="/dms" replace />} />
      <Route path="*" element={<Navigate to="/dms" replace />} />
    </Routes>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <AppRoutes />
        <Toaster richColors position="top-right" />
      </AuthProvider>
    </BrowserRouter>
  );
}

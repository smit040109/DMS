import React, { Suspense } from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider, useAuth } from "@/context/AuthContext";
import { TenantProvider } from "@/context/TenantContext";
import { Toaster } from "@/components/ui/sonner";
import AppShell from "@/components/layout/AppShell";
import Login from "@/pages/Login";
import Dashboard from "@/pages/Dashboard";

/**
 * Route-level code-splitting.
 * Each module file becomes its own webpack chunk, so the initial JS
 * payload only contains AppShell + Dashboard + Login + shared UI.
 * All list/inventory/finance/reverse/analytics/admin modules load on demand.
 *
 * lazyNamed() extracts a named export from a module file and shapes it as a
 * default export (which is what React.lazy expects).
 */
const lazyNamed = (loader, name) =>
  React.lazy(() => loader().then((mod) => ({ default: mod[name] })));

// ListModules chunk
const listLoader = () => import(/* webpackChunkName: "list" */ "@/pages/modules/ListModules");
const ProductsPage        = lazyNamed(listLoader, "ProductsPage");
const SkusPage            = lazyNamed(listLoader, "SkusPage");
const BatchesPage         = lazyNamed(listLoader, "BatchesPage");
const WarehousesPage      = lazyNamed(listLoader, "WarehousesPage");
const DistributorsPage    = lazyNamed(listLoader, "DistributorsPage");
const RetailersPage       = lazyNamed(listLoader, "RetailersPage");
const CustomersPage       = lazyNamed(listLoader, "CustomersPage");
const PrimaryOrdersPage   = lazyNamed(listLoader, "PrimaryOrdersPage");
const SecondaryOrdersPage = lazyNamed(listLoader, "SecondaryOrdersPage");
const InvoicesPage        = lazyNamed(listLoader, "InvoicesPage");
const DispatchesPage      = lazyNamed(listLoader, "DispatchesPage");
const GitPage             = lazyNamed(listLoader, "GitPage");
const GrnPage             = lazyNamed(listLoader, "GrnPage");
const ExpensesPage        = lazyNamed(listLoader, "ExpensesPage");
const ApprovalsPage       = lazyNamed(listLoader, "ApprovalsPage");
const NotificationsPage   = lazyNamed(listLoader, "NotificationsPage");

// AdminModules chunk
const adminLoader = () => import(/* webpackChunkName: "admin" */ "@/pages/modules/AdminModules");
const UsersPage       = lazyNamed(adminLoader, "UsersPage");
const RolesPage       = lazyNamed(adminLoader, "RolesPage");
const MasterDataPage  = lazyNamed(adminLoader, "MasterDataPage");
const ReportsPage     = lazyNamed(adminLoader, "ReportsPage");
const AnalyticsPage   = lazyNamed(adminLoader, "AnalyticsPage");
const AiAssistantPage = lazyNamed(adminLoader, "AiAssistantPage");
const SettingsPage    = lazyNamed(adminLoader, "SettingsPage");

// InventoryModules chunk
const invLoader = () => import(/* webpackChunkName: "inventory" */ "@/pages/modules/InventoryModules");
const CompanyInventoryPage     = lazyNamed(invLoader, "CompanyInventoryPage");
const DistributorInventoryPage = lazyNamed(invLoader, "DistributorInventoryPage");
const RetailerInventoryPage    = lazyNamed(invLoader, "RetailerInventoryPage");
const StockLedgerPage          = lazyNamed(invLoader, "StockLedgerPage");

// FinanceModules chunk
const finLoader = () => import(/* webpackChunkName: "finance" */ "@/pages/modules/FinanceModules");
const PaymentsFinancePage = lazyNamed(finLoader, "PaymentsFinancePage");
const OutstandingPage     = lazyNamed(finLoader, "OutstandingPage");
const DoubleLedgerPage    = lazyNamed(finLoader, "DoubleLedgerPage");
const CashbackEnginePage  = lazyNamed(finLoader, "CashbackEnginePage");
const CouponsEnginePage   = lazyNamed(finLoader, "CouponsEnginePage");
const CustomerOrdersPage  = lazyNamed(finLoader, "CustomerOrdersPage");
const WalletsPage         = lazyNamed(finLoader, "WalletsPage");
const ReconciliationPage  = lazyNamed(finLoader, "ReconciliationPage");
const AuditLogPage        = lazyNamed(finLoader, "AuditLogPage");

// ReverseModules chunk
const revLoader = () => import(/* webpackChunkName: "reverse" */ "@/pages/modules/ReverseModules");
const ReturnsPage         = lazyNamed(revLoader, "ReturnsPage");
const DamagePage          = lazyNamed(revLoader, "DamagePage");
const ClaimsPage          = lazyNamed(revLoader, "ClaimsPage");
const CreditNotesPage     = lazyNamed(revLoader, "CreditNotesPage");
const DebitNotesPage      = lazyNamed(revLoader, "DebitNotesPage");
const ReplacementsPage    = lazyNamed(revLoader, "ReplacementsPage");
const ExpiryPage          = lazyNamed(revLoader, "ExpiryPage");
const ApprovalEnginePage  = lazyNamed(revLoader, "ApprovalEnginePage");
const ExceptionsPage      = lazyNamed(revLoader, "ExceptionsPage");
const ReportsHubPage      = lazyNamed(revLoader, "ReportsHubPage");

// AnalyticsModules chunk (Phase 4 BI)
const anaLoader = () => import(/* webpackChunkName: "analytics" */ "@/pages/modules/AnalyticsModules");
const ExecutiveCommandCenter = lazyNamed(anaLoader, "ExecutiveCommandCenter");
const OrderTracePage         = lazyNamed(anaLoader, "OrderTracePage");
const Party360Page           = lazyNamed(anaLoader, "Party360Page");
const SalesAnalyticsPage     = lazyNamed(anaLoader, "SalesAnalyticsPage");
const InventoryAnalyticsPage = lazyNamed(anaLoader, "InventoryAnalyticsPage");
const FinanceAnalyticsPage   = lazyNamed(anaLoader, "FinanceAnalyticsPage");
const BusinessAlertsPage     = lazyNamed(anaLoader, "BusinessAlertsPage");
const ScorecardsPage         = lazyNamed(anaLoader, "ScorecardsPage");
const ExecutiveAnalyticsHub  = lazyNamed(anaLoader, "ExecutiveAnalyticsHub");

// PlatformModules chunk (VayuERP SaaS control plane)
const platLoader = () => import(/* webpackChunkName: "platform" */ "@/pages/modules/PlatformModules");
const TenantOnboardingPage  = lazyNamed(platLoader, "TenantOnboardingPage");
const PlatformTenantsPage   = lazyNamed(platLoader, "PlatformTenantsPage");
const PlatformAnalyticsPage = lazyNamed(platLoader, "PlatformAnalyticsPage");
const PlatformPlansPage     = lazyNamed(platLoader, "PlatformPlansPage");
const PlatformSubscriptionsPage = lazyNamed(platLoader, "PlatformSubscriptionsPage");
const PlatformModulesPage   = lazyNamed(platLoader, "PlatformModulesPage");
const PlatformBillingPage   = lazyNamed(platLoader, "PlatformBillingPage");
const PlatformAnnouncementsPage = lazyNamed(platLoader, "PlatformAnnouncementsPage");
const PlatformFlagsPage     = lazyNamed(platLoader, "PlatformFlagsPage");
const PlatformBackupsPage   = lazyNamed(platLoader, "PlatformBackupsPage");
const TenantBrandingPage    = lazyNamed(platLoader, "TenantBrandingPage");
const TenantSettingsPage    = lazyNamed(platLoader, "TenantSettingsPage");
const TenantApiKeysPage     = lazyNamed(platLoader, "TenantApiKeysPage");
const TenantWebhooksPage    = lazyNamed(platLoader, "TenantWebhooksPage");
const TenantMarketplacePage = lazyNamed(platLoader, "TenantMarketplacePage");

function RouteFallback() {
  return (
    <div className="min-h-[50vh] flex items-center justify-center" data-testid="route-loading">
      <div className="flex items-center gap-3 text-ink-muted text-sm">
        <div className="h-4 w-4 rounded-full border-2 border-current border-t-transparent animate-spin" />
        <span>Loading module…</span>
      </div>
    </div>
  );
}

function Protected({ children }) {
  const { user } = useAuth();
  if (user === null) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-canvas" data-testid="auth-loading">
        <div className="text-ink-muted text-sm">Loading command center…</div>
      </div>
    );
  }
  if (!user) return <Navigate to="/login" replace />;
  return children;
}

function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route
        path="/app"
        element={
          <Protected>
            <AppShell><Dashboard /></AppShell>
          </Protected>
        }
      />
      {[
        ["products", ProductsPage],
        ["skus", SkusPage],
        ["batches", BatchesPage],
        ["inventory", CompanyInventoryPage],
        ["distributor-inventory", DistributorInventoryPage],
        ["retailer-inventory", RetailerInventoryPage],
        ["stock-ledger", StockLedgerPage],
        ["warehouses", WarehousesPage],
        ["distributors", DistributorsPage],
        ["retailers", RetailersPage],
        ["customers", CustomersPage],
        ["primary-orders", PrimaryOrdersPage],
        ["secondary-orders", SecondaryOrdersPage],
        ["customer-orders", CustomerOrdersPage],
        ["invoices", InvoicesPage],
        ["dispatches", DispatchesPage],
        ["goods-in-transit", GitPage],
        ["grns", GrnPage],
        ["payments", PaymentsFinancePage],
        ["outstanding", OutstandingPage],
        ["ledger", DoubleLedgerPage],
        ["reconciliation", ReconciliationPage],
        ["expenses", ExpensesPage],
        ["cashback", CashbackEnginePage],
        ["coupons", CouponsEnginePage],
        ["wallets", WalletsPage],
        ["approvals", ApprovalsPage],
        ["audit-log", AuditLogPage],
        ["notifications", NotificationsPage],
        ["users", UsersPage],
        ["roles", RolesPage],
        ["master-data", MasterDataPage],
        ["reports", ReportsPage],
        ["analytics", AnalyticsPage],
        ["ai-assistant", AiAssistantPage],
        ["settings", SettingsPage],
        // Phase 3 — Reverse Logistics
        ["returns", ReturnsPage],
        ["damage", DamagePage],
        ["claims", ClaimsPage],
        ["credit-notes", CreditNotesPage],
        ["debit-notes", DebitNotesPage],
        ["replacements", ReplacementsPage],
        ["expiry", ExpiryPage],
        ["approval-engine", ApprovalEnginePage],
        ["exceptions", ExceptionsPage],
        ["reports-hub", ReportsHubPage],
        // Phase 4 — Business Intelligence
        ["executive-center", ExecutiveCommandCenter],
        ["order-trace", OrderTracePage],
        ["party-360", Party360Page],
        ["party360/:type/:id", Party360Page],
        ["sales-analytics", SalesAnalyticsPage],
        ["inventory-analytics", InventoryAnalyticsPage],
        ["finance-analytics", FinanceAnalyticsPage],
        ["executive-analytics", ExecutiveAnalyticsHub],
        ["business-alerts", BusinessAlertsPage],
        ["scorecards", ScorecardsPage],
        // VayuERP — Platform (super admin)
        ["platform/tenants", PlatformTenantsPage],
        ["platform/analytics", PlatformAnalyticsPage],
        ["platform/plans", PlatformPlansPage],
        ["platform/subscriptions", PlatformSubscriptionsPage],
        ["platform/modules", PlatformModulesPage],
        ["platform/billing", PlatformBillingPage],
        ["platform/announcements", PlatformAnnouncementsPage],
        ["platform/flags", PlatformFlagsPage],
        ["platform/backups", PlatformBackupsPage],
        ["platform/onboard", TenantOnboardingPage],
        // Tenant admin
        ["tenant/branding", TenantBrandingPage],
        ["tenant/settings", TenantSettingsPage],
        ["tenant/api-keys", TenantApiKeysPage],
        ["tenant/webhooks", TenantWebhooksPage],
        ["tenant/marketplace", TenantMarketplacePage],
      ].map(([path, Component]) => (
        <Route
          key={path}
          path={`/app/${path}`}
          element={
            <Protected>
              <AppShell>
                <Suspense fallback={<RouteFallback />}>
                  <Component />
                </Suspense>
              </AppShell>
            </Protected>
          }
        />
      ))}
      <Route path="/" element={<Navigate to="/app" replace />} />
      <Route path="*" element={<Navigate to="/app" replace />} />
    </Routes>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <TenantProvider>
          <AppRoutes />
          <Toaster richColors position="top-right" />
        </TenantProvider>
      </AuthProvider>
    </BrowserRouter>
  );
}

import React from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider, useAuth } from "@/context/AuthContext";
import { Toaster } from "@/components/ui/sonner";
import AppShell from "@/components/layout/AppShell";
import Login from "@/pages/Login";
import Dashboard from "@/pages/Dashboard";

import {
  ProductsPage, SkusPage, BatchesPage,
  WarehousesPage,
  DistributorsPage, RetailersPage, CustomersPage,
  PrimaryOrdersPage, SecondaryOrdersPage, InvoicesPage,
  DispatchesPage, GitPage, GrnPage,
  ExpensesPage,
  ApprovalsPage, NotificationsPage,
} from "@/pages/modules/ListModules";

import {
  UsersPage, RolesPage, MasterDataPage,
  ReportsPage, AnalyticsPage,
  AiAssistantPage, SettingsPage,
} from "@/pages/modules/AdminModules";

import {
  CompanyInventoryPage, DistributorInventoryPage, RetailerInventoryPage, StockLedgerPage,
} from "@/pages/modules/InventoryModules";

import {
  PaymentsFinancePage, OutstandingPage, DoubleLedgerPage,
  CashbackEnginePage, CouponsEnginePage,
  CustomerOrdersPage, WalletsPage, ReconciliationPage, AuditLogPage,
} from "@/pages/modules/FinanceModules";

import {
  ReturnsPage, DamagePage, ClaimsPage,
  CreditNotesPage, DebitNotesPage, ReplacementsPage,
  ExpiryPage, ApprovalEnginePage, ExceptionsPage, ReportsHubPage,
} from "@/pages/modules/ReverseModules";

import {
  ExecutiveCommandCenter, OrderTracePage, Party360Page,
  SalesAnalyticsPage, InventoryAnalyticsPage, FinanceAnalyticsPage,
  BusinessAlertsPage, ScorecardsPage, ExecutiveAnalyticsHub,
} from "@/pages/modules/AnalyticsModules";

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
        ["products", <ProductsPage />],
        ["skus", <SkusPage />],
        ["batches", <BatchesPage />],
        ["inventory", <CompanyInventoryPage />],
        ["distributor-inventory", <DistributorInventoryPage />],
        ["retailer-inventory", <RetailerInventoryPage />],
        ["stock-ledger", <StockLedgerPage />],
        ["warehouses", <WarehousesPage />],
        ["distributors", <DistributorsPage />],
        ["retailers", <RetailersPage />],
        ["customers", <CustomersPage />],
        ["primary-orders", <PrimaryOrdersPage />],
        ["secondary-orders", <SecondaryOrdersPage />],
        ["customer-orders", <CustomerOrdersPage />],
        ["invoices", <InvoicesPage />],
        ["dispatches", <DispatchesPage />],
        ["goods-in-transit", <GitPage />],
        ["grns", <GrnPage />],
        ["payments", <PaymentsFinancePage />],
        ["outstanding", <OutstandingPage />],
        ["ledger", <DoubleLedgerPage />],
        ["reconciliation", <ReconciliationPage />],
        ["expenses", <ExpensesPage />],
        ["cashback", <CashbackEnginePage />],
        ["coupons", <CouponsEnginePage />],
        ["wallets", <WalletsPage />],
        ["approvals", <ApprovalsPage />],
        ["audit-log", <AuditLogPage />],
        ["notifications", <NotificationsPage />],
        ["users", <UsersPage />],
        ["roles", <RolesPage />],
        ["master-data", <MasterDataPage />],
        ["reports", <ReportsPage />],
        ["analytics", <AnalyticsPage />],
        ["ai-assistant", <AiAssistantPage />],
        ["settings", <SettingsPage />],
        // Phase 3 — Reverse Logistics
        ["returns", <ReturnsPage />],
        ["damage", <DamagePage />],
        ["claims", <ClaimsPage />],
        ["credit-notes", <CreditNotesPage />],
        ["debit-notes", <DebitNotesPage />],
        ["replacements", <ReplacementsPage />],
        ["expiry", <ExpiryPage />],
        ["approval-engine", <ApprovalEnginePage />],
        ["exceptions", <ExceptionsPage />],
        ["reports-hub", <ReportsHubPage />],
        // Phase 4 — Business Intelligence
        ["executive-center", <ExecutiveCommandCenter />],
        ["order-trace", <OrderTracePage />],
        ["party-360", <Party360Page />],
        ["party360/:type/:id", <Party360Page />],
        ["sales-analytics", <SalesAnalyticsPage />],
        ["inventory-analytics", <InventoryAnalyticsPage />],
        ["finance-analytics", <FinanceAnalyticsPage />],
        ["executive-analytics", <ExecutiveAnalyticsHub />],
        ["business-alerts", <BusinessAlertsPage />],
        ["scorecards", <ScorecardsPage />],
      ].map(([path, el]) => (
        <Route
          key={path}
          path={`/app/${path}`}
          element={
            <Protected>
              <AppShell>{el}</AppShell>
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
        <AppRoutes />
        <Toaster richColors position="top-right" />
      </AuthProvider>
    </BrowserRouter>
  );
}

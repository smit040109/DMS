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

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

function Protected({ children }) {
  const { user } = useAuth();
  if (user === null) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <div className="text-sm text-slate-500">Loading…</div>
      </div>
    );
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

function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />

      {/* DMS routes */}
      <Route path="/dms" element={<DmsPage Component={DmsDashboardRouter} />} />

      {/* Owner routes */}
      <Route path="/dms/owner/categories"          element={<DmsPage Component={CategoriesPage} />} />
      <Route path="/dms/owner/products"            element={<DmsPage Component={ProductsPage} />} />
      <Route path="/dms/owner/distributors"        element={<DmsPage Component={DistributorsPage} />} />
      <Route path="/dms/owner/distributors/:id"    element={<DmsPage Component={DistributorDetailPage} />} />
      <Route path="/dms/owner/primary-orders"      element={<DmsPage Component={OwnerPrimaryOrdersPage} />} />
      <Route path="/dms/owner/primary-orders/:id"  element={<DmsPage Component={OwnerOrderDetailPage} />} />
      <Route path="/dms/owner/inventory"           element={<DmsPage Component={OwnerInventoryPage} />} />
      <Route path="/dms/owner/ledger"              element={<DmsPage Component={PrimaryLedgerPage} />} />

      {/* Distributor routes */}
      <Route path="/dms/distributor/browse"           element={<DmsPage Component={DistributorBrowsePage} />} />
      <Route path="/dms/distributor/my-orders"        element={<DmsPage Component={DistributorOrdersPage} />} />
      <Route path="/dms/distributor/my-orders/:id"    element={<DmsPage Component={DistributorOrderDetailPage} />} />
      <Route path="/dms/distributor/stock"            element={<DmsPage Component={DistributorStockPage} />} />
      <Route path="/dms/distributor/ledger"           element={<DmsPage Component={PrimaryLedgerPage} />} />

      {/* Root → send to /dms if logged in, /login otherwise */}
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

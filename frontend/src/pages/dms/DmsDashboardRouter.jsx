import React from "react";
import { Navigate } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { OwnerDashboardPage } from "./OwnerPages";
import { DistributorDashboardPage } from "./DistributorPages";
import { RetailerDashboardPage, SalespersonDashboardPage, TeamLeaderDashboardPage, RegionalManagerDashboardPage, DistAcctDashboardPage } from "./PlaceholderPages";

/**
 * Dashboard router — picks the right dashboard based on user's role.
 * All roles land at /dms and are shown their own dashboard.
 */
export default function DmsDashboardRouter() {
  const { user } = useAuth();
  if (!user) return null;
  const role = user.role;
  if (role === "owner" || role === "super_admin") return <OwnerDashboardPage />;
  if (role === "owner_accountant") return <OwnerDashboardPage />;  // same view for now
  if (role === "distributor") return <DistributorDashboardPage />;
  if (role === "distributor_accountant") return <DistAcctDashboardPage />;
  if (role === "retailer") return <RetailerDashboardPage />;
  if (role === "salesperson") return <SalespersonDashboardPage />;
  if (role === "team_leader") return <TeamLeaderDashboardPage />;
  if (role === "regional_manager") return <RegionalManagerDashboardPage />;
  // Legacy roles from the old ERP still logged in — redirect to their dashboard
  return <div className="p-6 text-sm text-slate-500">This role isn&apos;t part of the Simple DMS. Please log in with a DMS demo account.</div>;
}

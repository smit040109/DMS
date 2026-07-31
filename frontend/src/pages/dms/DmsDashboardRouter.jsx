import React from "react";
import { useAuth } from "@/context/AuthContext";
import { OwnerDashboardPage } from "./OwnerPages";
import { DistributorDashboardPage } from "./DistributorPages";
import { RetailerDashboardPage } from "./RetailerPages";
import { SalespersonDashboardPage } from "./SalesTeamPages";
import { SuperAdminDashboardPage } from "./SuperAdminPages";
import { TlDashboardPage } from "./TeamLeaderPages";
import { RmDashboardPage } from "./RegionalManagerPages";

export default function DmsDashboardRouter() {
  const { user } = useAuth();
  if (!user) return null;
  const role = user.role;
  if (role === "super_admin") return <SuperAdminDashboardPage />;
  if (role === "owner") return <OwnerDashboardPage />;
  if (role === "owner_accountant") return <OwnerDashboardPage />;
  if (role === "distributor" || role === "distributor_accountant") return <DistributorDashboardPage />;
  if (role === "retailer") return <RetailerDashboardPage />;
  if (role === "salesperson") return <SalespersonDashboardPage />;
  if (role === "team_leader") return <TlDashboardPage />;
  if (role === "regional_manager") return <RmDashboardPage />;
  return <div className="p-6 text-sm text-slate-500">This role isn&apos;t part of the Simple DMS. Please log in with a DMS demo account.</div>;
}

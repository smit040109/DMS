import React from "react";

const MAP = {
  // Neutral / info blue
  open: { bg: "#EFF6FF", fg: "#2563EB", label: "Open" },
  info: { bg: "#EFF6FF", fg: "#2563EB", label: "Info" },
  invoiced: { bg: "#F1F5F9", fg: "#475569", label: "Invoiced" },
  closed: { bg: "#F1F5F9", fg: "#475569", label: "Closed" },
  draft: { bg: "#F1F5F9", fg: "#64748B", label: "Draft" },
  dormant: { bg: "#F1F5F9", fg: "#64748B", label: "Dormant" },

  // success
  approved: { bg: "#ECFDF5", fg: "#16A34A", label: "Approved" },
  ready: { bg: "#ECFDF5", fg: "#16A34A", label: "Ready" },
  paid: { bg: "#ECFDF5", fg: "#16A34A", label: "Paid" },
  cleared: { bg: "#ECFDF5", fg: "#16A34A", label: "Cleared" },
  delivered: { bg: "#ECFDF5", fg: "#16A34A", label: "Delivered" },
  active: { bg: "#ECFDF5", fg: "#16A34A", label: "Active" },
  accepted: { bg: "#ECFDF5", fg: "#16A34A", label: "Accepted" },
  credited: { bg: "#ECFDF5", fg: "#16A34A", label: "Credited" },
  ok: { bg: "#ECFDF5", fg: "#16A34A", label: "OK" },
  reimbursed: { bg: "#ECFDF5", fg: "#16A34A", label: "Reimbursed" },
  good: { bg: "#ECFDF5", fg: "#16A34A", label: "Good" },

  // warning
  pending: { bg: "#FFFBEB", fg: "#B45309", label: "Pending" },
  partial: { bg: "#FFFBEB", fg: "#B45309", label: "Partial" },
  low: { bg: "#FFFBEB", fg: "#B45309", label: "Low" },
  "under test": { bg: "#FFFBEB", fg: "#B45309", label: "Under Test" },
  "under review": { bg: "#FFFBEB", fg: "#B45309", label: "Under Review" },
  "in transit": { bg: "#FFFBEB", fg: "#B45309", label: "In Transit" },
  loaded: { bg: "#FFFBEB", fg: "#B45309", label: "Loaded" },
  prepared: { bg: "#FFFBEB", fg: "#B45309", label: "Prepared" },
  paused: { bg: "#FFFBEB", fg: "#B45309", label: "Paused" },
  "on hold": { bg: "#FFFBEB", fg: "#B45309", label: "On Hold" },
  "pending kyc": { bg: "#FFFBEB", fg: "#B45309", label: "Pending KYC" },
  redeemed: { bg: "#FFFBEB", fg: "#B45309", label: "Redeemed" },
  short: { bg: "#FFFBEB", fg: "#B45309", label: "Short" },

  // danger
  delayed: { bg: "#FEF2F2", fg: "#DC2626", label: "Delayed" },
  overdue: { bg: "#FEF2F2", fg: "#DC2626", label: "Overdue" },
  rejected: { bg: "#FEF2F2", fg: "#DC2626", label: "Rejected" },
  disputed: { bg: "#FEF2F2", fg: "#DC2626", label: "Disputed" },
  bounced: { bg: "#FEF2F2", fg: "#DC2626", label: "Bounced" },
  damaged: { bg: "#FEF2F2", fg: "#DC2626", label: "Damaged" },
  unpaid: { bg: "#FEF2F2", fg: "#DC2626", label: "Unpaid" },
  expired: { bg: "#FEF2F2", fg: "#DC2626", label: "Expired" },
  "stock-out": { bg: "#FEF2F2", fg: "#DC2626", label: "Stock-out" },

  // Gold accent
  gold: { bg: "#F7EFD4", fg: "#A67C00", label: "Gold" },
  success: { bg: "#ECFDF5", fg: "#16A34A", label: "Success" },
  warning: { bg: "#FFFBEB", fg: "#B45309", label: "Warning" },
  danger: { bg: "#FEF2F2", fg: "#DC2626", label: "Danger" },
};

export default function StatusPill({ value, size = "md" }) {
  const v = String(value ?? "").toLowerCase();
  const meta = MAP[v] || { bg: "#F1F5F9", fg: "#475569", label: value || "—" };
  const pad = size === "sm" ? "px-2 py-0.5 text-[11px]" : "px-2.5 py-1 text-xs";
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full font-medium ${pad}`}
      style={{ background: meta.bg, color: meta.fg }}
      data-testid={`status-pill-${v}`}
    >
      <span className="w-1.5 h-1.5 rounded-full" style={{ background: meta.fg }} />
      {meta.label}
    </span>
  );
}

// Navigation config. Each item's visibility filtered by role.

export const NAV_GROUPS = [
  {
    label: "Overview",
    items: [
      { key: "dashboard", label: "Dashboard", icon: "LayoutDashboard", to: "/app", roles: "*" },
    ],
  },
  {
    label: "Catalog",
    items: [
      { key: "products", label: "Products", icon: "Package", to: "/app/products", roles: ["super_admin", "company_admin", "regional_manager"] },
      { key: "skus", label: "SKUs", icon: "Boxes", to: "/app/skus", roles: ["super_admin", "company_admin", "regional_manager"] },
      { key: "batches", label: "Batches", icon: "Layers", to: "/app/batches", roles: ["super_admin", "company_admin", "regional_manager"] },
    ],
  },
  {
    label: "Operations",
    items: [
      { key: "inventory", label: "Company Inventory", icon: "Warehouse", to: "/app/inventory", roles: ["super_admin", "company_admin", "regional_manager"] },
      { key: "distributor-inventory", label: "Distributor Inventory", icon: "Handshake", to: "/app/distributor-inventory", roles: ["super_admin", "company_admin", "regional_manager", "distributor"] },
      { key: "retailer-inventory", label: "Retailer Inventory", icon: "Store", to: "/app/retailer-inventory", roles: ["super_admin", "company_admin", "regional_manager", "retailer"] },
      { key: "stock-ledger", label: "Stock Ledger", icon: "BookOpen", to: "/app/stock-ledger", roles: ["super_admin", "company_admin", "regional_manager", "distributor_accountant"] },
      { key: "warehouses", label: "Warehouses", icon: "Building2", to: "/app/warehouses", roles: ["super_admin", "company_admin", "regional_manager"] },
      { key: "dispatches", label: "Dispatch", icon: "Truck", to: "/app/dispatches", roles: ["super_admin", "company_admin", "regional_manager", "distributor"] },
      { key: "goods-in-transit", label: "Goods In Transit", icon: "Route", to: "/app/goods-in-transit", roles: ["super_admin", "company_admin", "regional_manager", "distributor"] },
      { key: "grns", label: "GRN", icon: "PackageCheck", to: "/app/grns", roles: ["super_admin", "company_admin", "regional_manager", "distributor"] },
    ],
  },
  {
    label: "Network",
    items: [
      { key: "distributors", label: "Distributors", icon: "Handshake", to: "/app/distributors", roles: ["super_admin", "company_admin", "regional_manager", "sales_executive"] },
      { key: "retailers", label: "Retailers", icon: "Store", to: "/app/retailers", roles: ["super_admin", "company_admin", "regional_manager", "sales_executive", "distributor"] },
      { key: "customers", label: "Customers", icon: "Users", to: "/app/customers", roles: ["super_admin", "company_admin", "regional_manager", "sales_executive"] },
    ],
  },
  {
    label: "Sales",
    items: [
      { key: "primary-orders", label: "Primary Orders", icon: "ShoppingCart", to: "/app/primary-orders", roles: ["super_admin", "company_admin", "regional_manager", "distributor"] },
      { key: "secondary-orders", label: "Secondary Orders", icon: "ShoppingBag", to: "/app/secondary-orders", roles: ["super_admin", "company_admin", "regional_manager", "sales_executive", "distributor", "retailer"] },
      { key: "customer-orders", label: "Customer Orders", icon: "Users", to: "/app/customer-orders", roles: ["super_admin", "company_admin", "regional_manager", "sales_executive", "retailer", "customer"] },
      { key: "invoices", label: "Invoices", icon: "FileText", to: "/app/invoices", roles: ["super_admin", "company_admin", "regional_manager", "distributor", "distributor_accountant", "retailer", "customer"] },
    ],
  },
  {
    label: "Finance",
    items: [
      { key: "payments", label: "Payments", icon: "CreditCard", to: "/app/payments", roles: ["super_admin", "company_admin", "regional_manager", "distributor", "distributor_accountant", "retailer"] },
      { key: "outstanding", label: "Outstanding", icon: "AlertCircle", to: "/app/outstanding", roles: ["super_admin", "company_admin", "regional_manager", "distributor_accountant"] },
      { key: "ledger", label: "Double-Entry Ledger", icon: "BookOpen", to: "/app/ledger", roles: ["super_admin", "company_admin", "regional_manager", "distributor_accountant"] },
      { key: "reconciliation", label: "Reconciliation", icon: "GitCompareArrows", to: "/app/reconciliation", roles: ["super_admin", "company_admin", "regional_manager", "distributor_accountant"] },
      { key: "expenses", label: "Expenses", icon: "Receipt", to: "/app/expenses", roles: ["super_admin", "company_admin", "regional_manager", "distributor_accountant"] },
    ],
  },
  {
    label: "Rewards",
    items: [
      { key: "cashback", label: "Cashback Engine", icon: "Gift", to: "/app/cashback", roles: ["super_admin", "company_admin", "regional_manager", "sales_executive", "retailer"] },
      { key: "coupons", label: "Coupon Engine", icon: "Ticket", to: "/app/coupons", roles: ["super_admin", "company_admin", "regional_manager", "sales_executive"] },
      { key: "wallets", label: "Wallets", icon: "Wallet", to: "/app/wallets", roles: ["super_admin", "company_admin", "regional_manager", "distributor_accountant", "retailer", "customer"] },
    ],
  },
  {
    label: "Reverse Logistics",
    items: [
      { key: "returns", label: "Returns", icon: "Undo2", to: "/app/returns", roles: ["super_admin", "company_admin", "regional_manager", "distributor", "retailer", "customer", "sales_executive"] },
      { key: "damage", label: "Damage", icon: "ShieldAlert", to: "/app/damage", roles: ["super_admin", "company_admin", "regional_manager", "distributor"] },
      { key: "claims", label: "Claims", icon: "HandCoins", to: "/app/claims", roles: ["super_admin", "company_admin", "regional_manager", "distributor", "retailer"] },
      { key: "credit-notes", label: "Credit Notes", icon: "FileMinus", to: "/app/credit-notes", roles: ["super_admin", "company_admin", "regional_manager", "distributor_accountant"] },
      { key: "debit-notes", label: "Debit Notes", icon: "FilePlus", to: "/app/debit-notes", roles: ["super_admin", "company_admin", "regional_manager", "distributor_accountant"] },
      { key: "replacements", label: "Replacements", icon: "Repeat", to: "/app/replacements", roles: ["super_admin", "company_admin", "regional_manager", "distributor"] },
      { key: "expiry", label: "Expiry", icon: "Timer", to: "/app/expiry", roles: ["super_admin", "company_admin", "regional_manager"] },
    ],
  },
  {
    label: "Compliance",
    items: [
      { key: "approval-engine", label: "Approval Engine", icon: "GitBranchPlus", to: "/app/approval-engine", roles: ["super_admin", "company_admin", "regional_manager", "distributor_accountant"] },
      { key: "exceptions", label: "Exception Engine", icon: "AlertOctagon", to: "/app/exceptions", roles: ["super_admin", "company_admin", "regional_manager"] },
      { key: "reports-hub", label: "Reports Hub", icon: "FileBarChart2", to: "/app/reports-hub", roles: ["super_admin", "company_admin", "regional_manager", "distributor_accountant"] },
    ],
  },
  {
    label: "Business Intelligence",
    items: [
      { key: "executive-center", label: "Executive Center", icon: "Activity", to: "/app/executive-center", roles: ["super_admin", "company_admin", "regional_manager"] },
      { key: "order-trace", label: "Order Trace", icon: "GitBranchPlus", to: "/app/order-trace", roles: ["super_admin", "company_admin", "regional_manager", "distributor", "sales_executive"] },
      { key: "party-360", label: "Party 360°", icon: "Users", to: "/app/party-360", roles: ["super_admin", "company_admin", "regional_manager"] },
      { key: "sales-analytics", label: "Sales Analytics", icon: "TrendingUp", to: "/app/sales-analytics", roles: ["super_admin", "company_admin", "regional_manager", "sales_executive"] },
      { key: "inventory-analytics", label: "Inventory Analytics", icon: "Package", to: "/app/inventory-analytics", roles: ["super_admin", "company_admin", "regional_manager"] },
      { key: "finance-analytics", label: "Finance Analytics", icon: "DollarSign", to: "/app/finance-analytics", roles: ["super_admin", "company_admin", "distributor_accountant", "regional_manager"] },
      { key: "executive-analytics", label: "Executive Analytics", icon: "BarChart3", to: "/app/executive-analytics", roles: ["super_admin", "company_admin", "regional_manager"] },
      { key: "business-alerts", label: "Business Alerts", icon: "AlertOctagon", to: "/app/business-alerts", roles: ["super_admin", "company_admin", "regional_manager"] },
      { key: "scorecards", label: "Scorecards", icon: "Award", to: "/app/scorecards", roles: ["super_admin", "company_admin", "regional_manager"] },
    ],
  },
  {
    label: "Insights",
    items: [
      { key: "reports", label: "Reports", icon: "FileBarChart2", to: "/app/reports", roles: ["super_admin", "company_admin", "regional_manager", "distributor_accountant"] },
      { key: "analytics", label: "Analytics", icon: "TrendingUp", to: "/app/analytics", roles: ["super_admin", "company_admin", "regional_manager"] },
    ],
  },
  {
    label: "Administration",
    items: [
      { key: "users", label: "User Management", icon: "UserCog", to: "/app/users", roles: ["super_admin", "company_admin"] },
      { key: "roles", label: "Role Management", icon: "ShieldCheck", to: "/app/roles", roles: ["super_admin", "company_admin"] },
      { key: "master-data", label: "Master Data", icon: "Database", to: "/app/master-data", roles: ["super_admin", "company_admin"] },
      { key: "approvals", label: "Approval Engine", icon: "CheckCheck", to: "/app/approvals", roles: ["super_admin", "company_admin", "regional_manager"] },
      { key: "audit-log", label: "Audit Log", icon: "ScrollText", to: "/app/audit-log", roles: ["super_admin", "company_admin"] },
      { key: "notifications", label: "Notifications", icon: "Bell", to: "/app/notifications", roles: "*" },
      { key: "ai-assistant", label: "AI Assistant", icon: "Sparkles", to: "/app/ai-assistant", roles: "*" },
      { key: "settings", label: "Settings", icon: "Settings", to: "/app/settings", roles: "*" },
    ],
  },
  {
    label: "Tenant Admin",
    items: [
      { key: "tenant-branding", label: "Branding & Theme", icon: "Palette", to: "/app/tenant/branding", roles: ["super_admin", "company_admin", "platform_owner"] },
      { key: "tenant-settings", label: "Company Settings", icon: "Building2", to: "/app/tenant/settings", roles: ["super_admin", "company_admin", "platform_owner"] },
      { key: "tenant-marketplace", label: "App Marketplace", icon: "LayoutGrid", to: "/app/tenant/marketplace", roles: ["super_admin", "company_admin", "platform_owner"] },
      { key: "tenant-api-keys", label: "API Keys", icon: "KeyRound", to: "/app/tenant/api-keys", roles: ["super_admin", "company_admin", "platform_owner"] },
      { key: "tenant-webhooks", label: "Webhooks", icon: "Webhook", to: "/app/tenant/webhooks", roles: ["super_admin", "company_admin", "platform_owner"] },
    ],
  },
  {
    label: "Platform",
    items: [
      { key: "platform-tenants", label: "Tenants", icon: "Building", to: "/app/platform/tenants", roles: ["platform_owner"] },
      { key: "platform-analytics", label: "Platform Analytics", icon: "LineChart", to: "/app/platform/analytics", roles: ["platform_owner"] },
      { key: "platform-plans", label: "Subscription Plans", icon: "Crown", to: "/app/platform/plans", roles: ["platform_owner"] },
      { key: "platform-subscriptions", label: "Subscriptions", icon: "Repeat", to: "/app/platform/subscriptions", roles: ["platform_owner"] },
      { key: "platform-modules", label: "Modules Catalogue", icon: "Boxes", to: "/app/platform/modules", roles: ["platform_owner"] },
      { key: "platform-billing", label: "Platform Billing", icon: "CreditCard", to: "/app/platform/billing", roles: ["platform_owner"] },
      { key: "platform-announcements", label: "Announcements", icon: "Megaphone", to: "/app/platform/announcements", roles: ["platform_owner"] },
      { key: "platform-flags", label: "Feature Flags", icon: "Flag", to: "/app/platform/flags", roles: ["platform_owner"] },
      { key: "platform-backups", label: "Backups", icon: "DatabaseBackup", to: "/app/platform/backups", roles: ["platform_owner"] },
      { key: "platform-onboard", label: "Onboard New Tenant", icon: "Sparkles", to: "/app/platform/onboard", roles: ["platform_owner"] },
    ],
  },
];

export function filterNavForRole(role) {
  return NAV_GROUPS.map((group) => ({
    ...group,
    items: group.items.filter((it) => it.roles === "*" || it.roles.includes(role)),
  })).filter((g) => g.items.length > 0);
}

export const ROLE_LABELS = {
  platform_owner: "Platform Owner",
  super_admin: "Super Admin",
  company_admin: "Company Admin",
  regional_manager: "Regional Manager",
  sales_executive: "Sales Executive",
  distributor: "Distributor",
  distributor_accountant: "Distributor Accountant",
  retailer: "Retailer",
  customer: "Customer",
};

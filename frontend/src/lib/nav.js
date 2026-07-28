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
      { key: "invoices", label: "Invoices", icon: "FileText", to: "/app/invoices", roles: ["super_admin", "company_admin", "regional_manager", "distributor", "distributor_accountant", "retailer", "customer"] },
    ],
  },
  {
    label: "Finance",
    items: [
      { key: "payments", label: "Payments", icon: "CreditCard", to: "/app/payments", roles: ["super_admin", "company_admin", "regional_manager", "distributor", "distributor_accountant"] },
      { key: "ledger", label: "Ledger", icon: "BookOpen", to: "/app/ledger", roles: ["super_admin", "company_admin", "regional_manager", "distributor", "distributor_accountant"] },
      { key: "expenses", label: "Expenses", icon: "Receipt", to: "/app/expenses", roles: ["super_admin", "company_admin", "regional_manager", "distributor_accountant"] },
    ],
  },
  {
    label: "Rewards",
    items: [
      { key: "cashback", label: "Cashback", icon: "Gift", to: "/app/cashback", roles: ["super_admin", "company_admin", "regional_manager", "sales_executive", "retailer"] },
      { key: "coupons", label: "Coupons", icon: "Ticket", to: "/app/coupons", roles: ["super_admin", "company_admin", "regional_manager", "sales_executive"] },
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
      { key: "notifications", label: "Notifications", icon: "Bell", to: "/app/notifications", roles: "*" },
      { key: "ai-assistant", label: "AI Assistant", icon: "Sparkles", to: "/app/ai-assistant", roles: "*" },
      { key: "settings", label: "Settings", icon: "Settings", to: "/app/settings", roles: "*" },
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
  super_admin: "Super Admin",
  company_admin: "Company Admin",
  regional_manager: "Regional Manager",
  sales_executive: "Sales Executive",
  distributor: "Distributor",
  distributor_accountant: "Distributor Accountant",
  retailer: "Retailer",
  customer: "Customer",
};

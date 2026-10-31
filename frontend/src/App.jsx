import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AuthProvider } from "./context/AuthContext";
import { RealtimeProvider } from "./realtime/RealtimeProvider.jsx";
import ProtectedRoute from "./components/ProtectedRoute";

import Login from "./pages/Login";
import Register from "./pages/Register";
import ForgotPassword from "./pages/ForgotPassword.jsx";
import ResetPassword from "./pages/ResetPassword.jsx";
import Account from "./pages/Account.jsx";
import Dashboard from "./pages/Dashboard";
import Roles from "./pages/Roles";
import Inventory from "./pages/Inventory";
import Accounts from "./pages/Accounts";
import Organization from "./pages/Organization";
import Projects from "./pages/Projects";
import ProjectDetails from "./pages/ProjectDetails.jsx";
import Delivery from "./pages/Delivery.jsx";
import Business from "./pages/Business.jsx";
import Assistant from "./pages/Assistant.jsx";
import Analytics from "./pages/Analytics.jsx";
import InventoryAnalytics from "./pages/InventoryAnalytics.jsx";
import AccountsAnalytics from "./pages/AccountsAnalytics.jsx";
import OrganizationAnalytics from "./pages/OrganizationAnalytics.jsx";
import DeliveryAnalytics from "./pages/DeliveryAnalytics.jsx";
import ProjectsAnalytics from "./pages/ProjectsAnalytics.jsx";

// path, page, required permission (null = any signed-in user)
const protectedRoutes = [
  ["/dashboard", Dashboard, null],
  ["/account", Account, null],
  ["/assistant", Assistant, "ai.use"],
  ["/business", Business, null],
  ["/roles", Roles, "rbac.manage"],
  ["/inventory", Inventory, "inventory.read"],
  ["/accounts", Accounts, "accounts.read"],
  ["/organization", Organization, "organization.read"],
  ["/projects", Projects, "projects.read"],
  ["/projects/:id", ProjectDetails, "projects.read"],
  ["/delivery", Delivery, "delivery.read"],
  ["/analytics", Analytics, null],
  ["/analytics/inventory", InventoryAnalytics, "inventory.read"],
  ["/analytics/accounts", AccountsAnalytics, "accounts.read"],
  ["/analytics/organization", OrganizationAnalytics, "organization.read"],
  ["/analytics/delivery", DeliveryAnalytics, "delivery.read"],
  ["/analytics/projects", ProjectsAnalytics, "projects.read"],
];

export default function App() {
  return (
    <AuthProvider>
      <RealtimeProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/" element={<Login />} />
            <Route path="/register" element={<Register />} />
            <Route path="/forgot-password" element={<ForgotPassword />} />
            <Route path="/reset-password" element={<ResetPassword />} />
            {protectedRoutes.map(([path, Page, permission]) => (
              <Route
                key={path}
                path={path}
                element={
                  <ProtectedRoute permission={permission}>
                    <Page />
                  </ProtectedRoute>
                }
              />
            ))}
            <Route path="*" element={<Navigate to="/dashboard" replace />} />
          </Routes>
        </BrowserRouter>
      </RealtimeProvider>
    </AuthProvider>
  );
}

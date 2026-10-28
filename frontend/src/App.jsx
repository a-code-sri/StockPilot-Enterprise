import { BrowserRouter, Routes, Route } from "react-router-dom";
import { AuthProvider } from "./context/AuthContext";
import ProtectedRoute from "./components/ProtectedRoute";

import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import Roles from "./pages/Roles";
import Register from "./pages/Register";
import Inventory from "./pages/Inventory";
import Accounts from "./pages/Accounts";
import Organization from "./pages/Organization";
import Projects from "./pages/Projects";
import ProjectDetails from "./pages/ProjectDetails.jsx";
import Delivery from "./pages/Delivery.jsx";
import Analytics from "./pages/Analytics.jsx";
import InventoryAnalytics from "./pages/InventoryAnalytics.jsx";
import AccountsAnalytics from "./pages/AccountsAnalytics.jsx";
import OrganizationAnalytics from "./pages/OrganizationAnalytics.jsx";
import DeliveryAnalytics from "./pages/DeliveryAnalytics.jsx";
import  { RealtimeProvider } from "./realtime/RealtimeProvider.jsx"
function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <RealtimeProvider>
          <Routes>
            <Route path="/" element={<Login />} />

            <Route
              path="/dashboard"
              element={
                <ProtectedRoute>
                  <Dashboard />
                </ProtectedRoute>
              }
            />

            <Route
              path="/roles"
              element={
                <ProtectedRoute>
                  <Roles />
                </ProtectedRoute>
              }
            />
            <Route path="/register" element={<Register />} />
            <Route
              path="/inventory"
              element={
                <ProtectedRoute>
                  <Inventory />
                </ProtectedRoute>
              }
            />
            <Route
              path="/accounts"
              element={
                <ProtectedRoute>
                  <Accounts />
                </ProtectedRoute>
              }
            />
            <Route 
            path = "/organization"
            element = {
              <ProtectedRoute>
                <Organization />
              </ProtectedRoute>
            }/>
            <Route 
            path = "/projects"
            element = {
              <ProtectedRoute>
                <Projects />
              </ProtectedRoute>
            }/>
            <Route 
            path = "/projects/:id"
            element = {
              <ProtectedRoute>
                <ProjectDetails/>
              </ProtectedRoute>
            }/>
            <Route
              path="/delivery"
              element={
                <ProtectedRoute>
                  <Delivery />
                </ProtectedRoute>
              }
            />
            <Route
              path="/analytics"
              element={
                <ProtectedRoute>
                  <Analytics />
                </ProtectedRoute>
              }
            />

            <Route
              path="/analytics/inventory"
              element={
                <ProtectedRoute>
                  <InventoryAnalytics />
                </ProtectedRoute>
              }
            />
            <Route
            path="/analytics/accounts"
            element={
              <ProtectedRoute>
                <AccountsAnalytics />
              </ProtectedRoute>
            }
          />
          <Route
            path="/analytics/organization"
            element={
              <ProtectedRoute>
                <OrganizationAnalytics />
              </ProtectedRoute>
            }
          />
          <Route
            path="/analytics/delivery"
            element={
              <ProtectedRoute>
                <DeliveryAnalytics />
              </ProtectedRoute>
            }
          />
          </Routes>
        </RealtimeProvider>
      </BrowserRouter>
    </AuthProvider>
  );
}

export default App;
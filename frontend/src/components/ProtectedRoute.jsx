import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import Sidebar from "./Sidebar";

export default function ProtectedRoute({ children, permission }) {
  const { user, restoring, can } = useAuth();
  const location = useLocation();

  if (restoring) {
    return (
      <div className="min-h-screen bg-gray-950 text-gray-400 flex items-center justify-center">
        Loading…
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/" replace state={{ from: location.pathname }} />;
  }

  if (permission && !can(permission)) {
    return (
      <div className="flex bg-gray-950 text-gray-200 min-h-screen">
        <Sidebar />
        <div className="flex-1 p-10">
          <h1 className="text-2xl font-semibold mb-3">No access</h1>
          <p className="text-gray-400">
            Your account needs the <code className="text-indigo-300">{permission}</code> permission to open
            this page. Ask an administrator to grant it on the RBAC page.
          </p>
        </div>
      </div>
    );
  }

  return children;
}

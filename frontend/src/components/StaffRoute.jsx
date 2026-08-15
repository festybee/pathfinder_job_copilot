import { Navigate } from "react-router-dom";
import { useAuth } from "../AuthContext.jsx";

/**
 * Like ProtectedRoute, but also requires user.is_staff. The server enforces
 * this independently (IsAdminUser on the pending-users/approve endpoints) -
 * this is just for not showing the page/nav link to non-staff users.
 */
export default function StaffRoute({ children }) {
  const { user, loading } = useAuth();

  if (loading) return <p className="container">Loading...</p>;
  if (!user) return <Navigate to="/login" replace />;
  if (!user.is_staff) return <Navigate to="/jobs" replace />;

  return children;
}

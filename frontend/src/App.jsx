import { Navigate, Route, Routes } from "react-router-dom";
import NavBar from "./components/NavBar.jsx";
import ProtectedRoute from "./components/ProtectedRoute.jsx";
import LoginPage from "./pages/LoginPage.jsx";
import SignupPage from "./pages/SignupPage.jsx";
import JobsPage from "./pages/JobsPage.jsx";
import CriteriaListPage from "./pages/CriteriaListPage.jsx";
import CriteriaDetailPage from "./pages/CriteriaDetailPage.jsx";
import PortfolioPage from "./pages/PortfolioPage.jsx";
import AiAssistPage from "./pages/AiAssistPage.jsx";

export default function App() {
  return (
    <>
      <NavBar />
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/signup" element={<SignupPage />} />
        <Route
          path="/jobs"
          element={
            <ProtectedRoute>
              <JobsPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/jobs/:jobId/ai"
          element={
            <ProtectedRoute>
              <AiAssistPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/criteria"
          element={
            <ProtectedRoute>
              <CriteriaListPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/criteria/:id"
          element={
            <ProtectedRoute>
              <CriteriaDetailPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/portfolio"
          element={
            <ProtectedRoute>
              <PortfolioPage />
            </ProtectedRoute>
          }
        />
        <Route path="/" element={<Navigate to="/jobs" replace />} />
      </Routes>
    </>
  );
}

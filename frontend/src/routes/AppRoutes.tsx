import { Route, Routes } from "react-router-dom";

import { AppLayout } from "../components/AppLayout";
import { useAuth } from "../auth/AuthContext";
import { HomePage } from "../pages/HomePage";
import { LoginPage } from "../pages/LoginPage";
import { NotFoundPage } from "../pages/NotFoundPage";
import { RiskListPage } from "../pages/RiskListPage";

export function AppRoutes() {
  const { isLoading } = useAuth();

  if (isLoading) {
    return (
      <main className="session-loading" aria-live="polite">
        <p role="status">Restoring session...</p>
      </main>
    );
  }

  return (
    <Routes>
      <Route element={<AppLayout />}>
        <Route path="/" element={<HomePage />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/risks" element={<RiskListPage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  );
}

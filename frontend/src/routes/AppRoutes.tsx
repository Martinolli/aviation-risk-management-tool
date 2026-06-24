import { Route, Routes } from "react-router-dom";

import { AppLayout } from "../components/AppLayout";
import { useAuth } from "../auth/AuthContext";
import { HomePage } from "../pages/HomePage";
import { LoginPage } from "../pages/LoginPage";
import { NotFoundPage } from "../pages/NotFoundPage";
import { RiskCreatePage } from "../pages/RiskCreatePage";
import { RiskAssessmentCreatePage } from "../pages/RiskAssessmentCreatePage";
import { RiskActionCreatePage } from "../pages/RiskActionCreatePage";
import { RiskDetailPage } from "../pages/RiskDetailPage";
import { RiskListPage } from "../pages/RiskListPage";
import { RiskSubmitPage } from "../pages/RiskSubmitPage";

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
        <Route path="/risks/new" element={<RiskCreatePage />} />
        <Route
          path="/risks/:riskRecordId/assessments/new"
          element={<RiskAssessmentCreatePage />}
        />
        <Route
          path="/risks/:riskRecordId/actions/new"
          element={<RiskActionCreatePage />}
        />
        <Route path="/risks/:riskRecordId/submit" element={<RiskSubmitPage />} />
        <Route path="/risks/:riskRecordId" element={<RiskDetailPage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  );
}

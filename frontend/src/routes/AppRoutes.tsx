import { Route, Routes } from "react-router-dom";

import { AppLayout } from "../components/AppLayout";
import { useAuth } from "../auth/AuthContext";
import { AdminGovernancePage } from "../pages/AdminGovernancePage";
import { AuditTrailPage } from "../pages/AuditTrailPage";
import { CommitteeMeetingDetailPage } from "../pages/CommitteeMeetingDetailPage";
import { CommitteeMeetingPacksPage } from "../pages/CommitteeMeetingPacksPage";
import { CommitteeMeetingsPage } from "../pages/CommitteeMeetingsPage";
import { HomePage } from "../pages/HomePage";
import { LoginPage } from "../pages/LoginPage";
import { ManagementDashboardPage } from "../pages/ManagementDashboardPage";
import { MyDecisionQueuePage } from "../pages/MyDecisionQueuePage";
import { MyActionsPage } from "../pages/MyActionsPage";
import { MyMonitoringPage } from "../pages/MyMonitoringPage";
import { NotificationsPage } from "../pages/NotificationsPage";
import { NotFoundPage } from "../pages/NotFoundPage";
import { ReportsPage } from "../pages/ReportsPage";
import { RiskCreatePage } from "../pages/RiskCreatePage";
import { RiskAssessmentCreatePage } from "../pages/RiskAssessmentCreatePage";
import { RiskActionCreatePage } from "../pages/RiskActionCreatePage";
import { RiskActionCompletePage } from "../pages/RiskActionCompletePage";
import { RiskDetailPage } from "../pages/RiskDetailPage";
import { RiskDashboardPage } from "../pages/RiskDashboardPage";
import { RiskDecisionCreatePage } from "../pages/RiskDecisionCreatePage";
import { RiskListPage } from "../pages/RiskListPage";
import { RiskPackageEditPage } from "../pages/RiskPackageEditPage";
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
        <Route path="/dashboard" element={<RiskDashboardPage />} />
        <Route
          path="/management-dashboard"
          element={<ManagementDashboardPage />}
        />
        <Route path="/notifications" element={<NotificationsPage />} />
        <Route path="/risks" element={<RiskListPage />} />
        <Route path="/my-decisions" element={<MyDecisionQueuePage />} />
        <Route path="/my-actions" element={<MyActionsPage />} />
        <Route path="/my-monitoring" element={<MyMonitoringPage />} />
        <Route
          path="/committee-meeting-packs"
          element={<CommitteeMeetingPacksPage />}
        />
        <Route path="/committee-meetings" element={<CommitteeMeetingsPage />} />
        <Route
          path="/committee-meetings/:meetingId"
          element={<CommitteeMeetingDetailPage />}
        />
        <Route path="/reports" element={<ReportsPage />} />
        <Route path="/audit-trail" element={<AuditTrailPage />} />
        <Route path="/admin/governance" element={<AdminGovernancePage />} />
        <Route path="/risks/new" element={<RiskCreatePage />} />
        <Route
          path="/risks/:riskRecordId/assessments/new"
          element={<RiskAssessmentCreatePage assessmentType="INITIAL" />}
        />
        <Route
          path="/risks/:riskRecordId/assessments/initial/new"
          element={<RiskAssessmentCreatePage assessmentType="INITIAL" />}
        />
        <Route
          path="/risks/:riskRecordId/assessments/residual/new"
          element={<RiskAssessmentCreatePage assessmentType="RESIDUAL" />}
        />
        <Route
          path="/risks/:riskRecordId/actions/new"
          element={<RiskActionCreatePage />}
        />
        <Route
          path="/risks/:riskRecordId/actions/:riskActionId/complete"
          element={<RiskActionCompletePage />}
        />
        <Route
          path="/risks/:riskRecordId/decisions/new"
          element={<RiskDecisionCreatePage />}
        />
        <Route path="/risks/:riskRecordId/submit" element={<RiskSubmitPage />} />
        <Route
          path="/risks/:riskRecordId/package/edit"
          element={<RiskPackageEditPage />}
        />
        <Route path="/risks/:riskRecordId" element={<RiskDetailPage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  );
}

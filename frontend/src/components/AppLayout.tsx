import { useEffect, useState } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";

import { getMyNotifications } from "../api/notifications";
import { useAuth } from "../auth/AuthContext";

export function AppLayout() {
  const { isAuthenticated, logout, token, user } = useAuth();
  const navigate = useNavigate();
  const [attentionCount, setAttentionCount] = useState<number | null>(null);

  useEffect(() => {
    let isCurrent = true;
    if (!isAuthenticated || !token) {
      setAttentionCount(null);
      return;
    }
    const tokenToUse = token;

    async function loadAttentionCount() {
      try {
        const summary = await getMyNotifications(tokenToUse, {
          includeInfo: false,
          limit: 50,
        });
        if (isCurrent) {
          setAttentionCount(summary.critical_count + summary.warning_count);
        }
      } catch {
        if (isCurrent) {
          setAttentionCount(null);
        }
      }
    }

    void loadAttentionCount();
    return () => {
      isCurrent = false;
    };
  }, [isAuthenticated, token]);

  function handleLogout() {
    logout();
    navigate("/", { replace: true });
  }

  return (
    <div className="app-shell">
      <header className="app-header">
        <div className="header-content">
          <NavLink className="app-name" to="/">
            Aviation Risk Management Tool
          </NavLink>
          <nav aria-label="Primary navigation" className="primary-nav">
            <NavLink to="/">Home</NavLink>
            {!isAuthenticated && <NavLink to="/login">Login</NavLink>}
            {isAuthenticated && (
              <>
                <NavLink to="/dashboard">Dashboard</NavLink>
                <NavLink to="/management-dashboard">Management</NavLink>
                <NavLink to="/notifications">
                  <span>Notifications</span>
                  {attentionCount !== null && attentionCount > 0 && (
                    <span className="nav-notification-badge">
                      {attentionCount}
                    </span>
                  )}
                </NavLink>
                <NavLink to="/risks">Risks</NavLink>
                <NavLink to="/my-decisions">My Queue</NavLink>
                <NavLink to="/my-actions">My Actions</NavLink>
                <NavLink to="/my-monitoring">My Monitoring</NavLink>
                <NavLink to="/committee-meeting-packs">Meeting Packs</NavLink>
                <NavLink to="/committee-meetings">Meetings</NavLink>
                <NavLink to="/reports">Reports</NavLink>
                <NavLink to="/audit-trail">Audit Trail</NavLink>
                <NavLink to="/admin/governance">Admin</NavLink>
                <span className="nav-placeholder" title="Coming soon">
                  Committees <small>Coming soon</small>
                </span>
              </>
            )}
          </nav>
          {isAuthenticated && user && (
            <div className="user-controls">
              <span className="user-summary">
                <strong>{user.display_name || user.email}</strong>
                <span>{user.email}</span>
              </span>
              <button
                className="logout-button"
                onClick={handleLogout}
                type="button"
              >
                Logout
              </button>
            </div>
          )}
        </div>
      </header>
      <main className="main-content">
        <Outlet />
      </main>
    </div>
  );
}

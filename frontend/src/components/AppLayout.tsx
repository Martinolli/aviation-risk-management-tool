import { NavLink, Outlet } from "react-router-dom";

import { useAuth } from "../auth/AuthContext";

export function AppLayout() {
  const { isAuthenticated, logout, user } = useAuth();

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
          </nav>
          {isAuthenticated && user && (
            <div className="user-controls">
              <span className="user-summary">
                <strong>{user.display_name || user.email}</strong>
                <span>{user.email}</span>
              </span>
              <button className="logout-button" onClick={logout} type="button">
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

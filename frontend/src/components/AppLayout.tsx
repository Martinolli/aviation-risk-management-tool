import { NavLink, Outlet } from "react-router-dom";

export function AppLayout() {
  return (
    <div className="app-shell">
      <header className="app-header">
        <div className="header-content">
          <NavLink className="app-name" to="/">
            Aviation Risk Management Tool
          </NavLink>
          <nav aria-label="Primary navigation" className="primary-nav">
            <NavLink to="/">Home</NavLink>
            <NavLink to="/login">Login</NavLink>
          </nav>
        </div>
      </header>
      <main className="main-content">
        <Outlet />
      </main>
    </div>
  );
}

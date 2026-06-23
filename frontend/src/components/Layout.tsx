import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";

const LINKS = [
  { to: "/", label: "Дашборд", end: true },
  { to: "/resume", label: "Резюме" },
  { to: "/vacancy", label: "Вакансия" },
  { to: "/questions", label: "Вопросы" },
  { to: "/interview", label: "Интервью" },
  { to: "/tutor", label: "AI-тьютор" },
  { to: "/billing", label: "Тариф" },
];

export default function Layout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">🐍 AI Career Coach</div>
        <nav className="nav">
          {LINKS.map((l) => (
            <NavLink
              key={l.to}
              to={l.to}
              end={l.end}
              className={({ isActive }) => "nav-link" + (isActive ? " active" : "")}
            >
              {l.label}
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-footer">
          <div className="user-email" title={user?.email}>
            {user?.email}
          </div>
          {user?.level && <div className="badge">{user.level}</div>}
          <button
            className="btn ghost"
            onClick={() => {
              logout();
              navigate("/login");
            }}
          >
            Выйти
          </button>
        </div>
      </aside>
      <main className="content">
        <Outlet />
      </main>
    </div>
  );
}

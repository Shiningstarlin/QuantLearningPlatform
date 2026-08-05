import { BarChart3, BrainCircuit, History, LineChart, LogOut, Settings, UserCircle, WalletCards } from "lucide-react";
import { useEffect, useState } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";

import { apiRequest, clearToken, CurrentUser, getToken } from "../lib/api";

const navItems = [
  { to: "/tasks", label: "我的账户", icon: WalletCards },
  { to: "/market-board", label: "行情看板", icon: LineChart },
  { to: "/factor-radar", label: "因子雷达", icon: BrainCircuit },
  { to: "/backtests", label: "策略回测", icon: History },
  { to: "/settings", label: "设置", icon: Settings }
];

export function AppLayout() {
  const navigate = useNavigate();
  const [user, setUser] = useState<CurrentUser | null>(null);

  useEffect(() => {
    if (!getToken()) {
      setUser(null);
      return;
    }
    apiRequest<CurrentUser>("/api/auth/me")
      .then(setUser)
      .catch(() => {
        clearToken();
        setUser(null);
      });
  }, []);

  function logout() {
    clearToken();
    setUser(null);
    navigate("/login");
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <WalletCards size={24} />
          <span>Quant Lab</span>
        </div>
        <nav>
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink key={item.to} to={item.to} className={({ isActive }) => (isActive ? "active" : "")}>
                <Icon size={18} />
                <span>{item.label}</span>
              </NavLink>
            );
          })}
        </nav>
        <div className="sidebar-account">
          {user ? (
            <>
              <div className="account-line">
                <UserCircle size={18} />
                <span>{user.display_name}</span>
              </div>
              <small>{user.email}</small>
              <button className="sidebar-button" type="button" onClick={logout}>
                <LogOut size={16} />
                登出
              </button>
            </>
          ) : (
            <>
              <div className="account-line">
                <BarChart3 size={18} />
                <span>仅模拟资金</span>
              </div>
              <button className="sidebar-button" type="button" onClick={() => navigate("/login")}>
                登录
              </button>
            </>
          )}
        </div>
      </aside>
      <main className="main-panel">
        <Outlet />
      </main>
    </div>
  );
}

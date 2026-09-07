import { useEffect, useState } from "react";
import { Navigate, NavLink, useLocation } from "react-router-dom";
import ChatPage from "./pages/ChatPage";
import DashboardPage from "./pages/DashboardPage";
import { canSeeAnalytics, decodeCurrentUser, initTokenFromUrl, type IcsaUser } from "./utils/auth";

const PSS_URL = import.meta.env.VITE_PSS_URL || "http://localhost:5174/";

export default function App() {
    const { pathname } = useLocation();
    const pageName = pathname === "/dashboard" ? "Analytics Dashboard" : "Citizen Service Assistant";

    const [user, setUser] = useState<IcsaUser | null>(null);
    useEffect(() => {
        initTokenFromUrl();
        setUser(decodeCurrentUser());
    }, []);

    const analyticsAllowed = canSeeAnalytics(user);

    if (pathname === "/dashboard" && !analyticsAllowed) {
        return <Navigate to="/" replace />;
    }

    return (
        <div className="app">
            <header className="top-nav">
                <div className="brand">
                    <div className="brand-seal-wrapper">
                        <svg className="brand-seal-icon" viewBox="0 0 24 24" fill="none">
                            <path d="M12 2L15.09 8.26L22 9.27L17 14.14L18.18 21.02L12 17.77L5.82 21.02L7 14.14L2 9.27L8.91 8.26L12 2Z" fill="url(#goldGradApp)" stroke="#F3C63F" strokeWidth="1.2" />
                            <defs>
                                <linearGradient id="goldGradApp" x1="2" y1="2" x2="22" y2="21" gradientUnits="userSpaceOnUse">
                                    <stop stopColor="#F8D66D" />
                                    <stop offset="1" stopColor="#B8860B" />
                                </linearGradient>
                            </defs>
                        </svg>
                    </div>
                    <div className="brand-text-group">
                        <div className="brand-title-row">
                            <span className="brand-title">Planning &amp; Standards System</span>
                            <span className="brand-badge">ICSA v1.0</span>
                        </div>
                        <span className="brand-sub">Polytechnic University of the Philippines - Caloocan Campus</span>
                    </div>
                </div>
                <div className="top-nav-right">
                    <nav className="nav-tabs">
                        <NavLink to="/" end className={({ isActive }) => (isActive ? "tab active" : "tab")}>
                            <span>Assistant</span>
                        </NavLink>
                        {analyticsAllowed && (
                            <NavLink to="/dashboard" className={({ isActive }) => (isActive ? "tab active" : "tab")}>
                                <span>Analytics</span>
                            </NavLink>
                        )}
                    </nav>
                    <a href={PSS_URL} className="btn-back-to-pss" title="Back to Planning & Standards System">
                        <span>Back to PSS</span>
                    </a>
                </div>
            </header>

            <div className="page-header">
                <div className="breadcrumb-box">
                    <span className="breadcrumb-text">
                        PSS / ICSA / <strong>{pageName}</strong>
                    </span>
                </div>
                <div className="status-badge">
                    <span className="status-pulse-dot"></span>
                    <span>CITIZEN'S CHARTER - LIVE</span>
                </div>
            </div>

            <main className={`main ${pathname === "/dashboard" ? "main-dashboard" : ""}`}>
                <div style={{ display: pathname === "/dashboard" ? "none" : "block", height: "100%" }}>
                    <ChatPage />
                </div>
                {analyticsAllowed && (
                    <div style={{ display: pathname === "/dashboard" ? "block" : "none", height: "100%" }}>
                        <DashboardPage user={user} />
                    </div>
                )}
            </main>
        </div>
    );
}
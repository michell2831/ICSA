import { useEffect, useState } from "react";
import {
    getAvgResponseTime,
    getConfidenceDistribution,
    getEscalationRate,
    getQueryVolume,
    getRecentInteractions,
    getServicesCount,
    getTopServices,
    type ServicesCountResponse,
} from "../api/analyticsApi";
import ConfidenceDistributionChart from "../components/charts/ConfidenceDistributionChart";
import QueryVolumeChart from "../components/charts/QueryVolumeChart";
import TopServicesChart from "../components/charts/TopServicesChart";
import { OFFICE_CODE_TO_LABEL, type IcsaUser } from "../utils/auth";
import type { ConfidenceBucket, EscalationRate, QueryVolumePoint, RecentInteraction, TopService } from "../types";

const OFFICE_OPTIONS = ["All Offices", "Academic", "Administrative", "OSAS"];

interface DashboardPageProps {
    user: IcsaUser | null;
}

export default function DashboardPage({ user }: DashboardPageProps) {
    // ENH-01: office scoping driven by the decoded PSS token, NOT a client-
    // editable URL query param. Super Admin / Planning Officer (isCrossOffice)
    // get the real, changeable filter below; every other role is permanently
    // locked to their own office - there is no click-to-unlock escape hatch,
    // because the server-side check in icsa-api/utils/auth.py
    // resolve_scoped_office() ignores whatever the client claims anyway for
    // office-locked users. The lock badge here is just an honest reflection
    // of that, not the enforcement itself.
    const isCrossOffice = !!user?.isCrossOffice;
    const lockedOfficeLabel = user ? (OFFICE_CODE_TO_LABEL[user.office] || user.office) : null;

    const [selectedOffice, setSelectedOffice] = useState(
        isCrossOffice ? "All Offices" : (lockedOfficeLabel || "All Offices")
    );
    const [lastUpdated, setLastUpdated] = useState("");
    const [topServices, setTopServices] = useState<TopService[]>([]);
    const [queryVolume, setQueryVolume] = useState<QueryVolumePoint[]>([]);
    const [confidenceData, setConfidenceData] = useState<ConfidenceBucket[]>([]);
    const [escalationData, setEscalationData] = useState<EscalationRate>({
        rate: 0,
        total: 0,
        escalated: 0,
    });
    const [avgResponseMs, setAvgResponseMs] = useState<number | null>(null);
    const [recentInteractions, setRecentInteractions] = useState<RecentInteraction[]>([]);
    const [servicesCount, setServicesCount] = useState<ServicesCountResponse | null>(null);
    const [isFullLog, setIsFullLog] = useState(false);

    // The office actually used for every fetch. For locked users this is
    // NOT selectedOffice (there's no UI to change it anyway) - it's always
    // derived fresh from the token, so if `user` resolves a tick after first
    // render (async token decode), data still ends up scoped correctly
    // instead of briefly fetching unscoped "All Offices" data.
    const effectiveOffice = isCrossOffice
        ? (selectedOffice === "All Offices" ? undefined : selectedOffice)
        : lockedOfficeLabel || undefined;

    const fetchAllData = (officeFilter?: string) => {
        getTopServices(officeFilter)
            .then((data) => setTopServices(data || []))
            .catch(() => { });

        getQueryVolume(officeFilter)
            .then((data) => setQueryVolume(data || []))
            .catch(() => { });

        getEscalationRate(officeFilter)
            .then((data) => data && setEscalationData(data))
            .catch(() => { });

        getAvgResponseTime(officeFilter)
            .then((data) => data && setAvgResponseMs(data.avg_response_time_ms))
            .catch(() => { });

        getConfidenceDistribution(officeFilter)
            .then((data) => data && setConfidenceData(data))
            .catch(() => { });

        getRecentInteractions(officeFilter, isFullLog ? 50 : 15)
            .then((data) => data && setRecentInteractions(data))
            .catch(() => { });

        getServicesCount()
            .then((data) => data && setServicesCount(data))
            .catch(() => { });

        setLastUpdated(new Date().toLocaleString("en-PH", { timeZone: "Asia/Manila" }));
    };

    useEffect(() => {
        fetchAllData(effectiveOffice);

        // Simple 8-second polling refresh
        const intervalId = setInterval(() => {
            fetchAllData(effectiveOffice);
        }, 8000);

        return () => clearInterval(intervalId);
    }, [effectiveOffice, isFullLog]);

    const resolutionRate = escalationData.total > 0 ? Math.round(100 - escalationData.rate) : 0;

    const getConfBadge = (conf: number) => {
        const pct = Math.round(conf * 100);
        if (conf >= 0.70) return <span className="conf-badge conf-high">{pct}% Exact Match</span>;
        if (conf >= 0.40) return <span className="conf-badge conf-medium">{pct}% Good Match</span>;
        return <span className="conf-badge conf-low">{pct}% Low Match</span>;
    };

    const displayOffice = isCrossOffice ? selectedOffice : (lockedOfficeLabel || "Your Office");

    return (
        <div className="dash-container">
            {/* TOOLBAR */}
            <div className="dash-header-row">
                <div>
                    <h1 className="dash-title">
                        {displayOffice === "All Offices" ? "PUP Citizen Services Assistant & Analytics" : `${displayOffice} Dashboard`}
                    </h1>
                    <p className="dash-subtitle">
                        Overview of citizen inquiries, AI match accuracy, and active PUP services
                    </p>
                </div>
                <div className="dash-toolbar-controls">
                    {isCrossOffice ? (
                        <select
                            value={selectedOffice}
                            onChange={(e) => setSelectedOffice(e.target.value)}
                            className="office-select"
                        >
                            {OFFICE_OPTIONS.map((o) => (
                                <option key={o} value={o}>
                                    {o}
                                </option>
                            ))}
                        </select>
                    ) : (
                        // ENH-01: Office Heads get a fixed, non-interactive badge - no
                        // click-to-unlock, no dropdown. Purely cosmetic; the real
                        // scoping is enforced server-side in icsa-api/utils/auth.py
                        // regardless of anything this component does.
                        <div
                            className="office-select rbac-locked"
                            title="Locked by PSS Role-Based Access Control"
                            style={{ display: "flex", alignItems: "center", gap: "6px", cursor: "default", background: "#f8f9fa", padding: "8px 16px", borderRadius: "20px", border: "1px solid #e5e7eb", fontSize: "14px", fontWeight: "500", color: "#374151" }}
                        >
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#ef4444" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                <rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect>
                                <path d="M7 11V7a5 5 0 0 1 10 0v4"></path>
                            </svg>
                            {displayOffice} Office
                        </div>
                    )}
                </div>
            </div>

            {/* TOP 4 CHATBOT METRIC CARDS */}
            <div className="top-metrics-grid">
                <div className="metric-card card-maroon">
                    <span className="metric-label">TOTAL CITIZEN INQUIRIES</span>
                    <div className="metric-value">{escalationData.total}</div>
                    <span className="metric-trend green">^ Live Inquiry Feed</span>
                </div>
                <div className="metric-card card-purple">
                    <span className="metric-label">TOTAL PUP SERVICES AVAILABLE</span>
                    <div className="metric-value">{servicesCount?.total ?? 54}</div>
                    <span className="metric-trend green">^ Synced from Catalogue</span>
                </div>
                <div className="metric-card card-green">
                    <span className="metric-label">AI RESOLUTION PERFORMANCE</span>
                    <div className="metric-value">{resolutionRate}%</div>
                    <span className="metric-trend green">^ High AI Accuracy</span>
                </div>
                <div className="metric-card card-gold">
                    <span className="metric-label">AVERAGE ANSWER SPEED</span>
                    <div className="metric-value">
                        {avgResponseMs !== null ? `${Math.round(avgResponseMs)}ms` : "-"}
                    </div>
                    <span className="metric-trend green">^ Fast AI Processing</span>
                </div>
            </div>

            {/* MAIN 2-COLUMN GRID */}
            <div className="dash-main-grid">
                {/* LEFT COLUMN */}
                <div className="dash-column">
                    {/* Row 1 Left: Top Services Chart */}
                    <div className="dash-card">
                        <div className="dash-card-header">
                            <div>
                                <h2 className="dash-card-title">Most Requested PUP Services</h2>
                                <p className="dash-card-subtitle">
                                    The PUP services citizens ask about most often
                                </p>
                            </div>
                            <span className="dash-pill-badge live">Live Activity Log</span>
                        </div>
                        <TopServicesChart data={topServices} />
                    </div>

                    {/* Row 2 Left: Active PSS Service Catalogue Inventory Widget */}
                    <div className="dash-card kpi-card-equal">
                        <div className="dash-card-header kpi-header-equal">
                            <div>
                                <h2 className="dash-card-title">PUP Services Inventory per Office</h2>
                                <p className="dash-card-subtitle">
                                    Breakdown of available services offered across PUP offices
                                </p>
                            </div>
                            <span className="dash-pill-badge live">Official Catalogue</span>
                        </div>

                        <div className="kpi-body">
                            <div className="services-count-total-box">
                                <span className="total-num">{servicesCount?.total ?? 54}</span>
                                <span className="total-lbl">Total Active Services</span>
                            </div>

                            <div className="kpi-bars-list">
                                {Object.entries(servicesCount?.per_office || { Academic: 9, Administrative: 20, OSAS: 25 }).map(
                                    ([off, count]) => {
                                        const total = servicesCount?.total || 54;
                                        const pct = Math.round((count / total) * 100);
                                        return (
                                            <div key={off} className="kpi-bar-row">
                                                <span className="kpi-office-name">{off} Office</span>
                                                <div className="kpi-track">
                                                    <div className="kpi-fill" style={{ width: `${pct}%` }} />
                                                </div>
                                                <span className="kpi-percentage">{count} ({pct}%)</span>
                                            </div>
                                        );
                                    }
                                )}
                            </div>
                        </div>
                    </div>

                    {/* Row 3 Left: AI Search Match Accuracy Bar Chart */}
                    <div className="dash-card">
                        <div className="dash-card-header">
                            <div>
                                <h2 className="dash-card-title">AI Search Match Accuracy</h2>
                                <p className="dash-card-subtitle">
                                    How accurately the chatbot matched citizen questions to official PUP services
                                </p>
                            </div>
                            <span className="dash-pill-badge live">Accuracy Levels</span>
                        </div>
                        <ConfidenceDistributionChart data={confidenceData} />
                    </div>
                </div>

                {/* RIGHT COLUMN */}
                <div className="dash-column">
                    {/* Row 1 Right: Daily Citizen Inquiry Volume Line Chart */}
                    <div className="dash-card">
                        <div className="dash-card-header">
                            <div>
                                <h2 className="dash-card-title">Daily Inquiries Received (Last 7 Days)</h2>
                                <p className="dash-card-subtitle">
                                    Number of questions asked by citizens each day
                                </p>
                            </div>
                            <span className="dash-pill-badge beige">7-Day Overview</span>
                        </div>
                        <QueryVolumeChart data={queryVolume} />
                    </div>

                    {/* Row 2 Right: AI Automated Resolution vs Escalation Rate */}
                    <div className="dash-card kpi-card-equal">
                        <div className="dash-card-header kpi-header-equal">
                            <div>
                                <h2 className="dash-card-title">AI Direct Answers vs Staff Referrals</h2>
                                <p className="dash-card-subtitle">
                                    Share of questions solved directly by AI versus referred to office staff
                                </p>
                            </div>
                            <span className="dash-pill-badge live">Live Overview</span>
                        </div>

                        <div className="kpi-body">
                            <div className="donut-wrapper">
                                <svg className="donut-svg" viewBox="0 0 100 100">
                                    <circle className="donut-bg" cx="50" cy="50" r="38" />
                                    <circle
                                        className="donut-fill"
                                        cx="50"
                                        cy="50"
                                        r="38"
                                        strokeDasharray="238.76"
                                        strokeDashoffset={238.76 * (1 - resolutionRate / 100)}
                                    />
                                </svg>
                                <div className="donut-text">
                                    <span className="donut-val">{resolutionRate}%</span>
                                    <span className="donut-sub">AUTOMATED</span>
                                </div>
                            </div>

                            <div className="kpi-bars-list">
                                <div className="kpi-bar-row">
                                    <span className="kpi-office-name">Answered by AI</span>
                                    <div className="kpi-track">
                                        <div className="kpi-fill" style={{ width: `${resolutionRate}%` }} />
                                    </div>
                                    <span className="kpi-percentage">{resolutionRate}%</span>
                                </div>
                                <div className="kpi-bar-row">
                                    <span className="kpi-office-name">Referred to Staff</span>
                                    <div className="kpi-track">
                                        <div
                                            className="kpi-fill"
                                            style={{
                                                width: `${escalationData.rate}%`,
                                                backgroundColor: "#DC2626",
                                            }}
                                        />
                                    </div>
                                    <span className="kpi-percentage">{escalationData.rate}%</span>
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* Row 3 Right: Live Citizen Interaction Activity Log */}
                    <div className="dash-card">
                        <div className="dash-card-header">
                            <div>
                                <h2 className="dash-card-title">Recent Citizen Questions Log</h2>
                                <p className="dash-card-subtitle">
                                    Recent questions asked by citizens, updated automatically
                                </p>
                            </div>
                            <span className="dash-pill-badge maroon">Live Feed</span>
                        </div>

                        <div className="sla-table-wrapper">
                            <table className="sla-table">
                                <thead>
                                    <tr>
                                        <th>CITIZEN QUESTION & MATCHED PUP SERVICE</th>
                                        <th>OFFICE RESPONSIBLE</th>
                                        <th className="align-right">ANSWER SPEED</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {recentInteractions.map((item, idx) => (
                                        <tr key={idx}>
                                            <td>
                                                <div className="table-service-name">"{item.query}"</div>
                                                <div className="table-office-sub">
                                                    Match: <strong>{item.matched_service || "No match"}</strong>
                                                    {getConfBadge(item.confidence)}
                                                </div>
                                            </td>
                                            <td>
                                                <span className="meta-pill office">{item.office || "General"}</span>
                                            </td>
                                            <td className="align-right time-cell">{item.response_time_ms}ms</td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>

                        <div className="table-footer-bar">
                            <span className="dash-card-subtitle">
                                Showing {recentInteractions.length} entries
                            </span>
                            <button
                                className="btn-view-full-log"
                                onClick={() => setIsFullLog((prev) => !prev)}
                            >
                                {isFullLog ? "Collapse Entries" : "Expand All Entries"}
                            </button>
                        </div>
                    </div>
                </div>
            </div>

            <div className="dash-footer">
                <span>Last updated: {lastUpdated} (auto-refreshing)</span>
            </div>
        </div>
    );
}
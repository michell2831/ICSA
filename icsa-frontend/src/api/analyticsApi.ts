// FE-02: analytics API client with mock mode. Mock names = real PUP services.
import axios from "axios";
import { getToken } from "../utils/auth";
import type {
    AvgResponseTime,
    ConfidenceBucket,
    EscalationRate,
    QueryVolumePoint,
    RecentInteraction,
    TopService
} from "../types";

const BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";
const MOCK = import.meta.env.VITE_USE_MOCK_API === "true";

// ENH-01: every analytics endpoint now requires this. Missing/expired token
// means the backend returns 401/403 - the caller (DashboardPage) already
// won't be mounted in that case (see App.tsx canSeeAnalytics gate), but we
// still attach it defensively here so a stale/reused component instance
// can't slip a request through unauthenticated.
function authHeaders(): Record<string, string> {
    const token = getToken();
    return token ? { Authorization: `Bearer ${token}` } : {};
}

export const MOCK_TOP_SERVICES: TopService[] = [
    { service_name: "Issuance of Medical Certificate", office: "Administrative", query_count: 42 },
    { service_name: "Application for New Identification Card", office: "OSAS", query_count: 38 },
    { service_name: "Processing of Application for Cross-Enrollment", office: "Academic", query_count: 31 },
    { service_name: "Counseling Service", office: "OSAS", query_count: 24 },
    { service_name: "Processing of Manual Enrollment", office: "Academic", query_count: 19 },
    { service_name: "Issuance of Recommendation Letter", office: "OSAS", query_count: 14 },
    { service_name: "Processing of Application for Overload of Subjects", office: "Academic", query_count: 9 },
];

export const MOCK_QUERY_VOLUME: QueryVolumePoint[] = [
    { date: "2026-07-07", count: 12 },
    { date: "2026-07-08", count: 18 },
    { date: "2026-07-09", count: 22 },
    { date: "2026-07-10", count: 15 },
    { date: "2026-07-11", count: 30 },
    { date: "2026-07-12", count: 25 },
    { date: "2026-07-13", count: 20 },
];

export const MOCK_ESCALATION: EscalationRate = { rate: 12.3, total: 178, escalated: 22 };

export const MOCK_AVG_RESPONSE_TIME: AvgResponseTime = { avg_response_time_ms: 162.4 };

export const MOCK_RECENT_INTERACTIONS: RecentInteraction[] = [
    { query: "How do I get a new student ID?", matched_service: "Application for New Identification Card", office: "OSAS", confidence: 0.88, response_time_ms: 162, escalated: false },
    { query: "What do I need for a medical certificate?", matched_service: "Issuance of Medical Certificate", office: "Administrative", confidence: 0.92, response_time_ms: 185, escalated: false },
    { query: "Paano mag-apply ng cross-enrollment?", matched_service: "Processing of Application for Cross-Enrollment", office: "Academic", confidence: 0.84, response_time_ms: 210, escalated: false },
    { query: "Ano ang kailangan para sa counseling appointment?", matched_service: "Counseling Service", office: "OSAS", confidence: 0.79, response_time_ms: 140, escalated: false },
    { query: "Paano mag-request ng Good Moral Certificate?", matched_service: "Issuance of Good Moral Certificate", office: "OSAS", confidence: 0.70, response_time_ms: 641, escalated: true },
];

export const MOCK_CONFIDENCE_DISTRIBUTION: ConfidenceBucket[] = [
    { bucket: "0-30% (Low Match)", count: 3, color: "#DC2626" },
    { bucket: "31-50% (Fair Match)", count: 8, color: "#F59E0B" },
    { bucket: "51-70% (Good Match)", count: 22, color: "#10B981" },
    { bucket: "71-100% (High Match)", count: 45, color: "#059669" },
];

export async function getTopServices(office?: string): Promise<TopService[]> {
    if (MOCK) return office ? MOCK_TOP_SERVICES.filter((s) => s.office === office) : MOCK_TOP_SERVICES;
    const r = await axios.get<TopService[]>(`${BASE}/api/analytics/top-services`, {
        params: office ? { office } : {},
        headers: authHeaders(),
    });
    return r.data;
}

export async function getQueryVolume(office?: string): Promise<QueryVolumePoint[]> {
    if (MOCK) return MOCK_QUERY_VOLUME;
    const r = await axios.get<QueryVolumePoint[]>(`${BASE}/api/analytics/query-volume`, {
        params: { period: "weekly", ...(office ? { office } : {}) },
        headers: authHeaders(),
    });
    return r.data;
}

export async function getEscalationRate(office?: string): Promise<EscalationRate> {
    if (MOCK) return MOCK_ESCALATION;
    const r = await axios.get<EscalationRate>(`${BASE}/api/analytics/escalation-rate`, {
        params: office ? { office } : {},
        headers: authHeaders(),
    });
    return r.data;
}

export async function getAvgResponseTime(office?: string): Promise<AvgResponseTime> {
    if (MOCK) return MOCK_AVG_RESPONSE_TIME;
    const r = await axios.get<AvgResponseTime>(`${BASE}/api/analytics/avg-response-time`, {
        params: office ? { office } : {},
        headers: authHeaders(),
    });
    return r.data;
}

export async function getRecentInteractions(office?: string, limit: number = 15): Promise<RecentInteraction[]> {
    if (MOCK) return office ? MOCK_RECENT_INTERACTIONS.filter((i) => i.office === office) : MOCK_RECENT_INTERACTIONS;
    const r = await axios.get<RecentInteraction[]>(`${BASE}/api/analytics/recent-interactions`, {
        params: { limit, ...(office ? { office } : {}) },
        headers: authHeaders(),
    });
    return r.data;
}

export async function getConfidenceDistribution(office?: string): Promise<ConfidenceBucket[]> {
    if (MOCK) return MOCK_CONFIDENCE_DISTRIBUTION;
    try {
        const r = await axios.get<ConfidenceBucket[]>(`${BASE}/api/analytics/confidence-distribution`, {
            params: office ? { office } : {},
            headers: authHeaders(),
        });
        return r.data;
    } catch {
        return MOCK_CONFIDENCE_DISTRIBUTION;
    }
}

export interface ServicesCountResponse {
    total: number;
    per_office: Record<string, number>;
}

export async function getServicesCount(): Promise<ServicesCountResponse> {
    if (MOCK) return { total: 54, per_office: { Academic: 9, Administrative: 20, OSAS: 25 } };
    try {
        const r = await axios.get<ServicesCountResponse>(`${BASE}/api/services/count`);
        return r.data;
    } catch {
        return { total: 54, per_office: { Academic: 9, Administrative: 20, OSAS: 25 } };
    }
}
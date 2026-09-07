

const ICSA_TOKEN_KEY = "icsa_token";

export interface IcsaUser {
    userId: string;
    username: string;
    displayName: string;
    armsRole: string;
    office: string; // PSS short code: 'ACAD' | 'OSAS' | 'ADMIN' | 'ALL'
    isCrossOffice: boolean;
}

export const ANALYTICS_ALLOWED_ROLES = new Set(["SUPER_ADMIN", "PLANNING_OFFICER", "SUBSYSTEM_ADMIN"]);

export const OFFICE_CODE_TO_LABEL: Record<string, string> = {
    ACAD: "Academic",
    ADMIN: "Administrative",
    OSAS: "OSAS",
};

export function getToken(): string | null {
    return localStorage.getItem(ICSA_TOKEN_KEY);
}

function setToken(token: string) {
    localStorage.setItem(ICSA_TOKEN_KEY, token);
}


export function initTokenFromUrl(): void {
    const params = new URLSearchParams(window.location.search);
    const token = params.get("token");
    if (!token) return;

    setToken(token);
    params.delete("token");
    const newSearch = params.toString();
    const newUrl = window.location.pathname + (newSearch ? `?${newSearch}` : "") + window.location.hash;
    window.history.replaceState({}, "", newUrl);
}

export function decodeCurrentUser(): IcsaUser | null {
    const token = getToken();
    if (!token || !token.startsWith("mock-token-")) return null;

    try {
        const b64Part = token.slice("mock-token-".length);
        const json = decodeURIComponent(escape(atob(b64Part)));
        const claims = JSON.parse(json);
        return {
            userId: claims.userId || claims.id || "unknown",
            username: claims.username || "unknown",
            displayName: claims.displayName || claims.username || "Unknown User",
            armsRole: claims.armsRole || claims.role || "STAFF",
            office: claims.office || "ACAD",
            isCrossOffice: !!claims.isCrossOffice,
        };
    } catch (e) {
        console.warn("[icsa-auth] Failed to decode token:", e);
        return null;
    }
}

export function canSeeAnalytics(user: IcsaUser | null): boolean {
    if (!user) return false;
    return ANALYTICS_ALLOWED_ROLES.has(user.armsRole);
}
// TypeScript interfaces — must match /docs/api-contracts.md exactly (SETUP-03).

export interface ChatHistoryTurn {
    role: "citizen" | "assistant";
    content: string;
}

export interface ChatRequest {
    query: string;
    session_id?: string;
    // H-01: last 3-5 turns sent so the backend can resolve follow-up
    // questions ("what are the requirements for that?") into a standalone
    // search query instead of treating every message as context-free.
    chat_history?: ChatHistoryTurn[];
}

export interface MatchedService {
    service_id: string | null;
    service_name: string | null;
    office: string | null;
    confidence: number;
}

export interface ChatResponse {
    answer: string;
    matched_service: string | null;
    matched_service_id: string | null;
    office: string | null;
    confidence: number;
    matched_services?: MatchedService[];
    escalated: boolean;
    response_time_ms: number;
    session_id?: string;
}

export interface TopService {
    service_name: string;
    office: string;
    query_count: number;
}

export interface QueryVolumePoint {
    date: string;
    count: number;
}

export interface EscalationRate {
    rate: number;
    total: number;
    escalated: number;
}

export interface ApiError {
    error: string;
    code: number;
}

export interface Message {
    role: "citizen" | "assistant";
    content: string;
    response?: ChatResponse;
    isError?: boolean;
}

export interface AvgResponseTime {
    avg_response_time_ms: number;
}

export interface RecentInteraction {
    query: string;
    matched_service: string;
    office: string;
    confidence: number;
    response_time_ms: number;
    escalated: boolean;
    created_at?: string;
}

export interface ConfidenceBucket {
    bucket: string;
    count: number;
    color: string;
}
// FE-02: chat API client with mock mode (VITE_USE_MOCK_API).
import axios from "axios";
import type { ChatHistoryTurn, ChatResponse } from "../types";

const BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";
const MOCK = import.meta.env.VITE_USE_MOCK_API === "true";

// Real PUP Citizen's Charter service name (per FE-02 AC).
export const MOCK_CHAT_RESPONSE: ChatResponse = {
    answer:
        "To get a Medical Certificate, visit the campus Medical Clinic (Administrative Office). Requirements:\n• Accomplished Patient Information Sheet\n• Valid PUP ID\nSteps:\n1. Register at the Medical Clinic\n2. Undergo consultation with the campus physician\n3. Receive your medical certificate\nSLA: 30 Minutes.",
    matched_service: "Medical Certificate",
    matched_service_id: "mock-0001",
    office: "Administrative",
    confidence: 0.87,
    escalated: false,
    response_time_ms: 1000,
};

const delay = (ms: number) => new Promise((r) => setTimeout(r, ms));

export async function sendMessage(
    query: string,
    sessionId?: string,
    chatHistory?: ChatHistoryTurn[]
): Promise<ChatResponse> {
    if (MOCK) {
        await delay(1000); 
        return MOCK_CHAT_RESPONSE;
    }
    try {
        const response = await axios.post<ChatResponse>(`${BASE}/api/chat`, {
            query,
            session_id: sessionId,
           
            chat_history: chatHistory,
        });
        return response.data;
    } catch (err: any) {
        if (err.response?.status === 400) throw new Error("Query cannot be empty");
        if (err.response?.status === 500) throw new Error("Server error. Please try again.");
        if (err.code === "ECONNABORTED")
            throw new Error("The assistant took too long. Please try again.");
        throw new Error("Server error. Please try again.");
    }
}
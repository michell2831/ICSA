import { useCallback, useEffect, useRef, useState } from "react";
import { sendMessage } from "../api/chatApi";
import type { ChatHistoryTurn, Message } from "../types";

const HISTORY_TURNS_TO_SEND = 5;
const STORAGE_KEY_MESSAGES = "icsa_chat_messages";
const STORAGE_KEY_SESSION = "icsa_chat_session_id";

function loadSavedMessages(): Message[] {
    try {
        const raw = sessionStorage.getItem(STORAGE_KEY_MESSAGES);
        return raw ? JSON.parse(raw) : [];
    } catch {
        return [];
    }
}

function loadSavedSessionId(): string | undefined {
    try {
        return sessionStorage.getItem(STORAGE_KEY_SESSION) || undefined;
    } catch {
        return undefined;
    }
}

export function useChat() {
    const [messages, setMessages] = useState<Message[]>(loadSavedMessages);
    const [isLoading, setIsLoading] = useState(false);
    const sessionIdRef = useRef<string | undefined>(loadSavedSessionId());

    useEffect(() => {
        try {
            sessionStorage.setItem(STORAGE_KEY_MESSAGES, JSON.stringify(messages));
        } catch { }
    }, [messages]);

    const send = useCallback(
        async (query: string) => {
            const trimmed = query.trim();
            if (!trimmed || isLoading) return;

            const historyToSend: ChatHistoryTurn[] = messages
                .slice(-HISTORY_TURNS_TO_SEND)
                .map((m) => ({ role: m.role, content: m.content }));

            setMessages((prev) => [...prev, { role: "citizen", content: trimmed }]);
            setIsLoading(true);
            try {
                const response = await sendMessage(
                    trimmed,
                    sessionIdRef.current,
                    historyToSend
                );

                if (response.session_id) {
                    sessionIdRef.current = response.session_id;
                    try {
                        sessionStorage.setItem(STORAGE_KEY_SESSION, response.session_id);
                    } catch { }
                }
                setMessages((prev) => [
                    ...prev,
                    { role: "assistant", content: response.answer, response },
                ]);
            } catch (err: any) {
                setMessages((prev) => [
                    ...prev,
                    { role: "assistant", content: err.message ?? "Something went wrong.", isError: true },
                ]);
            } finally {
                setIsLoading(false);
            }
        },
        [isLoading, messages]
    );

    const clearChat = useCallback(() => {
        setMessages([]);
        sessionIdRef.current = undefined;
        try {
            sessionStorage.removeItem(STORAGE_KEY_MESSAGES);
            sessionStorage.removeItem(STORAGE_KEY_SESSION);
        } catch { }
    }, []);

    return { messages, isLoading, send, clearChat };
}
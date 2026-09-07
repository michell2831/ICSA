import { useEffect, useRef, useState } from "react";
import { useChat } from "../hooks/useChat";
import type { MatchedService } from "../types";
import MessageBubble from "./MessageBubble";
import ServiceCard from "./ServiceCard";

const PupStarLogo = ({ size = 18 }: { size?: number }) => (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none">
        <path
            d="M12 2L15.09 8.26L22 9.27L17 14.14L18.18 21.02L12 17.77L5.82 21.02L7 14.14L2 9.27L8.91 8.26L12 2Z"
            fill="url(#goldGradCW)"
            stroke="#F3C63F"
            strokeWidth="1.2"
        />
        <defs>
            <linearGradient id="goldGradCW" x1="2" y1="2" x2="22" y2="21" gradientUnits="userSpaceOnUse">
                <stop stopColor="#F8D66D" />
                <stop offset="1" stopColor="#B8860B" />
            </linearGradient>
        </defs>
    </svg>
);

interface SuggestedQuestion {
    category: string;
    question: string;
}

const SUGGESTED_QUESTIONS: SuggestedQuestion[] = [
    {
        category: "Health Services",
        question: "What do I need for a medical certificate?",
    },
    {
        category: "Registrar Office",
        question: "How do I get a new student ID?",
    },
    {
        category: "Academic Services",
        question: "How do I apply for cross-enrollment?",
    },
    {
        category: "OSAS Guidance",
        question: "What do I need for a counseling appointment?",
    },
];

export default function ChatWindow() {
    const { messages, isLoading, send, clearChat } = useChat();
    const [input, setInput] = useState("");
    const bottomRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        bottomRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [messages, isLoading]);

    const handleSend = (text?: string) => {
        const value = (text ?? input).trim();
        if (!value) return;
        send(value);
        setInput("");
    };

    return (
        <div className="chat-window">
            <header className="chat-header">
                <div className="chat-header-info">
                    <div className="chat-header-seal" aria-hidden>
                        <PupStarLogo size={18} />
                    </div>
                    <div>
                        <div className="chat-header-title-row">
                            <h1 className="chat-header-name">Citizen Service Assistant</h1>
                        </div>
                        <p className="chat-header-caption">
                            Instant guidance grounded on PUP's Official Citizen's Charter
                        </p>
                    </div>
                </div>

                <button
                    className="btn-new-chat"
                    onClick={clearChat}
                    title="Start a new conversation"
                >
                    <span>New Chat</span>
                </button>
            </header>

            <div className="chat-messages">
                {messages.length === 0 && (
                    <div className="chat-empty">
                        <div className="chat-empty-badge">
                            <span>PUP CALOOCAN CITIZEN'S CHARTER</span>
                        </div>
                        <h2 className="chat-empty-title">Welcome to Citizen Service Assistant</h2>
                        <p className="chat-empty-caption">
                            How may we assist you today? Select a frequent inquiry below or type your specific service question.
                        </p>

                        <div className="suggestion-grid">
                            {SUGGESTED_QUESTIONS.map((item) => (
                                <button
                                    key={item.question}
                                    className="suggestion-card"
                                    onClick={() => handleSend(item.question)}
                                >
                                    <div className="suggestion-card-top">
                                        <span className="suggestion-category">{item.category}</span>
                                    </div>
                                    <p className="suggestion-text">"{item.question}"</p>
                                    <span className="suggestion-action">Inquire service {"->"}</span>
                                </button>
                            ))}
                        </div>
                    </div>
                )}

                {messages.map((m, i) => {
                    const services: MatchedService[] = [];
                    if (m.response) {
                        if (m.response.matched_services && m.response.matched_services.length > 0) {
                            services.push(
                                ...m.response.matched_services.filter(
                                    (s) => s.confidence >= 0.40 && s.service_name
                                )
                            );
                        } else if (m.response.matched_service && m.response.confidence >= 0.40) {
                            services.push({
                                service_id: m.response.matched_service_id,
                                service_name: m.response.matched_service,
                                office: m.response.office,
                                confidence: m.response.confidence,
                            });
                        }
                    }

                    return (
                        <div key={i} className="message-group">
                            <MessageBubble message={m} />
                            {services.slice(0, 1).map((s, idx) => (
                                <ServiceCard
                                    key={s.service_id || `${s.service_name}-${idx}`}
                                    matchedService={s}
                                />
                            ))}
                        </div>
                    );
                })}

                {isLoading && (
                    <div className="loading-dots-container">
                        <div className="bot-icon mini" aria-hidden>
                            <PupStarLogo size={14} />
                        </div>
                        <div className="loading-dots" aria-label="Assistant is thinking">
                            <span></span>
                            <span></span>
                            <span></span>
                        </div>
                        <span className="loading-label">Searching Citizen's Charter database...</span>
                    </div>
                )}
                <div ref={bottomRef} />
            </div>

            <div className="chat-input-row">
                <div className="input-wrapper">
                    <input
                        type="text"
                        value={input}
                        placeholder="Ask about any service, requirements, or process..."
                        onChange={(e) => setInput(e.target.value)}
                        onKeyDown={(e) => e.key === "Enter" && handleSend()}
                        disabled={isLoading}
                    />
                    <span className="enter-hint">Press Enter</span>
                </div>
                <button
                    className="send-btn"
                    onClick={() => handleSend()}
                    disabled={isLoading || !input.trim()}
                    title="Send Message"
                >
                    <span>Send</span>
                    <svg className="send-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                        <line x1="22" y1="2" x2="11" y2="13"></line>
                        <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
                    </svg>
                </button>
            </div>
        </div>
    );
}
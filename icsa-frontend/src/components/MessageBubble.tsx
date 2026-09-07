import type { Message } from "../types";
import ReactMarkdown from "react-markdown";

const PUP_CONTACT_PHONE = "(02) 8365-0080";

const PupStarLogo = () => (
  <svg width="15" height="15" viewBox="0 0 24 24" fill="none">
    <path
      d="M12 2L15.09 8.26L22 9.27L17 14.14L18.18 21.02L12 17.77L5.82 21.02L7 14.14L2 9.27L8.91 8.26L12 2Z"
      fill="url(#goldGradMB)"
      stroke="#F3C63F"
      strokeWidth="1.2"
    />
    <defs>
      <linearGradient id="goldGradMB" x1="2" y1="2" x2="22" y2="21" gradientUnits="userSpaceOnUse">
        <stop stopColor="#F8D66D" />
        <stop offset="1" stopColor="#B8860B" />
      </linearGradient>
    </defs>
  </svg>
);

function isNoContextAnswer(content: string): boolean {
  const c = content.toLowerCase();
  return (
    c.includes("please visit") ||
    c.includes("do not have specific") ||
    c.includes("don't have specific")
  );
}

export default function MessageBubble({ message }: { message: Message }) {
  const isCitizen = message.role === "citizen";
  const noContext = !isCitizen && !message.isError && isNoContextAnswer(message.content);

  const bubbleClass = isCitizen
    ? "bubble-citizen"
    : message.isError
      ? "bubble-error"
      : noContext
        ? "bubble-warning"
        : "bubble-assistant";

  return (
    <div className={`bubble-row ${isCitizen ? "right" : "left"}`}>
      {!isCitizen && (
        <div className="bot-icon-badge" title="PUP Citizen Service Assistant">
          <PupStarLogo />
        </div>
      )}
      <div className={`bubble ${bubbleClass}`}>
        {noContext && (
          <div className="warn-header">
            <span className="warn-title">No direct Charter match found</span>
          </div>
        )}
        <div className="bubble-content-text">
          <ReactMarkdown>{message.content}</ReactMarkdown>
        </div>
        {noContext && (
          <div className="warn-contact-box">
            <span className="contact-label">Need direct assistance?</span>
            <a href="tel:0283650080" className="contact-link">
              PUP Caloocan: {PUP_CONTACT_PHONE}
            </a>
          </div>
        )}
      </div>
      {isCitizen && (
        <div className="citizen-icon-badge" title="You">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path>
            <circle cx="12" cy="7" r="4"></circle>
          </svg>
        </div>
      )}
    </div>
  );
}


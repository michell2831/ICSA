import type { ChatResponse, MatchedService } from "../types";

const MIN_CONFIDENCE_THRESHOLD = 0.40;

interface ServiceCardProps {
  matchedService?: MatchedService | null;
  response?: ChatResponse | null;
  minConfidence?: number;
}

export default function ServiceCard({
  matchedService,
  response,
  minConfidence = MIN_CONFIDENCE_THRESHOLD,
}: ServiceCardProps) {
  const serviceName = matchedService?.service_name ?? response?.matched_service;
  const office = matchedService?.office ?? response?.office;
  const confidence = matchedService?.confidence ?? response?.confidence ?? 0;

  if (!serviceName || confidence < minConfidence) return null;
  const matchPercentage = Math.round(confidence * 100);

  return (
    <div className="service-card">
      <div className="service-card-header">
        <span className="service-badge-tag">
          Official Charter Match
        </span>
        <div className="confidence-meter-container">
          <span className="confidence-text">{matchPercentage}% confidence</span>
          <div className="confidence-track">
            <div
              className="confidence-fill"
              style={{ width: `${Math.max(matchPercentage, 10)}%` }}
            />
          </div>
        </div>
      </div>

      <h3 className="service-name">{serviceName}</h3>

      <div className="service-meta">
        {office && (
          <span className="meta-pill office">
            {office}
          </span>
        )}
        <span className="meta-pill status">
          Citizen Charter Verified
        </span>
      </div>
    </div>
  );
}

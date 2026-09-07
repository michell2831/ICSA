// FE-04/FE-10: horizontal bar chart — sorted desc, data labels, PUP office colors.
import {
  Bar, BarChart, CartesianGrid, Cell, LabelList,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import type { TopService } from "../../types";

// PUP One UI palette (PSS tokens): maroon / gold / info-navy
const OFFICE_COLORS: Record<string, string> = {
  Academic: "#700010",
  Administrative: "#D97706",
  OSAS: "#1E3A8A",
};

const formatServiceName = (name: string) => {
  if (!name) return "";
  let s = name;
  // Clean up long repetitive prefixes to keep unique service names distinct
  s = s.replace(/^Processing of Application for /i, "App for ");
  s = s.replace(/^Processing of Request for /i, "Request for ");
  s = s.replace(/^Request for Reservation of /i, "Reservation: ");

  if (s.length > 42) {
    const match = s.match(/^(.*?)(\s*\(.*\))$/);
    if (match) {
      const base = match[1];
      const suffix = match[2];
      const avail = 42 - suffix.length - 1;
      return avail > 5 ? `${base.substring(0, avail)}…${suffix}` : `${s.substring(0, 40)}…`;
    }
    return `${s.substring(0, 40)}…`;
  }
  return s;
};

export default function TopServicesChart({ data }: { data: TopService[] }) {
  const map = new Map<string, TopService>();
  for (const item of data) {
    const name = item.service_name?.trim();
    if (!name) continue;
    const existing = map.get(name);
    if (existing) {
      existing.query_count += item.query_count;
      if (!existing.office && item.office) {
        existing.office = item.office;
      }
    } else {
      map.set(name, { ...item, service_name: name });
    }
  }

  const sorted = Array.from(map.values())
    .sort((a, b) => b.query_count - a.query_count)
    .map((s) => ({
      ...s,
      displayName: formatServiceName(s.service_name),
    }));

  if (sorted.length === 0) {
    return (
      <div style={{ height: 340, display: "flex", alignItems: "center", justifyContent: "center", color: "#94A3B8", fontSize: "13px", fontWeight: 500 }}>
        No service inquiries recorded yet
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={340}>
      <BarChart data={sorted} layout="vertical" margin={{ left: 10, right: 35, top: 10, bottom: 10 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#F1F5F9" horizontal={false} />
        <XAxis type="number" tick={{ fontSize: 11, fill: "#64748B" }} axisLine={{ stroke: "#E2E8F0" }} />
        <YAxis
          type="category"
          dataKey="displayName"
          width={260}
          tick={{ fontSize: 11, fill: "#334155", fontWeight: 500 }}
          axisLine={false}
          tickLine={false}
        />
        <Tooltip
          formatter={(value: any) => [`${value} Queries`, "Total"]}
          labelFormatter={(label, payload) => {
            if (payload && payload[0]) return payload[0].payload.service_name;
            return label;
          }}
          contentStyle={{
            backgroundColor: "#0F172A",
            borderRadius: "8px",
            border: "1px solid #334155",
            fontSize: "12px",
            padding: "8px 12px",
            boxShadow: "0 10px 15px -3px rgba(0, 0, 0, 0.3)",
          }}
          labelStyle={{ color: "#F59E0B", fontWeight: 700, marginBottom: "4px" }}
          itemStyle={{ color: "#F8FAFC", fontWeight: 600 }}
        />
        <Bar dataKey="query_count" radius={[0, 6, 6, 0]} barSize={18}>
          <LabelList dataKey="query_count" position="right" style={{ fontSize: 11, fill: "#475569", fontWeight: 700 }} />
          {sorted.map((s, idx) => (
            <Cell key={idx} fill={OFFICE_COLORS[s.office] ?? "#700010"} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

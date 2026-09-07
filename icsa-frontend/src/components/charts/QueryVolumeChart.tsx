import {
  Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import type { QueryVolumePoint } from "../../types";

export default function QueryVolumeChart({ data }: { data: QueryVolumePoint[] }) {
  if (!data || data.length === 0) {
    return (
      <div style={{ height: 340, display: "flex", alignItems: "center", justifyContent: "center", color: "#94A3B8", fontSize: "13px", fontWeight: 500 }}>
        No inquiry volume recorded yet
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={340}>
      <AreaChart data={data} margin={{ left: 10, right: 20, top: 10, bottom: 10 }}>
        <defs>
          <linearGradient id="maroonGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#700010" stopOpacity={0.25} />
            <stop offset="95%" stopColor="#700010" stopOpacity={0.0} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="#F1F5F9" />
        <XAxis dataKey="date" tick={{ fontSize: 11, fill: "#64748B" }} axisLine={{ stroke: "#E2E8F0" }} />
        <YAxis
          allowDecimals={false}
          tick={{ fontSize: 11, fill: "#64748B" }}
          axisLine={{ stroke: "#E2E8F0" }}
        />
        <Tooltip
          formatter={(val: any) => [`${val} Queries`, "Volume"]}
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
        <Area
          type="monotone"
          dataKey="count"
          stroke="#700010"
          strokeWidth={2.5}
          fillOpacity={1}
          fill="url(#maroonGrad)"
          activeDot={{ r: 5, fill: "#700010", stroke: "#FFFFFF", strokeWidth: 2 }}
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}

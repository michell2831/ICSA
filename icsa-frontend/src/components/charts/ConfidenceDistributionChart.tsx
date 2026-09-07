import {
  Bar, BarChart, CartesianGrid, Cell, LabelList,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import type { ConfidenceBucket } from "../../types";

export default function ConfidenceDistributionChart({ data }: { data: ConfidenceBucket[] }) {
  return (
    <ResponsiveContainer width="100%" height={340}>
      <BarChart data={data} layout="vertical" margin={{ left: 10, right: 35, top: 15, bottom: 15 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#F1F5F9" horizontal={false} />
        <XAxis type="number" tick={{ fontSize: 11, fill: "#64748B" }} axisLine={{ stroke: "#E2E8F0" }} />
        <YAxis
          type="category"
          dataKey="bucket"
          width={130}
          tick={{ fontSize: 11, fill: "#334155", fontWeight: 600 }}
          axisLine={false}
          tickLine={false}
        />
        <Tooltip
          formatter={(value: any) => [`${value} Inquiries`, "Count"]}
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
        <Bar dataKey="count" radius={[0, 6, 6, 0]} barSize={26}>
          <LabelList dataKey="count" position="right" style={{ fontSize: 11, fill: "#475569", fontWeight: 700 }} />
          {data.map((entry, index) => (
            <Cell key={`cell-${index}`} fill={entry.color || "#059669"} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

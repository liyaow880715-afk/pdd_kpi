import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from "recharts"

interface TrendChartProps {
  data: any[]
}

export function TrendChart({ data }: TrendChartProps) {
  if (!data || data.length === 0) return null

  const metrics = [
    { key: "promo_spend", name: "推广花费", color: "#ef4444" },
    { key: "valid_order_gmv", name: "有效 GMV", color: "#22c55e" },
  ]

  return (
    <div className="h-[300px] w-full">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
          <XAxis dataKey="date" tick={{ fontSize: 12 }} />
          <YAxis tick={{ fontSize: 12 }} />
          <Tooltip
            contentStyle={{
              backgroundColor: "hsl(var(--card))",
              borderColor: "hsl(var(--border))",
              borderRadius: "0.5rem",
            }}
          />
          <Legend />
          {metrics.map((m) => (
            <Line key={m.key} type="monotone" dataKey={m.key} name={m.name} stroke={m.color} strokeWidth={2} dot={false} />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}

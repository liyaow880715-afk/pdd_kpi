import { useState } from "react"
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from "recharts"
import { Badge } from "@/components/ui/badge"

interface TrendChartProps {
  data: any[]
}

const ALL_METRICS = [
  { key: "promo_spend", name: "推广花费", color: "#ef4444", unit: "元" },
  { key: "valid_order_gmv", name: "有效 GMV", color: "#22c55e", unit: "元" },
  { key: "promo_roi", name: "推广 ROI", color: "#3b82f6", unit: "" },
  { key: "real_roi", name: "真实 ROI", color: "#8b5cf6", unit: "" },
  { key: "cpm", name: "CPM", color: "#f59e0b", unit: "元" },
  { key: "cpc", name: "CPC", color: "#06b6d4", unit: "元" },
  { key: "ctr", name: "CTR", color: "#ec4899", unit: "%" },
  { key: "refund_rate", name: "退款率", color: "#64748b", unit: "%" },
]

export function TrendChart({ data }: TrendChartProps) {
  const [selected, setSelected] = useState<string[]>(["promo_spend", "valid_order_gmv"])

  if (!data || data.length === 0) return null

  const toggle = (key: string) => {
    setSelected((prev) =>
      prev.includes(key) ? prev.filter((k) => k !== key) : [...prev, key]
    )
  }

  const activeMetrics = ALL_METRICS.filter((m) => selected.includes(m.key))

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-2">
        {ALL_METRICS.map((m) => {
          const isActive = selected.includes(m.key)
          return (
            <button
              key={m.key}
              onClick={() => toggle(m.key)}
              className="focus:outline-none"
            >
              <Badge
                variant={isActive ? "default" : "outline"}
                style={isActive ? { backgroundColor: m.color, borderColor: m.color } : { borderColor: m.color, color: m.color }}
              >
                {m.name}
              </Badge>
            </button>
          )
        })}
      </div>
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
            {activeMetrics.map((m) => (
              <Line
                key={m.key}
                type="monotone"
                dataKey={m.key}
                name={m.name}
                stroke={m.color}
                strokeWidth={2}
                dot={false}
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}

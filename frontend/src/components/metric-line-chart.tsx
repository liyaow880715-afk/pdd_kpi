import { useEffect, useState } from "react"
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts"

interface MetricConfig {
  key: string
  name: string
  color: string
  unit?: string
}

interface MetricLineChartProps {
  data: any[]
  title: string
  description?: string
  metrics: MetricConfig[]
  hiddenKeys?: Set<string>
}

function formatValue(v: any) {
  if (v === null || v === undefined || Number.isNaN(v)) return "-"
  if (typeof v === "number") return v.toLocaleString("zh-CN", { maximumFractionDigits: 2 })
  return v
}

export function MetricLineChart({ data, title, description, metrics, hiddenKeys }: MetricLineChartProps) {
  const [selected, setSelected] = useState<Set<string>>(new Set())

  // 根据外部 hiddenKeys 初始化/更新选中状态
  useEffect(() => {
    const next = new Set<string>()
    metrics.forEach((m) => {
      if (!hiddenKeys?.has(m.key)) {
        next.add(m.key)
      }
    })
    setSelected(next)
  }, [metrics, hiddenKeys])

  if (!data || data.length === 0) return null

  const toggle = (key: string) => {
    setSelected((prev) => {
      const next = new Set(prev)
      if (next.has(key)) {
        next.delete(key)
      } else {
        next.add(key)
      }
      return next
    })
  }

  const activeMetrics = metrics.filter((m) => selected.has(m.key))

  return (
    <div className="space-y-2">
      <div>
        <h3 className="text-sm font-semibold">{title}</h3>
        {description && <p className="text-xs text-muted-foreground">{description}</p>}
      </div>
      <div className="flex flex-wrap gap-1.5">
        {metrics.map((m) => {
          const isActive = selected.has(m.key)
          return (
            <button
              key={m.key}
              onClick={() => toggle(m.key)}
              className={`text-xs px-2 py-0.5 rounded-full border transition-colors ${
                isActive ? "text-white" : "bg-muted text-muted-foreground hover:bg-muted/80"
              }`}
              style={
                isActive
                  ? { backgroundColor: m.color, borderColor: m.color }
                  : { borderColor: m.color }
              }
            >
              {m.name}
            </button>
          )
        })}
      </div>
      {activeMetrics.length === 0 ? (
        <div className="h-[200px] flex items-center justify-center text-xs text-muted-foreground rounded-md border border-dashed">
          点击上方按钮选择要展示的指标
        </div>
      ) : (
        <div className="h-[240px] w-full">
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
                formatter={(value: any, name: any) => {
                  const cfg = metrics.find((m) => m.name === name)
                  return [`${formatValue(value)}${cfg?.unit ? " " + cfg.unit : ""}`, name]
                }}
              />
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
      )}
    </div>
  )
}

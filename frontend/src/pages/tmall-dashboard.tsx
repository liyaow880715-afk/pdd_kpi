import { useEffect, useState } from "react"
import { LayoutDashboard, Calendar, BarChart3 } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { MetricLineChart } from "@/components/metric-line-chart"
import { getStores, getTmallDashboardSummary, getTmallAnalysis, type Store } from "@/api/client"

function formatNumber(v: any, digits = 2) {
  if (v === null || v === undefined || Number.isNaN(v)) return "-"
  if (typeof v === "number") return v.toLocaleString("zh-CN", { maximumFractionDigits: digits })
  return v
}

const productSumKeys = [
  "spend",
  "gmv",
  "valid_gmv",
  "actual_revenue",
  "order_count",
  "valid_order_count",
  "exposure",
  "clicks",
  "refund_orders",
  "refund_amount",
]

function aggregateProductMetrics(storeMetrics: Record<string, any>[][]): Record<string, any>[] {
  const map = new Map<string, Record<string, any>>()
  for (const rows of storeMetrics) {
    for (const row of rows) {
      const id = row.product_id
      if (!id) continue
      if (!map.has(id)) {
        map.set(id, { ...row })
        continue
      }
      const existing = map.get(id)!
      for (const k of productSumKeys) {
        existing[k] = (existing[k] || 0) + (row[k] || 0)
      }
      existing.roi = existing.spend ? existing.gmv / existing.spend : 0
      existing.valid_roi = existing.spend ? existing.valid_gmv / existing.spend : 0
      existing.ctr = existing.exposure ? (existing.clicks / existing.exposure) * 100 : 0
      existing.cvr = existing.clicks ? (existing.order_count / existing.clicks) * 100 : 0
      existing.refund_rate = existing.order_count ? (existing.refund_orders / existing.order_count) * 100 : 0
    }
  }
  return Array.from(map.values())
}

function downloadCsv(filename: string, rows: Record<string, any>[], headers: { key: string; label: string }[]) {
  if (rows.length === 0) return
  const escape = (v: any) => {
    const s = v === null || v === undefined ? "" : String(v)
    if (s.includes(",") || s.includes("\n") || s.includes('"')) {
      return `"${s.replace(/"/g, '""')}"`
    }
    return s
  }
  const lines = [headers.map((h) => h.label).join(","), ...rows.map((r) => headers.map((h) => escape(r[h.key])).join(","))]
  const blob = new Blob(["\ufeff" + lines.join("\n")], { type: "text/csv;charset=utf-8" })
  const url = URL.createObjectURL(blob)
  const a = document.createElement("a")
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(url)
}

function KpiCard({ label, value, unit = "" }: { label: string; value: any; unit?: string }) {
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardDescription className="text-xs">{label}</CardDescription>
      </CardHeader>
      <CardContent>
        <CardTitle className="text-xl">
          {formatNumber(value)} {unit && <span className="text-sm font-normal text-muted-foreground">{unit}</span>}
        </CardTitle>
      </CardContent>
    </Card>
  )
}

const trendCharts = [
  {
    title: "成交与消耗",
    description: "消耗、成交金额、净成交金额",
    metrics: [
      { key: "spend", name: "消耗", color: "#ef4444", unit: "元" },
      { key: "gmv", name: "成交金额", color: "#3b82f6", unit: "元" },
      { key: "valid_gmv", name: "净成交金额", color: "#22c55e", unit: "元" },
      { key: "actual_revenue", name: "实际收入", color: "#f97316", unit: "元" },
    ],
  },
  {
    title: "订单与流量",
    description: "订单数、点击、曝光",
    metrics: [
      { key: "order_count", name: "订单数", color: "#8b5cf6" },
      { key: "valid_order_count", name: "净订单数", color: "#06b6d4" },
      { key: "clicks", name: "点击", color: "#f59e0b" },
      { key: "exposure", name: "曝光", color: "#64748b" },
    ],
  },
]

export function TmallDashboardPage() {
  const [stores, setStores] = useState<Store[]>([])
  const [selectedStores, setSelectedStores] = useState<string[]>([])
  const [startDate, setStartDate] = useState(() => {
    const d = new Date()
    d.setDate(d.getDate() - 14)
    return d.toISOString().split("T")[0]
  })
  const [endDate, setEndDate] = useState(() => new Date().toISOString().split("T")[0])
  const [kpis, setKpis] = useState<Record<string, number | null>>({})
  const [costKpis, setCostKpis] = useState<Record<string, number | null>>({})
  const [trend, setTrend] = useState<any[]>([])
  const [productMetrics, setProductMetrics] = useState<Record<string, any>[]>([])
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState("")

  useEffect(() => {
    getStores("tmall").then((s) => {
      setStores(s)
      if (s.length > 0) {
        setSelectedStores(s.map((x) => x.name))
      }
    })
  }, [])

  useEffect(() => {
    if (selectedStores.length > 0) {
      fetchSummary()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedStores.length])

  const fetchSummary = async () => {
    if (selectedStores.length === 0) {
      setMessage("请至少选择一个店铺")
      return
    }
    setLoading(true)
    setMessage("")
    try {
      const summary = await getTmallDashboardSummary(startDate, endDate, selectedStores)
      setKpis(summary.kpis)
      setCostKpis(summary.cost_kpis || {})
      setTrend(summary.trend)

      const analyses = await Promise.all(selectedStores.map((store) => getTmallAnalysis(store, startDate, endDate)))
      const merged = aggregateProductMetrics(analyses.map((a) => a.product_metrics))
      setProductMetrics(merged)
    } catch (err: any) {
      setMessage(err.message)
    } finally {
      setLoading(false)
    }
  }

  const toggleStore = (name: string) => {
    setSelectedStores((prev) => (prev.includes(name) ? prev.filter((n) => n !== name) : [...prev, name]))
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <LayoutDashboard className="h-6 w-6" />
        <h2 className="text-2xl font-bold">天猫总览</h2>
      </div>

      {message && <div className="text-sm p-3 rounded-md bg-destructive/10 text-destructive">{message}</div>}

      <Card>
        <CardContent className="pt-6">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-6 gap-4 items-end">
            <div className="space-y-2">
              <Label>开始日期</Label>
              <Input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} />
            </div>
            <div className="space-y-2">
              <Label>结束日期</Label>
              <Input type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} />
            </div>
            <div className="lg:col-span-3 space-y-2">
              <Label>店铺筛选</Label>
              <div className="flex flex-wrap gap-2 min-h-[40px] items-center rounded-md border border-input bg-background px-3 py-2">
                {stores.length === 0 ? (
                  <span className="text-sm text-muted-foreground">暂无天猫店铺，请先去店铺页创建</span>
                ) : (
                  stores.map((s) => (
                    <label key={s.id} className="flex items-center gap-1 text-sm">
                      <input
                        type="checkbox"
                        className="h-4 w-4 rounded border-input"
                        checked={selectedStores.includes(s.name)}
                        onChange={() => toggleStore(s.name)}
                      />
                      <span className="text-muted-foreground">{s.name}</span>
                    </label>
                  ))
                )}
              </div>
            </div>
            <Button onClick={fetchSummary} disabled={loading}>
              <Calendar className="h-4 w-4 mr-1" /> {loading ? "加载中..." : "查询"}
            </Button>
          </div>
        </CardContent>
      </Card>

      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 xl:grid-cols-6 gap-4">
        <KpiCard label="已选店铺" value={selectedStores.length} />
        <KpiCard label="总消耗" value={kpis.spend} unit="元" />
        <KpiCard label="成交金额" value={kpis.gmv} unit="元" />
        <KpiCard label="净成交金额" value={kpis.valid_gmv} unit="元" />
        <KpiCard label="实际收入" value={kpis.actual_revenue} unit="元" />
        <KpiCard label="订单数" value={kpis.order_count} />
        <KpiCard label="净订单数" value={kpis.valid_order_count} />
        <KpiCard label="ROI" value={kpis.roi} />
        <KpiCard label="点击率" value={kpis.ctr} unit="%" />
        <KpiCard label="总成本" value={costKpis.total_cost} unit="元" />
        <KpiCard label="毛利润" value={costKpis.gross_profit} unit="元" />
        <KpiCard label="盈亏" value={costKpis.profit_loss} unit="元" />
        <KpiCard label="毛利率" value={costKpis.gross_margin_rate} unit="%" />
        <KpiCard label="盈亏率" value={costKpis.profit_loss_rate} unit="%" />
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <BarChart3 className="h-4 w-4" />
            趋势
          </CardTitle>
        </CardHeader>
        <CardContent className="grid grid-cols-1 xl:grid-cols-2 gap-6">
          {trendCharts.map((chart) => (
            <MetricLineChart
              key={chart.title}
              title={chart.title}
              description={chart.description}
              data={trend}
              metrics={chart.metrics}
            />
          ))}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>商品明细（共 {selectedStores.length} 个店铺）</CardTitle>
            <Button
              variant="outline"
              size="sm"
              onClick={() =>
                downloadCsv(
                  `天猫商品明细_${startDate}_${endDate}.csv`,
                  productMetrics,
                  [
                    { key: "product_id", label: "商品ID" },
                    { key: "product_name", label: "商品名称" },
                    { key: "spend", label: "消耗" },
                    { key: "gmv", label: "成交金额" },
                    { key: "valid_gmv", label: "净成交金额" },
                    { key: "actual_revenue", label: "实际收入" },
                    { key: "order_count", label: "订单数" },
                    { key: "valid_order_count", label: "净订单数" },
                    { key: "roi", label: "ROI" },
                    { key: "ctr", label: "点击率" },
                    { key: "cvr", label: "转化率" },
                  ]
                )
              }
              disabled={productMetrics.length === 0}
            >
              导出商品明细
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          <div className="overflow-auto max-h-96">
            <table className="w-full text-sm">
              <thead className="bg-muted">
                <tr>
                  <th className="text-left px-3 py-2">商品</th>
                  <th className="text-right px-3 py-2">消耗</th>
                  <th className="text-right px-3 py-2">成交金额</th>
                  <th className="text-right px-3 py-2">净成交</th>
                  <th className="text-right px-3 py-2">实际收入</th>
                  <th className="text-right px-3 py-2">ROI</th>
                  <th className="text-right px-3 py-2">点击率</th>
                  <th className="text-right px-3 py-2">成本</th>
                  <th className="text-right px-3 py-2">毛利润</th>
                  <th className="text-right px-3 py-2">盈亏</th>
                </tr>
              </thead>
              <tbody>
                {productMetrics.map((row) => (
                  <tr key={row.product_id} className="border-b">
                    <td className="px-3 py-2">{row.product_name || row.product_id}</td>
                    <td className="text-right px-3 py-2">{formatNumber(row.spend)}</td>
                    <td className="text-right px-3 py-2">{formatNumber(row.gmv)}</td>
                    <td className="text-right px-3 py-2">{formatNumber(row.valid_gmv)}</td>
                    <td className="text-right px-3 py-2">{formatNumber(row.actual_revenue)}</td>
                    <td className="text-right px-3 py-2">{formatNumber(row.roi)}</td>
                    <td className="text-right px-3 py-2">{formatNumber(row.ctr)}%</td>
                    <td className="text-right px-3 py-2">{formatNumber(row.total_cost)}</td>
                    <td className="text-right px-3 py-2">{formatNumber(row.gross_profit)}</td>
                    <td className="text-right px-3 py-2">{formatNumber(row.profit_loss)}</td>
                  </tr>
                ))}
                {productMetrics.length === 0 && (
                  <tr>
                    <td colSpan={10} className="text-center text-muted-foreground py-8">
                      暂无数据
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

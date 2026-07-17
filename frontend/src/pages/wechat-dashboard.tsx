import { useEffect, useState } from "react"
import { LayoutDashboard, Calendar, BarChart3, Users } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { MetricLineChart } from "@/components/metric-line-chart"
import { getStores, getWechatDashboardSummary, getWechatAnalysis, getWechatKolStats, type Store } from "@/api/client"

function formatNumber(v: any, digits = 2) {
  if (v === null || v === undefined || Number.isNaN(v)) return "-"
  if (typeof v === "number") return v.toLocaleString("zh-CN", { maximumFractionDigits: digits })
  return v
}

const productSumKeys = [
  "gmv",
  "actual_revenue",
  "valid_gmv",
  "order_count",
  "valid_order_count",
  "quantity",
  "valid_quantity",
  "refund_orders",
  "refund_amount",
  "tech_fee",
  "commission",
  "net_revenue",
  "total_cost",
  "gross_profit",
  "profit_loss",
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
      existing.refund_rate = existing.order_count ? (existing.refund_orders / existing.order_count) * 100 : 0
      existing.refund_amount_rate = existing.gmv ? (existing.refund_amount / existing.gmv) * 100 : 0
      existing.gross_margin_rate = existing.valid_gmv ? (existing.gross_profit / existing.valid_gmv) * 100 : 0
      existing.profit_loss_rate = existing.valid_gmv ? (existing.profit_loss / existing.valid_gmv) * 100 : 0
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
    title: "成交与收入",
    description: "成交金额、实际收款、净成交金额",
    metrics: [
      { key: "gmv", name: "成交金额", color: "#3b82f6", unit: "元" },
      { key: "actual_revenue", name: "实际收款", color: "#f97316", unit: "元" },
      { key: "valid_gmv", name: "净成交金额", color: "#22c55e", unit: "元" },
      { key: "net_revenue", name: "净收入", color: "#8b5cf6", unit: "元" },
    ],
  },
  {
    title: "订单与售后",
    description: "订单数、净订单数、退款订单",
    metrics: [
      { key: "order_count", name: "订单数", color: "#8b5cf6" },
      { key: "valid_order_count", name: "净订单数", color: "#06b6d4" },
      { key: "refund_orders", name: "退款订单", color: "#ef4444" },
      { key: "quantity", name: "商品件数", color: "#64748b" },
    ],
  },
]

export function WechatDashboardPage() {
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
  const [kolStats, setKolStats] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState("")

  useEffect(() => {
    getStores("wechat").then((s) => {
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
      const summary = await getWechatDashboardSummary(startDate, endDate, selectedStores)
      setKpis(summary.kpis)
      setCostKpis(summary.cost_kpis || {})
      setTrend(summary.trend)

      const analyses = await Promise.all(selectedStores.map((store) => getWechatAnalysis(store, startDate, endDate)))
      const merged = aggregateProductMetrics(analyses.map((a) => a.product_metrics))
      setProductMetrics(merged)

      const firstStore = selectedStores[0]
      const kolData = await getWechatKolStats(firstStore, startDate, endDate)
      setKolStats(kolData)
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
        <h2 className="text-2xl font-bold">微信总览</h2>
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
                  <span className="text-sm text-muted-foreground">暂无微信店铺，请先去店铺页创建</span>
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
        <KpiCard label="成交金额" value={kpis.gmv} unit="元" />
        <KpiCard label="实际收款" value={kpis.actual_revenue} unit="元" />
        <KpiCard label="净成交金额" value={kpis.valid_gmv} unit="元" />
        <KpiCard label="净收入" value={kpis.net_revenue} unit="元" />
        <KpiCard label="订单数" value={kpis.order_count} />
        <KpiCard label="净订单数" value={kpis.valid_order_count} />
        <KpiCard label="商品件数" value={kpis.quantity} />
        <KpiCard label="退款订单" value={kpis.refund_orders} />
        <KpiCard label="退款金额" value={kpis.refund_amount} unit="元" />
        <KpiCard label="技术服务费" value={kpis.tech_fee} unit="元" />
        <KpiCard label="带货费用" value={kpis.commission} unit="元" />
        <KpiCard label="退款率" value={kpis.refund_rate} unit="%" />
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
            <CardTitle>商品/SKU 明细（共 {selectedStores.length} 个店铺）</CardTitle>
            <Button
              variant="outline"
              size="sm"
              onClick={() =>
                downloadCsv(
                  `微信商品明细_${startDate}_${endDate}.csv`,
                  productMetrics,
                  [
                    { key: "product_id", label: "商品/SKU" },
                    { key: "product_name", label: "商品名称" },
                    { key: "sku_code", label: "自定义 SKU" },
                    { key: "platform_sku_code", label: "平台 SKU" },
                    { key: "gmv", label: "成交金额" },
                    { key: "actual_revenue", label: "实际收款" },
                    { key: "valid_gmv", label: "净成交金额" },
                    { key: "order_count", label: "订单数" },
                    { key: "valid_order_count", label: "净订单数" },
                    { key: "quantity", label: "商品件数" },
                    { key: "refund_orders", label: "退款订单" },
                    { key: "refund_amount", label: "退款金额" },
                    { key: "tech_fee", label: "技术服务费" },
                    { key: "commission", label: "带货费用" },
                    { key: "total_cost", label: "总成本" },
                    { key: "gross_profit", label: "毛利润" },
                    { key: "profit_loss", label: "盈亏" },
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
                  <th className="text-left px-3 py-2">商品/SKU</th>
                  <th className="text-right px-3 py-2">成交金额</th>
                  <th className="text-right px-3 py-2">实际收款</th>
                  <th className="text-right px-3 py-2">净成交</th>
                  <th className="text-right px-3 py-2">订单数</th>
                  <th className="text-right px-3 py-2">件数</th>
                  <th className="text-right px-3 py-2">退款金额</th>
                  <th className="text-right px-3 py-2">技术服务费</th>
                  <th className="text-right px-3 py-2">带货费用</th>
                  <th className="text-right px-3 py-2">成本</th>
                  <th className="text-right px-3 py-2">毛利润</th>
                  <th className="text-right px-3 py-2">盈亏</th>
                </tr>
              </thead>
              <tbody>
                {productMetrics.map((row) => (
                  <tr key={row.product_id} className="border-b">
                    <td className="px-3 py-2">
                      <div className="max-w-[240px] truncate">{row.product_name || row.product_id}</div>
                      <div className="text-xs text-muted-foreground">{row.sku_code || row.platform_sku_code || row.product_id}</div>
                    </td>
                    <td className="text-right px-3 py-2">{formatNumber(row.gmv)}</td>
                    <td className="text-right px-3 py-2">{formatNumber(row.actual_revenue)}</td>
                    <td className="text-right px-3 py-2">{formatNumber(row.valid_gmv)}</td>
                    <td className="text-right px-3 py-2">{formatNumber(row.order_count, 0)}</td>
                    <td className="text-right px-3 py-2">{formatNumber(row.quantity, 0)}</td>
                    <td className="text-right px-3 py-2">{formatNumber(row.refund_amount)}</td>
                    <td className="text-right px-3 py-2">{formatNumber(row.tech_fee)}</td>
                    <td className="text-right px-3 py-2">{formatNumber(row.commission)}</td>
                    <td className="text-right px-3 py-2">{formatNumber(row.total_cost)}</td>
                    <td className="text-right px-3 py-2">{formatNumber(row.gross_profit)}</td>
                    <td className="text-right px-3 py-2">{formatNumber(row.profit_loss)}</td>
                  </tr>
                ))}
                {productMetrics.length === 0 && (
                  <tr>
                    <td colSpan={12} className="text-center text-muted-foreground py-8">
                      暂无数据
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Users className="h-4 w-4" />
            KOL 带货统计（{selectedStores[0] || "-"}）
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="overflow-auto max-h-96">
            <table className="w-full text-sm">
              <thead className="bg-muted">
                <tr>
                  <th className="text-left px-3 py-2">达人名称</th>
                  <th className="text-right px-3 py-2">订单数</th>
                  <th className="text-right px-3 py-2">GMV</th>
                  <th className="text-right px-3 py-2">净成交</th>
                  <th className="text-right px-3 py-2">佣金</th>
                  <th className="text-right px-3 py-2">退款</th>
                </tr>
              </thead>
              <tbody>
                {kolStats.map((row) => (
                  <tr key={row.kol_name} className="border-b">
                    <td className="px-3 py-2">{row.kol_name}</td>
                    <td className="text-right px-3 py-2">{formatNumber(row.order_count, 0)}</td>
                    <td className="text-right px-3 py-2">{formatNumber(row.gmv)}</td>
                    <td className="text-right px-3 py-2">{formatNumber(row.net_revenue)}</td>
                    <td className="text-right px-3 py-2">{formatNumber(row.commission)}</td>
                    <td className="text-right px-3 py-2">{formatNumber(row.refund_amount)}</td>
                  </tr>
                ))}
                {kolStats.length === 0 && (
                  <tr>
                    <td colSpan={6} className="text-center text-muted-foreground py-8">
                      暂无 KOL 数据
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

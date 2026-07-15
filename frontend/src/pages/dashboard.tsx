import { useEffect, useState } from "react"
import { BarChart3, Store, Calendar } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs"
import { MetricLineChart } from "@/components/metric-line-chart"
import { getStores, getDashboardSummary, type Kpis } from "@/api/client"

function formatNumber(v: any, digits = 2) {
  if (v === null || v === undefined || Number.isNaN(v)) return "-"
  if (typeof v === "number") return v.toLocaleString("zh-CN", { maximumFractionDigits: digits })
  return v
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

const kpiGroups = [
  {
    title: "成交与收入",
    items: [
      { key: "promo_spend", label: "推广花费", unit: "元" },
      { key: "promo_gmv", label: "推广 GMV", unit: "元" },
      { key: "order_gmv", label: "订单 GMV", unit: "元" },
      { key: "valid_order_gmv", label: "有效订单 GMV", unit: "元" },
      { key: "merchant_income", label: "商家实收", unit: "元" },
      { key: "valid_merchant_income", label: "有效商家实收", unit: "元" },
      { key: "promo_cost_ratio", label: "推广费比", unit: "%" },
      { key: "order_count", label: "订单数" },
      { key: "valid_order_count", label: "有效订单数" },
    ],
  },
  {
    title: "ROI 与效率",
    items: [
      { key: "promo_roi", label: "推广 ROI" },
      { key: "real_roi", label: "真实 ROI" },
      { key: "ctr", label: "点击率 CTR", unit: "%" },
      { key: "cpc", label: "CPC", unit: "元" },
      { key: "cpm", label: "CPM", unit: "元" },
    ],
  },
  {
    title: "退款与取消",
    items: [
      { key: "problem_rate", label: "问题订单率", unit: "%" },
      { key: "refund_rate", label: "退款率", unit: "%" },
      { key: "cancel_rate", label: "取消率", unit: "%" },
    ],
  },
  {
    title: "成本与利润",
    items: [
      { key: "total_product_cost", label: "商品成本", unit: "元" },
      { key: "total_logistics_cost", label: "物流成本", unit: "元" },
      { key: "total_cost", label: "总成本", unit: "元" },
      { key: "link_gross_profit", label: "链接毛利", unit: "元" },
      { key: "profit_loss", label: "盈亏", unit: "元" },
      { key: "gross_margin_rate", label: "毛利率", unit: "%" },
      { key: "profit_loss_rate", label: "盈亏率", unit: "%" },
    ],
  },
]

const trendCharts = [
  {
    title: "成交与收入",
    description: "推广花费、GMV、有效 GMV",
    metrics: [
      { key: "promo_spend", name: "推广花费", color: "#ef4444", unit: "元" },
      { key: "promo_gmv", name: "推广 GMV", color: "#3b82f6", unit: "元" },
      { key: "order_gmv", name: "订单 GMV", color: "#22c55e", unit: "元" },
      { key: "valid_order_gmv", name: "有效 GMV", color: "#8b5cf6", unit: "元" },
    ],
  },
  {
    title: "ROI 与效率",
    description: "推广 ROI、真实 ROI、CTR",
    metrics: [
      { key: "promo_roi", name: "推广 ROI", color: "#ef4444" },
      { key: "real_roi", name: "真实 ROI", color: "#3b82f6" },
      { key: "ctr", name: "CTR", color: "#22c55e", unit: "%" },
    ],
  },
  {
    title: "流量与点击成本",
    description: "曝光量、点击量、CPC、CPM",
    metrics: [
      { key: "exposure", name: "曝光量", color: "#f59e0b", unit: "次" },
      { key: "clicks", name: "点击量", color: "#06b6d4", unit: "次" },
      { key: "cpc", name: "CPC", color: "#64748b", unit: "元" },
      { key: "cpm", name: "CPM", color: "#8b5cf6", unit: "元" },
    ],
  },
  {
    title: "退款与取消",
    description: "问题订单率、退款率、取消率",
    metrics: [
      { key: "problem_rate", name: "问题订单率", color: "#ef4444", unit: "%" },
      { key: "refund_rate", name: "退款率", color: "#3b82f6", unit: "%" },
      { key: "cancel_rate", name: "取消率", color: "#f59e0b", unit: "%" },
    ],
  },
  {
    title: "成本与利润",
    description: "商品成本、物流成本、毛利、盈亏、毛利率、盈亏率",
    metrics: [
      { key: "total_product_cost", name: "商品成本", color: "#f59e0b", unit: "元" },
      { key: "total_logistics_cost", name: "物流成本", color: "#8b5cf6", unit: "元" },
      { key: "total_cost", name: "总成本", color: "#64748b", unit: "元" },
      { key: "link_gross_profit", name: "链接毛利", color: "#22c55e", unit: "元" },
      { key: "profit_loss", name: "盈亏", color: "#ef4444", unit: "元" },
      { key: "gross_margin_rate", name: "毛利率", color: "#3b82f6", unit: "%" },
      { key: "profit_loss_rate", name: "盈亏率", color: "#06b6d4", unit: "%" },
    ],
  },
]

export function DashboardPage() {
  const [stores, setStores] = useState<{ id: string; name: string }[]>([])
  const [selectedStores, setSelectedStores] = useState<string[]>([])
  const [startDate, setStartDate] = useState(() => {
    const d = new Date()
    d.setDate(d.getDate() - 30)
    return d.toISOString().split("T")[0]
  })
  const [endDate, setEndDate] = useState(() => new Date().toISOString().split("T")[0])
  const [kpis, setKpis] = useState<Kpis>({})
  const [trend, setTrend] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState("")
  const [activeTab, setActiveTab] = useState("overview")

  useEffect(() => {
    getStores("pdd").then((s) => {
      setStores(s)
      setSelectedStores(s.map((x) => x.name))
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
      const data = await getDashboardSummary(startDate, endDate, selectedStores)
      setKpis(data.kpis)
      setTrend(data.trend)
    } catch (err: any) {
      setMessage(err.message)
    } finally {
      setLoading(false)
    }
  }

  const toggleStore = (name: string) => {
    setSelectedStores((prev) =>
      prev.includes(name) ? prev.filter((n) => n !== name) : [...prev, name]
    )
  }

  return (
    <div className="space-y-4">
      <h2 className="text-2xl font-bold">总览</h2>

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
                  <span className="text-sm text-muted-foreground">暂无店铺</span>
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

      {message && (
        <div className="text-sm p-3 rounded-md bg-destructive/10 text-destructive">{message}</div>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="pb-2 flex flex-row items-center justify-between">
            <CardTitle className="text-sm font-medium">已选店铺</CardTitle>
            <Store className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">{selectedStores.length}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2 flex flex-row items-center justify-between">
            <CardTitle className="text-sm font-medium">数据区间</CardTitle>
            <Calendar className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-lg font-bold">{startDate} ~ {endDate}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2 flex flex-row items-center justify-between">
            <CardTitle className="text-sm font-medium">功能模块</CardTitle>
            <BarChart3 className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">8</div>
          </CardContent>
        </Card>
      </div>

      {kpis && Object.keys(kpis).length > 0 && (
        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList className="flex-wrap h-auto">
            <TabsTrigger value="overview">总览 KPI</TabsTrigger>
            <TabsTrigger value="trend">趋势</TabsTrigger>
          </TabsList>

          <TabsContent value="overview" className="space-y-4">
            {kpiGroups.map((group) => {
              const items = group.items.filter((item) => kpis[item.key] !== undefined && kpis[item.key] !== null)
              if (items.length === 0) return null
              return (
                <Card key={group.title}>
                  <CardHeader>
                    <CardTitle>{group.title}</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4">
                      {items.map((item) => (
                        <KpiCard key={item.key} label={item.label} value={kpis[item.key]} unit={item.unit} />
                      ))}
                    </div>
                  </CardContent>
                </Card>
              )
            })}
          </TabsContent>

          <TabsContent value="trend" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>趋势</CardTitle>
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
          </TabsContent>
        </Tabs>
      )}
    </div>
  )
}

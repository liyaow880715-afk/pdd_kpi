import { useEffect, useState } from "react"
import { Search } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select } from "@/components/ui/select"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Badge } from "@/components/ui/badge"
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs"
import { MetricLineChart } from "@/components/metric-line-chart"
import { getStores, getAnalysis, getTrend, type Store } from "@/api/client"

function formatNumber(v: any, digits = 2) {
  if (v === null || v === undefined || Number.isNaN(v)) return "-"
  if (typeof v === "number") return v.toLocaleString("zh-CN", { maximumFractionDigits: digits })
  return v
}

function KpiCard({ label, value, unit = "", indent = false }: { label: string; value: any; unit?: string; indent?: boolean }) {
  return (
    <Card className={indent ? "border-l-4 border-l-primary/30" : ""}>
      <CardHeader className="pb-2">
        <CardDescription className={`text-xs ${indent ? "pl-2" : ""}`}>{label}</CardDescription>
        <CardTitle className={`text-xl ${indent ? "pl-2" : ""}`}>
          {formatNumber(value)} {unit && <span className="text-sm font-normal text-muted-foreground">{unit}</span>}
        </CardTitle>
      </CardHeader>
    </Card>
  )
}

const kpiGroups = [
  {
    title: "成交与收入",
    items: [
      { key: "promo_spend", label: "推广花费", unit: "元" },
      { key: "promo_gmv", label: "推广 GMV", unit: "元" },
      { key: "promo_gmv_ratio", label: "推广 GMV 占比", unit: "%" },
      { key: "promo_orders", label: "推广订单数" },
      { key: "promo_order_ratio", label: "推广订单占比", unit: "%" },
      { key: "order_gmv", label: "订单 GMV", unit: "元" },
      { key: "valid_order_gmv", label: "有效订单 GMV", unit: "元" },
      { key: "valid_order_gmv_ratio", label: "有效 GMV 占比", unit: "%" },
      { key: "merchant_income", label: "商家实收", unit: "元" },
      { key: "valid_merchant_income", label: "有效商家实收", unit: "元" },
      { key: "order_count", label: "订单数" },
      { key: "valid_order_count", label: "有效订单数" },
    ],
  },
  {
    title: "ROI 与效率",
    items: [
      { key: "promo_roi", label: "推广 ROI" },
      { key: "real_roi", label: "真实 ROI" },
      { key: "valid_order_gmv_roi", label: "有效 GMV ROI" },
      { key: "exposure", label: "曝光量" },
      { key: "clicks", label: "点击量" },
      { key: "ctr", label: "点击率 CTR", unit: "%" },
      { key: "cpc", label: "CPC", unit: "元" },
      { key: "cpm", label: "CPM", unit: "元" },
      { key: "click_to_order_rate", label: "点击转化率", unit: "%" },
      { key: "exposure_to_order_rate", label: "曝光到订单转化率", unit: "%" },
      { key: "promo_cost_per_order", label: "推广单均成本", unit: "元" },
    ],
  },
  {
    title: "退款与取消",
    items: [
      { key: "problem_rate", label: "问题订单率", unit: "%" },
      { key: "refund_rate", label: "退款率", unit: "%" },
      { key: "refund_unshipped_rate", label: "└ 未发货退款率", unit: "%", indent: true },
      { key: "refund_shipped_rate", label: "└ 已发货退款率", unit: "%", indent: true },
      { key: "refund_received_rate", label: "└ 已收货退款率", unit: "%", indent: true },
      { key: "cancel_rate", label: "取消率", unit: "%" },
      { key: "refund_count", label: "退款数" },
      { key: "refund_unshipped_count", label: "└ 未发货退款数", indent: true },
      { key: "refund_shipped_count", label: "└ 已发货退款数", indent: true },
      { key: "refund_received_count", label: "└ 已收货退款数", indent: true },
      { key: "cancel_count", label: "取消数" },
    ],
  },
  {
    title: "自然流量",
    items: [
      { key: "organic_orders", label: "自然订单数" },
      { key: "organic_valid_order_count", label: "自然有效订单数" },
      { key: "organic_gmv", label: "自然 GMV", unit: "元" },
      { key: "organic_merchant_income", label: "自然有效商家实收", unit: "元" },
      { key: "organic_ratio_orders", label: "自然订单占比", unit: "%" },
      { key: "organic_ratio_valid_orders", label: "自然有效订单占比", unit: "%" },
      { key: "organic_ratio_gmv", label: "自然 GMV 占比", unit: "%" },
      { key: "organic_ratio_income", label: "自然有效收入占比", unit: "%" },
    ],
  },
  {
    title: "成本与利润",
    items: [
      { key: "total_cost", label: "总成本", unit: "元" },
      { key: "link_gross_profit", label: "链接毛利", unit: "元" },
      { key: "profit_loss", label: "盈亏", unit: "元" },
      { key: "gross_margin_rate", label: "毛利率", unit: "%" },
    ],
  },
]

const productColumns = [
  { key: "product_id", label: "商品ID" },
  { key: "product_name", label: "商品名称" },
  { key: "promo_spend", label: "推广花费" },
  { key: "promo_gmv", label: "推广GMV" },
  { key: "promo_orders", label: "推广订单" },
  { key: "exposure", label: "曝光量" },
  { key: "clicks", label: "点击量" },
  { key: "ctr", label: "CTR%" },
  { key: "cpc", label: "CPC" },
  { key: "cpm", label: "CPM" },
  { key: "order_count", label: "订单数" },
  { key: "valid_order_count", label: "有效订单" },
  { key: "valid_order_gmv", label: "有效GMV" },
  { key: "valid_merchant_income", label: "有效收入" },
  { key: "promo_roi", label: "推广ROI" },
  { key: "real_roi_merchant_income", label: "真实ROI" },
  { key: "refund_rate", label: "退款率%" },
  { key: "cancel_rate", label: "取消率%" },
  { key: "problem_rate", label: "问题率%" },
  { key: "organic_ratio_gmv", label: "自然GMV%" },
  { key: "organic_ratio_orders", label: "自然订单%" },
  { key: "organic_merchant_income", label: "自然有效收入" },
  { key: "organic_valid_order_count", label: "自然有效订单" },
  { key: "organic_ratio_income", label: "自然收入%" },
  { key: "organic_ratio_valid_orders", label: "自然有效订单%" },
  { key: "avg_order_gmv", label: "客单价" },
  { key: "avg_valid_order_income", label: "单均收入" },
  { key: "total_cost", label: "成本" },
  { key: "link_gross_profit", label: "毛利" },
  { key: "profit_loss", label: "盈亏" },
]

const styleColumns = [
  { key: "product_id", label: "商品ID" },
  { key: "style_id", label: "样式ID" },
  { key: "style_name", label: "样式名称" },
  { key: "order_count", label: "订单数" },
  { key: "valid_order_count", label: "有效订单" },
  { key: "order_gmv", label: "GMV" },
  { key: "valid_order_gmv", label: "有效GMV" },
  { key: "merchant_income", label: "收入" },
  { key: "valid_merchant_income", label: "有效收入" },
  { key: "refund_count", label: "退款数" },
  { key: "cancel_count", label: "取消数" },
  { key: "refund_unshipped_count", label: "未发货退款" },
  { key: "refund_shipped_count", label: "已发货退款" },
  { key: "refund_received_count", label: "已收货退款" },
]

export function MetricsPage() {
  const [stores, setStores] = useState<Store[]>([])
  const [storeName, setStoreName] = useState("")
  const [startDate, setStartDate] = useState(new Date().toISOString().split("T")[0])
  const [endDate, setEndDate] = useState(new Date().toISOString().split("T")[0])
  const [data, setData] = useState<any>(null)
  const [trend, setTrend] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [activeTab, setActiveTab] = useState("overview")

  useEffect(() => {
    getStores().then(setStores)
  }, [])

  const handleAnalyze = async () => {
    if (!storeName) return
    setLoading(true)
    try {
      const [analysis, trendData] = await Promise.all([
        getAnalysis(storeName, startDate, endDate),
        getTrend([storeName], startDate, endDate),
      ])
      setData(analysis)
      setTrend(trendData)
    } catch (err: any) {
      alert(err.message)
    } finally {
      setLoading(false)
    }
  }

  const kpis = data?.kpis || {}

  return (
    <div className="space-y-4">
      <h2 className="text-2xl font-bold">指标分析</h2>
      <Card>
        <CardContent className="pt-6">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 items-end">
            <div className="space-y-2">
              <Label>店铺</Label>
              <Select value={storeName} onChange={(e) => setStoreName(e.target.value)}>
                <option value="">选择店铺</option>
                {stores.map((s) => (
                  <option key={s.id} value={s.name}>
                    {s.name}
                  </option>
                ))}
              </Select>
            </div>
            <div className="space-y-2">
              <Label>开始日期</Label>
              <Input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} />
            </div>
            <div className="space-y-2">
              <Label>结束日期</Label>
              <Input type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} />
            </div>
            <Button onClick={handleAnalyze} disabled={loading}>
              <Search className="h-4 w-4 mr-1" /> {loading ? "分析中..." : "分析"}
            </Button>
          </div>
        </CardContent>
      </Card>

      {data && (
        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList className="flex-wrap h-auto">
            <TabsTrigger value="overview">总览 KPI</TabsTrigger>
            <TabsTrigger value="trend">趋势</TabsTrigger>
            <TabsTrigger value="products">商品明细</TabsTrigger>
            <TabsTrigger value="styles">样式明细</TabsTrigger>
          </TabsList>

          <TabsContent value="overview" className="space-y-4">
            {kpiGroups.map((group) => {
              const visibleItems = group.items.filter((item) => kpis[item.key] !== undefined && kpis[item.key] !== null)
              if (visibleItems.length === 0) return null
              return (
                <Card key={group.title}>
                  <CardHeader>
                    <CardTitle>{group.title}</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4">
                      {visibleItems.map((item) => (
                        <KpiCard key={item.key} label={item.label} value={kpis[item.key]} unit={item.unit} indent={(item as any).indent} />
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
                <CardTitle>趋势细分</CardTitle>
                <CardDescription>按主题拆分的多维度走势</CardDescription>
              </CardHeader>
              <CardContent className="grid grid-cols-1 xl:grid-cols-2 gap-6">
                <MetricLineChart
                  title="成交与收入"
                  description="推广花费、推广 GMV、订单 GMV、有效 GMV"
                  data={trend}
                  metrics={[
                    { key: "promo_spend", name: "推广花费", color: "#ef4444", unit: "元" },
                    { key: "promo_gmv", name: "推广 GMV", color: "#3b82f6", unit: "元" },
                    { key: "order_gmv", name: "订单 GMV", color: "#22c55e", unit: "元" },
                    { key: "valid_order_gmv", name: "有效 GMV", color: "#8b5cf6", unit: "元" },
                  ]}
                />
                <MetricLineChart
                  title="ROI 与效率"
                  description="推广 ROI、真实 ROI、有效 GMV ROI"
                  data={trend}
                  metrics={[
                    { key: "promo_roi", name: "推广 ROI", color: "#ef4444" },
                    { key: "real_roi", name: "真实 ROI", color: "#3b82f6" },
                    { key: "valid_order_gmv_roi", name: "有效 GMV ROI", color: "#22c55e" },
                  ]}
                />
                <MetricLineChart
                  title="流量与点击成本"
                  description="曝光量、点击量、CTR、CPC、CPM"
                  data={trend}
                  metrics={[
                    { key: "exposure", name: "曝光量", color: "#f59e0b", unit: "次" },
                    { key: "clicks", name: "点击量", color: "#06b6d4", unit: "次" },
                    { key: "ctr", name: "CTR", color: "#ec4899", unit: "%" },
                    { key: "cpc", name: "CPC", color: "#64748b", unit: "元" },
                    { key: "cpm", name: "CPM", color: "#8b5cf6", unit: "元" },
                  ]}
                />
                <MetricLineChart
                  title="退款与取消"
                  description="退款率、取消率、问题订单率及三阶段退款率"
                  data={trend}
                  metrics={[
                    { key: "refund_rate", name: "退款率", color: "#ef4444", unit: "%" },
                    { key: "cancel_rate", name: "取消率", color: "#f59e0b", unit: "%" },
                    { key: "problem_rate", name: "问题订单率", color: "#64748b", unit: "%" },
                    { key: "refund_unshipped_rate", name: "未发货退款率", color: "#3b82f6", unit: "%" },
                    { key: "refund_shipped_rate", name: "已发货退款率", color: "#22c55e", unit: "%" },
                    { key: "refund_received_rate", name: "已收货退款率", color: "#8b5cf6", unit: "%" },
                  ]}
                />
                <MetricLineChart
                  title="自然流量"
                  description="自然订单、自然有效订单、自然 GMV、自然有效收入及占比"
                  data={trend}
                  metrics={[
                    { key: "organic_orders", name: "自然订单", color: "#22c55e", unit: "单" },
                    { key: "organic_valid_order_count", name: "自然有效订单", color: "#10b981", unit: "单" },
                    { key: "organic_gmv", name: "自然 GMV", color: "#3b82f6", unit: "元" },
                    { key: "organic_merchant_income", name: "自然有效收入", color: "#06b6d4", unit: "元" },
                    { key: "organic_ratio_orders", name: "自然订单占比", color: "#f59e0b", unit: "%" },
                    { key: "organic_ratio_valid_orders", name: "自然有效订单占比", color: "#d97706", unit: "%" },
                    { key: "organic_ratio_gmv", name: "自然 GMV 占比", color: "#ec4899", unit: "%" },
                    { key: "organic_ratio_income", name: "自然有效收入占比", color: "#8b5cf6", unit: "%" },
                  ]}
                />
                <MetricLineChart
                  title="成本与利润"
                  description="链接毛利、盈亏、毛利率"
                  data={trend}
                  metrics={[
                    { key: "link_gross_profit", name: "链接毛利", color: "#22c55e", unit: "元" },
                    { key: "profit_loss", name: "盈亏", color: "#ef4444", unit: "元" },
                    { key: "gross_margin_rate", name: "毛利率", color: "#3b82f6", unit: "%" },
                  ]}
                />
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="products">
            <Card>
              <CardHeader>
                <CardTitle>商品指标（{data.product_metrics.length} 条）</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="overflow-auto">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        {productColumns.map((col) => (
                          <TableHead key={col.key} className="whitespace-nowrap text-xs">
                            {col.label}
                          </TableHead>
                        ))}
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {data.product_metrics.map((row: any, idx: number) => (
                        <TableRow key={idx}>
                          {productColumns.map((col) => {
                            const v = row[col.key]
                            const isRate = col.label.includes("%") || col.key.includes("rate") || col.key.includes("roi")
                            const isMoney = ["promo_spend", "promo_gmv", "valid_order_gmv", "valid_merchant_income", "order_gmv", "merchant_income", "total_cost", "link_gross_profit", "profit_loss", "cpc", "avg_order_gmv", "avg_valid_order_income"].includes(col.key)
                            return (
                              <TableCell key={col.key} className="text-xs whitespace-nowrap">
                                {col.key === "product_name" || col.key === "style_name" ? (
                                  <span className="max-w-[200px] truncate inline-block">{String(v ?? "")}</span>
                                ) : isRate ? (
                                  <Badge variant={(v > 30 && col.key.includes("refund")) || (v < 1 && col.key.includes("roi")) ? "destructive" : "default"}>
                                    {formatNumber(v)}
                                  </Badge>
                                ) : (
                                  formatNumber(v, isMoney ? 2 : 0)
                                )}
                              </TableCell>
                            )
                          })}
                        </TableRow>
                      ))}
                      {data.product_metrics.length === 0 && (
                        <TableRow>
                          <TableCell colSpan={productColumns.length} className="text-center text-muted-foreground">
                            无数据
                          </TableCell>
                        </TableRow>
                      )}
                    </TableBody>
                  </Table>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="styles">
            <Card>
              <CardHeader>
                <CardTitle>样式指标（{data.style_metrics.length} 条）</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="overflow-auto">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        {styleColumns.map((col) => (
                          <TableHead key={col.key} className="whitespace-nowrap text-xs">
                            {col.label}
                          </TableHead>
                        ))}
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {data.style_metrics.map((row: any, idx: number) => (
                        <TableRow key={idx}>
                          {styleColumns.map((col) => (
                            <TableCell key={col.key} className="text-xs whitespace-nowrap">
                              {formatNumber(row[col.key])}
                            </TableCell>
                          ))}
                        </TableRow>
                      ))}
                      {data.style_metrics.length === 0 && (
                        <TableRow>
                          <TableCell colSpan={styleColumns.length} className="text-center text-muted-foreground">
                            无数据
                          </TableCell>
                        </TableRow>
                      )}
                    </TableBody>
                  </Table>
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      )}
    </div>
  )
}

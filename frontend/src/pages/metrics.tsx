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
import { TrendChart } from "@/components/trend-chart"
import { getStores, getAnalysis, getTrend, type Store } from "@/api/client"

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
        <CardTitle className="text-xl">
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
      { key: "promo_orders", label: "推广订单数" },
      { key: "order_gmv", label: "订单 GMV", unit: "元" },
      { key: "valid_order_gmv", label: "有效订单 GMV", unit: "元" },
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
      { key: "ctr", label: "点击率 CTR", unit: "%" },
      { key: "click_to_order_rate", label: "点击转化率", unit: "%" },
      { key: "cpc", label: "CPC", unit: "元" },
      { key: "promo_cost_per_order", label: "推广单均成本", unit: "元" },
    ],
  },
  {
    title: "退款与取消",
    items: [
      { key: "refund_rate", label: "退款率", unit: "%" },
      { key: "cancel_rate", label: "取消率", unit: "%" },
      { key: "problem_rate", label: "问题订单率", unit: "%" },
      { key: "refund_unshipped_rate", label: "未发货退款率", unit: "%" },
      { key: "refund_shipped_rate", label: "已发货退款率", unit: "%" },
      { key: "refund_received_rate", label: "已收货退款率", unit: "%" },
      { key: "refund_count", label: "退款数" },
      { key: "cancel_count", label: "取消数" },
      { key: "refund_unshipped_count", label: "未发货退款数" },
      { key: "refund_shipped_count", label: "已发货退款数" },
      { key: "refund_received_count", label: "已收货退款数" },
    ],
  },
  {
    title: "自然流量",
    items: [
      { key: "organic_orders", label: "自然订单数" },
      { key: "organic_gmv", label: "自然 GMV", unit: "元" },
      { key: "organic_ratio_orders", label: "自然订单占比", unit: "%" },
      { key: "organic_ratio_gmv", label: "自然 GMV 占比", unit: "%" },
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
  { key: "order_count", label: "订单数" },
  { key: "valid_order_count", label: "有效订单" },
  { key: "valid_order_gmv", label: "有效GMV" },
  { key: "valid_merchant_income", label: "有效收入" },
  { key: "promo_roi", label: "推广ROI" },
  { key: "real_roi_merchant_income", label: "真实ROI" },
  { key: "ctr", label: "CTR%" },
  { key: "cpc", label: "CPC" },
  { key: "refund_rate", label: "退款率%" },
  { key: "cancel_rate", label: "取消率%" },
  { key: "problem_rate", label: "问题率%" },
  { key: "organic_ratio_gmv", label: "自然GMV%" },
  { key: "organic_ratio_orders", label: "自然订单%" },
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
  { key: "order_gmv", label: "GMV" },
  { key: "merchant_income", label: "收入" },
  { key: "refund_count", label: "退款数" },
  { key: "cancel_count", label: "取消数" },
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
                        <KpiCard key={item.key} label={item.label} value={kpis[item.key]} unit={item.unit} />
                      ))}
                    </div>
                  </CardContent>
                </Card>
              )
            })}
          </TabsContent>

          <TabsContent value="trend">
            <Card>
              <CardHeader>
                <CardTitle>趋势图</CardTitle>
                <CardDescription>推广花费与有效订单 GMV 走势</CardDescription>
              </CardHeader>
              <CardContent>
                <TrendChart data={trend} />
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

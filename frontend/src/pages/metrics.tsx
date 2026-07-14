import { useEffect, useState } from "react"
import { Search } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select } from "@/components/ui/select"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Badge } from "@/components/ui/badge"
import { getStores, getAnalysis, type Store } from "@/api/client"

function formatNumber(v: any) {
  if (v === null || v === undefined || Number.isNaN(v)) return "-"
  if (typeof v === "number") return v.toLocaleString("zh-CN", { maximumFractionDigits: 2 })
  return v
}

export function MetricsPage() {
  const [stores, setStores] = useState<Store[]>([])
  const [storeName, setStoreName] = useState("")
  const [startDate, setStartDate] = useState(new Date().toISOString().split("T")[0])
  const [endDate, setEndDate] = useState(new Date().toISOString().split("T")[0])
  const [data, setData] = useState<any>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    getStores().then(setStores)
  }, [])

  const handleAnalyze = async () => {
    if (!storeName) return
    setLoading(true)
    try {
      const res = await getAnalysis(storeName, startDate, endDate)
      setData(res)
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
          <div className="grid grid-cols-4 gap-4 items-end">
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
        <>
          <div className="grid grid-cols-4 gap-4">
            {[
              { label: "推广花费", key: "promo_spend" },
              { label: "推广 GMV", key: "promo_gmv" },
              { label: "有效 ROI", key: "valid_roi" },
              { label: "退款率", key: "refund_rate" },
            ].map((k) => (
              <Card key={k.key}>
                <CardHeader className="pb-2">
                  <CardDescription>{k.label}</CardDescription>
                  <CardTitle className="text-2xl">{formatNumber(kpis[k.key])}</CardTitle>
                </CardHeader>
              </Card>
            ))}
          </div>

          <Card>
            <CardHeader>
              <CardTitle>商品指标</CardTitle>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>商品ID</TableHead>
                    <TableHead>商品名称</TableHead>
                    <TableHead>花费</TableHead>
                    <TableHead>GMV</TableHead>
                    <TableHead>有效订单收入</TableHead>
                    <TableHead>ROI</TableHead>
                    <TableHead>退款率</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {data.product_metrics.slice(0, 50).map((row: any, idx: number) => (
                    <TableRow key={idx}>
                      <TableCell className="font-mono text-xs">{row.product_id}</TableCell>
                      <TableCell>{row.product_name}</TableCell>
                      <TableCell>{formatNumber(row.promo_spend)}</TableCell>
                      <TableCell>{formatNumber(row.promo_gmv)}</TableCell>
                      <TableCell>{formatNumber(row.valid_merchant_income)}</TableCell>
                      <TableCell>{formatNumber(row.valid_roi)}</TableCell>
                      <TableCell>
                        <Badge variant={row.refund_rate > 0.3 ? "destructive" : "default"}>
                          {formatNumber(row.refund_rate)}
                        </Badge>
                      </TableCell>
                    </TableRow>
                  ))}
                  {data.product_metrics.length === 0 && (
                    <TableRow>
                      <TableCell colSpan={7} className="text-center text-muted-foreground">
                        无数据
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  )
}

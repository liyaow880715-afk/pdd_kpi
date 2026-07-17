import { useEffect, useState } from "react"
import { Search } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select } from "@/components/ui/select"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { getStores, getWechatOrders, type Store } from "@/api/client"

function formatNumber(v: any, digits = 2) {
  if (v === null || v === undefined || Number.isNaN(v)) return "-"
  if (typeof v === "number") return v.toLocaleString("zh-CN", { maximumFractionDigits: digits })
  return v
}

export function WechatOrdersPage() {
  const [stores, setStores] = useState<Store[]>([])
  const [storeName, setStoreName] = useState("")
  const [date, setDate] = useState(new Date().toISOString().split("T")[0])
  const [orders, setOrders] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState("")

  useEffect(() => {
    getStores("wechat").then((s) => {
      setStores(s)
      if (s.length > 0) setStoreName(s[0].name)
    })
  }, [])

  const handleQuery = async () => {
    if (!storeName) return
    setLoading(true)
    setMessage("")
    try {
      const data = await getWechatOrders(storeName, date)
      setOrders(data)
    } catch (err: any) {
      setMessage(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-4">
      <h2 className="text-2xl font-bold">微信订单</h2>

      {message && <div className="text-sm p-3 rounded-md bg-destructive/10 text-destructive">{message}</div>}

      <Card>
        <CardContent className="pt-6">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 items-end">
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
              <Label>日期</Label>
              <Input type="date" value={date} onChange={(e) => setDate(e.target.value)} />
            </div>
            <Button onClick={handleQuery} disabled={loading}>
              <Search className="h-4 w-4 mr-1" /> {loading ? "查询中..." : "查询"}
            </Button>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>订单明细（{orders.length} 条）</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="overflow-auto max-h-[600px]">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="text-xs">订单编号</TableHead>
                  <TableHead className="text-xs">商品名称</TableHead>
                  <TableHead className="text-xs">自定义 SKU</TableHead>
                  <TableHead className="text-xs">平台 SKU</TableHead>
                  <TableHead className="text-xs">数量</TableHead>
                  <TableHead className="text-xs">实付金额</TableHead>
                  <TableHead className="text-xs">实际收款</TableHead>
                  <TableHead className="text-xs">退款金额</TableHead>
                  <TableHead className="text-xs">技术服务费</TableHead>
                  <TableHead className="text-xs">带货费用</TableHead>
                  <TableHead className="text-xs">净收入</TableHead>
                  <TableHead className="text-xs">订单状态</TableHead>
                  <TableHead className="text-xs">达人</TableHead>
                  <TableHead className="text-xs">下单时间</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {orders.map((row, idx) => (
                  <TableRow key={idx}>
                    <TableCell className="text-xs whitespace-nowrap">{row.order_id}</TableCell>
                    <TableCell className="text-xs max-w-[200px] truncate">{row.product_name}</TableCell>
                    <TableCell className="text-xs">{row.sku_code}</TableCell>
                    <TableCell className="text-xs">{row.platform_sku_code}</TableCell>
                    <TableCell className="text-xs">{formatNumber(row.quantity, 0)}</TableCell>
                    <TableCell className="text-xs">{formatNumber(row.amount)}</TableCell>
                    <TableCell className="text-xs">{formatNumber(row.actual_revenue)}</TableCell>
                    <TableCell className="text-xs">{formatNumber(row.refund_amount)}</TableCell>
                    <TableCell className="text-xs">{formatNumber(row.tech_fee)}</TableCell>
                    <TableCell className="text-xs">{formatNumber(row.commission)}</TableCell>
                    <TableCell className="text-xs">{formatNumber(row.net_revenue)}</TableCell>
                    <TableCell className="text-xs">{row.order_status}</TableCell>
                    <TableCell className="text-xs">{row.kol_name}</TableCell>
                    <TableCell className="text-xs whitespace-nowrap">{row.order_time}</TableCell>
                  </TableRow>
                ))}
                {orders.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={14} className="text-center text-muted-foreground">
                      暂无数据
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

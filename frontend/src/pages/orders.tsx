import { useEffect, useState } from "react"
import { Search } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select } from "@/components/ui/select"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { getStores, getOrders, type Store } from "@/api/client"

export function OrdersPage() {
  const [stores, setStores] = useState<Store[]>([])
  const [storeName, setStoreName] = useState("")
  const [date, setDate] = useState(new Date().toISOString().split("T")[0])
  const [orders, setOrders] = useState<any[]>([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    getStores("pdd").then(setStores)
  }, [])

  const handleSearch = async () => {
    if (!storeName) return
    setLoading(true)
    try {
      const res = await getOrders(storeName, date)
      setOrders(res)
    } catch (err: any) {
      alert(err.message)
    } finally {
      setLoading(false)
    }
  }

  const columns = orders.length > 0 ? Object.keys(orders[0]) : []

  return (
    <div className="space-y-4">
      <h2 className="text-2xl font-bold">订单明细</h2>
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
            <Button onClick={handleSearch} disabled={loading}>
              <Search className="h-4 w-4 mr-1" /> {loading ? "查询中..." : "查询"}
            </Button>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>订单列表（共 {orders.length} 条）</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                {columns.slice(0, 10).map((col) => (
                  <TableHead key={col}>{col}</TableHead>
                ))}
              </TableRow>
            </TableHeader>
            <TableBody>
              {orders.slice(0, 100).map((row, idx) => (
                <TableRow key={idx}>
                  {columns.slice(0, 10).map((col) => (
                    <TableCell key={col} className="text-xs max-w-[200px] truncate">
                      {String(row[col] ?? "")}
                    </TableCell>
                  ))}
                </TableRow>
              ))}
              {orders.length === 0 && (
                <TableRow>
                  <TableCell colSpan={Math.max(columns.length, 1)} className="text-center text-muted-foreground">
                    无订单数据
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  )
}

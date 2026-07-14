import { useEffect, useState } from "react"
import { Save, RefreshCw } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select } from "@/components/ui/select"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { getStores, getCosts, saveCosts, refreshCostCodes, type Store, type Cost } from "@/api/client"

export function CostsPage() {
  const [stores, setStores] = useState<Store[]>([])
  const [storeName, setStoreName] = useState("")
  const [costs, setCosts] = useState<Cost[]>([])
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState("")

  useEffect(() => {
    getStores().then(setStores)
  }, [])

  useEffect(() => {
    if (!storeName) return
    setLoading(true)
    getCosts(storeName)
      .then(setCosts)
      .finally(() => setLoading(false))
  }, [storeName])

  const updateCost = (idx: number, field: keyof Cost, value: any) => {
    const next = [...costs]
    next[idx] = { ...next[idx], [field]: value }
    setCosts(next)
  }

  const handleSave = async () => {
    if (!storeName) return
    try {
      await saveCosts(storeName, costs)
      setMessage("保存成功")
    } catch (err: any) {
      setMessage(err.message)
    }
  }

  const handleRefresh = async () => {
    if (!storeName) return
    try {
      await refreshCostCodes(storeName)
      const data = await getCosts(storeName)
      setCosts(data)
      setMessage("已刷新商家编码")
    } catch (err: any) {
      setMessage(err.message)
    }
  }

  return (
    <div className="space-y-4">
      <h2 className="text-2xl font-bold">成本管理</h2>
      {message && (
        <div className={`text-sm p-3 rounded-md ${message.includes("成功") || message.includes("刷新") ? "bg-green-100 text-green-800" : "bg-destructive/10 text-destructive"}`}>
          {message}
        </div>
      )}
      <Card>
        <CardContent className="pt-6">
          <div className="flex items-end gap-4">
            <div className="space-y-2 w-64">
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
            <Button variant="outline" onClick={handleRefresh} disabled={!storeName}>
              <RefreshCw className="h-4 w-4 mr-1" /> 刷新编码
            </Button>
            <Button onClick={handleSave} disabled={!storeName}>
              <Save className="h-4 w-4 mr-1" /> 保存
            </Button>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardContent className="pt-6">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>商家编码</TableHead>
                <TableHead>商品名称</TableHead>
                <TableHead>商品成本</TableHead>
                <TableHead>物流成本</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {costs.map((cost, idx) => (
                <TableRow key={cost.merchant_code}>
                  <TableCell className="font-mono text-xs">{cost.merchant_code}</TableCell>
                  <TableCell>
                    <Input value={cost.product_name} onChange={(e) => updateCost(idx, "product_name", e.target.value)} />
                  </TableCell>
                  <TableCell>
                    <Input type="number" value={cost.product_cost} onChange={(e) => updateCost(idx, "product_cost", parseFloat(e.target.value) || 0)} />
                  </TableCell>
                  <TableCell>
                    <Input type="number" value={cost.logistics_cost} onChange={(e) => updateCost(idx, "logistics_cost", parseFloat(e.target.value) || 0)} />
                  </TableCell>
                </TableRow>
              ))}
              {costs.length === 0 && !loading && (
                <TableRow>
                  <TableCell colSpan={4} className="text-center text-muted-foreground">
                    请选择店铺
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

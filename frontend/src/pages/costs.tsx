import { useEffect, useState } from "react"
import { Save, RefreshCw, Link2, AlertCircle } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Select } from "@/components/ui/select"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import {
  getGlobalCosts,
  saveGlobalCosts,
  refreshGlobalCostCodes,
  getUnmappedProducts,
  mapProductToMerchantCode,
  type Cost,
} from "@/api/client"

export function CostsPage() {
  const [costs, setCosts] = useState<Cost[]>([])
  const [unmapped, setUnmapped] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState("")
  const [mappingCodes, setMappingCodes] = useState<Record<string, string>>({})

  const fetchData = async () => {
    setLoading(true)
    try {
      const [costsData, unmappedData] = await Promise.all([getGlobalCosts(), getUnmappedProducts()])
      setCosts(costsData)
      setUnmapped(unmappedData)
    } catch (err: any) {
      setMessage(err.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
  }, [])

  const updateCost = (idx: number, field: keyof Cost, value: any) => {
    const next = [...costs]
    next[idx] = { ...next[idx], [field]: value }
    setCosts(next)
  }

  const handleSave = async () => {
    try {
      await saveGlobalCosts(costs)
      setMessage("保存成功")
    } catch (err: any) {
      setMessage(err.message)
    }
  }

  const handleRefresh = async () => {
    try {
      const res = await refreshGlobalCostCodes()
      await fetchData()
      setMessage(`已刷新商家编码，新增 ${res.added} 个`)
    } catch (err: any) {
      setMessage(err.message)
    }
  }

  const handleMap = async (productId: string) => {
    const merchantCode = mappingCodes[productId]
    if (!merchantCode) return
    try {
      await mapProductToMerchantCode(productId, merchantCode)
      setMappingCodes((prev) => ({ ...prev, [productId]: "" }))
      await fetchData()
      setMessage("映射成功")
    } catch (err: any) {
      setMessage(err.message)
    }
  }

  return (
    <div className="space-y-4">
      <h2 className="text-2xl font-bold">成本管理</h2>
      {message && (
        <div
          className={`text-sm p-3 rounded-md ${
            message.includes("成功") || message.includes("刷新") || message.includes("新增")
              ? "bg-green-100 text-green-800"
              : "bg-destructive/10 text-destructive"
          }`}
        >
          {message}
        </div>
      )}

      <Card>
        <CardHeader>
          <CardTitle>商家编码成本（全店铺通用）</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex gap-2">
            <Button variant="outline" onClick={handleRefresh} disabled={loading}>
              <RefreshCw className="h-4 w-4 mr-1" /> 刷新编码
            </Button>
            <Button onClick={handleSave}>
              <Save className="h-4 w-4 mr-1" /> 保存
            </Button>
          </div>
          <div className="overflow-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>商家编码</TableHead>
                  <TableHead>商品名称</TableHead>
                  <TableHead>商品成本/件</TableHead>
                  <TableHead>物流成本/件</TableHead>
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
                      点击「刷新编码」从订单中提取商家编码
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <AlertCircle className="h-5 w-5 text-yellow-500" />
            未映射商家编码的商品
          </CardTitle>
        </CardHeader>
        <CardContent>
          {unmapped.length === 0 ? (
            <div className="text-sm text-muted-foreground py-4 text-center">所有商品都有商家编码或已完成映射</div>
          ) : (
            <div className="overflow-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>商品ID</TableHead>
                    <TableHead>商品名称</TableHead>
                    <TableHead>出现店铺</TableHead>
                    <TableHead>订单天数</TableHead>
                    <TableHead>映射到商家编码</TableHead>
                    <TableHead className="text-right">操作</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {unmapped.map((row: any) => (
                    <TableRow key={row.product_id}>
                      <TableCell className="font-mono text-xs">{row.product_id}</TableCell>
                      <TableCell>{row.product_name}</TableCell>
                      <TableCell>{row.store_name}</TableCell>
                      <TableCell>{row.order_count}</TableCell>
                      <TableCell>
                        <div className="flex gap-2">
                          <Select
                            value={mappingCodes[row.product_id] || ""}
                            onChange={(e) => setMappingCodes((prev) => ({ ...prev, [row.product_id]: e.target.value }))}
                          >
                            <option value="">选择或输入</option>
                            {costs.map((c) => (
                              <option key={c.merchant_code} value={c.merchant_code}>
                                {c.merchant_code} {c.product_name ? `(${c.product_name})` : ""}
                              </option>
                            ))}
                          </Select>
                          <Input
                            placeholder="新编码"
                            className="w-24"
                            value={mappingCodes[row.product_id] || ""}
                            onChange={(e) => setMappingCodes((prev) => ({ ...prev, [row.product_id]: e.target.value }))}
                          />
                        </div>
                      </TableCell>
                      <TableCell className="text-right">
                        <Button size="sm" onClick={() => handleMap(row.product_id)} disabled={!mappingCodes[row.product_id]}>
                          <Link2 className="h-4 w-4 mr-1" /> 映射
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

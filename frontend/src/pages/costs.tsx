import { useEffect, useRef, useState } from "react"
import { Save, RefreshCw, Link2, AlertCircle, CheckCircle2, Download, Upload } from "lucide-react"
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
  exportGlobalCosts,
  importGlobalCosts,
  type Cost,
} from "@/api/client"

interface UnmappedRow {
  product_id: string
  product_name: string
  style_id: string
  style_name: string
  store_name: string
  order_count: number
  first_date: string
}

export function CostsPage() {
  const [costs, setCosts] = useState<Cost[]>([])
  const [unmapped, setUnmapped] = useState<UnmappedRow[]>([])
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState("")
  const [mappingCodes, setMappingCodes] = useState<Record<string, string>>({})
  const fileInputRef = useRef<HTMLInputElement>(null)

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

  const handleExportPending = async () => {
    try {
      const blob = await exportGlobalCosts(true)
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement("a")
      a.href = url
      a.download = `待维护商家编码_${new Date().toISOString().split("T")[0]}.csv`
      document.body.appendChild(a)
      a.click()
      a.remove()
      window.URL.revokeObjectURL(url)
      setMessage("导出成功")
    } catch (err: any) {
      setMessage(err.message)
    }
  }

  const handleImportClick = () => {
    fileInputRef.current?.click()
  }

  const handleImportFile = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    try {
      const res = await importGlobalCosts(file)
      await fetchData()
      setMessage(`导入成功，更新 ${res.updated} 条`)
    } catch (err: any) {
      setMessage(err.message)
    } finally {
      e.target.value = ""
    }
  }

  const mappingKey = (row: UnmappedRow) => `${row.product_id}::${row.style_id}`

  const handleMap = async (row: UnmappedRow) => {
    const key = mappingKey(row)
    const merchantCode = mappingCodes[key]
    if (!merchantCode) return
    try {
      await mapProductToMerchantCode(
        row.product_id,
        merchantCode,
        row.style_id === "-" ? undefined : row.style_id,
        row.product_name
      )
      setMappingCodes((prev) => ({ ...prev, [key]: "" }))
      await fetchData()
      setMessage("映射成功")
    } catch (err: any) {
      setMessage(err.message)
    }
  }

  const renderCostTable = (rows: Cost[], title: string, variant: "warning" | "success", icon: React.ReactNode) => {
    return (
      <div className="space-y-2">
        <h3 className="text-sm font-semibold flex items-center gap-2">
          {icon}
          {title}
          <span className="rounded-full bg-muted px-2 py-0.5 text-xs text-muted-foreground">{rows.length}</span>
        </h3>
        <div className="overflow-auto rounded-md border">
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
              {rows.map((cost) => {
                const idx = costs.findIndex((c) => c.merchant_code === cost.merchant_code)
                return (
                  <TableRow key={cost.merchant_code}>
                    <TableCell className="font-mono text-xs">{cost.merchant_code}</TableCell>
                    <TableCell>
                      <Input value={cost.product_name} onChange={(e) => updateCost(idx, "product_name", e.target.value)} />
                    </TableCell>
                    <TableCell>
                      <Input
                        type="number"
                        value={cost.product_cost}
                        onChange={(e) => updateCost(idx, "product_cost", parseFloat(e.target.value) || 0)}
                      />
                    </TableCell>
                    <TableCell>
                      <Input
                        type="number"
                        value={cost.logistics_cost}
                        onChange={(e) => updateCost(idx, "logistics_cost", parseFloat(e.target.value) || 0)}
                      />
                    </TableCell>
                  </TableRow>
                )
              })}
              {rows.length === 0 && (
                <TableRow>
                  <TableCell colSpan={4} className="text-center text-muted-foreground py-4">
                    {variant === "warning" ? "暂无待维护商家编码" : "暂无已维护商家编码"}
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </div>
      </div>
    )
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
          <div className="flex items-center justify-between">
            <CardTitle>商家编码成本（全店铺通用）</CardTitle>
            <div className="flex flex-wrap gap-2">
              <Button variant="outline" onClick={handleExportPending} disabled={loading}>
                <Download className="h-4 w-4 mr-1" /> 导出待维护
              </Button>
              <Button variant="outline" onClick={handleImportClick} disabled={loading}>
                <Upload className="h-4 w-4 mr-1" /> 导入成本
              </Button>
              <input
                ref={fileInputRef}
                type="file"
                accept=".csv"
                className="hidden"
                onChange={handleImportFile}
              />
              <Button variant="outline" onClick={handleRefresh} disabled={loading}>
                <RefreshCw className="h-4 w-4 mr-1" /> 刷新编码
              </Button>
              <Button onClick={handleSave}>
                <Save className="h-4 w-4 mr-1" /> 保存
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          {renderCostTable(
            costs.filter((c) => c.product_cost <= 0 || c.logistics_cost <= 0),
            "待维护商家编码",
            "warning",
            <AlertCircle className="h-5 w-5 text-yellow-500" />
          )}
          {renderCostTable(
            costs.filter((c) => c.product_cost > 0 && c.logistics_cost > 0),
            "已维护商家编码",
            "success",
            <CheckCircle2 className="h-5 w-5 text-green-500" />
          )}
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
                    <TableHead>样式ID</TableHead>
                    <TableHead>样式/规格</TableHead>
                    <TableHead>出现店铺</TableHead>
                    <TableHead>订单天数</TableHead>
                    <TableHead>映射到商家编码</TableHead>
                    <TableHead className="text-right">操作</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {unmapped.map((row) => {
                    const key = mappingKey(row)
                    return (
                      <TableRow key={key}>
                        <TableCell className="font-mono text-xs">{row.product_id}</TableCell>
                        <TableCell>{row.product_name}</TableCell>
                        <TableCell className="font-mono text-xs">{row.style_id}</TableCell>
                        <TableCell>{row.style_name}</TableCell>
                        <TableCell>{row.store_name}</TableCell>
                        <TableCell>{row.order_count}</TableCell>
                        <TableCell>
                          <div className="flex gap-2">
                            <Select
                              value={mappingCodes[key] || ""}
                              onChange={(e) => setMappingCodes((prev) => ({ ...prev, [key]: e.target.value }))}
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
                              value={mappingCodes[key] || ""}
                              onChange={(e) => setMappingCodes((prev) => ({ ...prev, [key]: e.target.value }))}
                            />
                          </div>
                        </TableCell>
                        <TableCell className="text-right">
                          <Button size="sm" onClick={() => handleMap(row)} disabled={!mappingCodes[key]}>
                            <Link2 className="h-4 w-4 mr-1" /> 映射
                          </Button>
                        </TableCell>
                      </TableRow>
                    )
                  })}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

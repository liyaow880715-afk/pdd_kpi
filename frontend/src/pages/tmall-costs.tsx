import { useEffect, useState } from "react"
import { Upload, Download, RotateCcw, Save } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs"
import { Select } from "@/components/ui/select"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Badge } from "@/components/ui/badge"
import {
  getStores,
  getTmallCosts,
  saveTmallCosts,
  importTmallCosts,
  refreshTmallCostCodes,
  getTmallUnmappedProducts,
  type Store,
  type TmallCost,
} from "@/api/client"

export function TmallCostsPage() {
  const [stores, setStores] = useState<Store[]>([])
  const [storeName, setStoreName] = useState("")
  const [tab, setTab] = useState("costs")
  const [costs, setCosts] = useState<TmallCost[]>([])
  const [unmapped, setUnmapped] = useState<any[]>([])
  const [file, setFile] = useState<File | null>(null)
  const [message, setMessage] = useState("")
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    getStores("tmall").then((s) => {
      setStores(s)
      if (s.length > 0) setStoreName(s[0].name)
    })
  }, [])

  useEffect(() => {
    if (!storeName) return
    loadData()
  }, [storeName])

  const loadData = async () => {
    try {
      const costsData = await getTmallCosts()
      setCosts(costsData || [])
      const unmappedData = await getTmallUnmappedProducts(undefined, undefined, storeName)
      setUnmapped(unmappedData || [])
    } catch (err: any) {
      setMessage(err.message)
    }
  }

  const handleSave = async () => {
    try {
      await saveTmallCosts(costs)
      setMessage("保存成功")
    } catch (err: any) {
      setMessage(err.message)
    }
  }

  const handleUpload = async () => {
    if (!file) return
    setLoading(true)
    try {
      await importTmallCosts(file)
      setMessage("上传成功")
      setFile(null)
      await loadData()
    } catch (err: any) {
      setMessage(err.message)
    } finally {
      setLoading(false)
    }
  }

  const handleRefresh = async () => {
    setLoading(true)
    try {
      await refreshTmallCostCodes()
      setMessage("刷新成功")
      await loadData()
    } catch (err: any) {
      setMessage(err.message)
    } finally {
      setLoading(false)
    }
  }

  const updateCost = (index: number, field: keyof TmallCost, value: string | number) => {
    setCosts((prev) => {
      const next = [...prev]
      next[index] = { ...next[index], [field]: value }
      return next
    })
  }

  return (
    <div className="space-y-4">
      <h2 className="text-2xl font-bold">天猫成本</h2>

      {message && <div className="text-sm p-3 rounded-md bg-primary/10">{message}</div>}

      <Card>
        <CardContent className="pt-6">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 items-end">
            <div className="space-y-2">
              <Label>店铺（仅用于未映射商品筛选）</Label>
              <Select value={storeName} onChange={(e) => setStoreName(e.target.value)}>
                <option value="">全部店铺</option>
                {stores.map((s) => (
                  <option key={s.id} value={s.name}>
                    {s.name}
                  </option>
                ))}
              </Select>
            </div>
            <div className="space-y-2">
              <Label>成本 CSV</Label>
              <Input type="file" accept=".csv" onChange={(e) => setFile(e.target.files?.[0] || null)} />
            </div>
            <Button onClick={handleUpload} disabled={!file || loading}>
              <Upload className="h-4 w-4 mr-1" /> 上传成本
            </Button>
            <Button variant="outline" onClick={handleRefresh} disabled={loading}>
              <RotateCcw className="h-4 w-4 mr-1" /> 刷新编码
            </Button>
          </div>
        </CardContent>
      </Card>

      <Tabs value={tab} onValueChange={setTab}>
        <TabsList>
          <TabsTrigger value="costs">成本管理</TabsTrigger>
          <TabsTrigger value="unmapped">未映射商品</TabsTrigger>
        </TabsList>

        <TabsContent value="costs" className="space-y-4">
          <div className="flex gap-2">
            <Button onClick={handleSave}>
              <Save className="h-4 w-4 mr-1" /> 保存成本
            </Button>
            <a
              href="/api/tmall/costs/export"
              className="inline-flex items-center justify-center rounded-md border border-input bg-background px-4 py-2 text-sm font-medium shadow-sm hover:bg-accent hover:text-accent-foreground"
            >
              <Download className="h-4 w-4 mr-1" /> 下载成本
            </a>
          </div>

          <Card>
            <CardHeader>
              <CardTitle>商家编码成本</CardTitle>
              <CardDescription>按商家编码设置单品成本</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="overflow-auto max-h-[600px]">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="text-xs">商家编码</TableHead>
                      <TableHead className="text-xs">商品名称</TableHead>
                      <TableHead className="text-xs">产品成本</TableHead>
                      <TableHead className="text-xs">物流成本</TableHead>
                      <TableHead className="text-xs">更新时间</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {costs.map((entry, idx) => (
                      <TableRow key={entry.merchant_code}>
                        <TableCell className="text-xs font-mono">{entry.merchant_code}</TableCell>
                        <TableCell className="text-xs max-w-[200px] truncate">{entry.product_name || "-"}</TableCell>
                        <TableCell>
                          <Input
                            type="number"
                            step="0.01"
                            className="w-24 h-8 text-xs"
                            value={entry.product_cost ?? ""}
                            onChange={(e) => updateCost(idx, "product_cost", parseFloat(e.target.value))}
                          />
                        </TableCell>
                        <TableCell>
                          <Input
                            type="number"
                            step="0.01"
                            className="w-24 h-8 text-xs"
                            value={entry.logistics_cost ?? ""}
                            onChange={(e) => updateCost(idx, "logistics_cost", parseFloat(e.target.value))}
                          />
                        </TableCell>
                        <TableCell className="text-xs text-muted-foreground">{entry.updated_at || "-"}</TableCell>
                      </TableRow>
                    ))}
                    {costs.length === 0 && (
                      <TableRow>
                        <TableCell colSpan={5} className="text-center text-muted-foreground">
                          暂无成本数据
                        </TableCell>
                      </TableRow>
                    )}
                  </TableBody>
                </Table>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="unmapped">
          <Card>
            <CardHeader>
              <CardTitle>未映射商家编码</CardTitle>
              <CardDescription>这些商品需要先在成本管理中维护商家编码成本</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex flex-wrap gap-2">
                {unmapped.length === 0 && <span className="text-muted-foreground text-sm">暂无未映射商品</span>}
                {unmapped.map((name) => (
                  <Badge key={name} variant="secondary" className="max-w-[240px] truncate" title={name}>
                    {name}
                  </Badge>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}

import { useEffect, useRef, useState } from "react"
import { Coins, Download, Upload, Plus, Save, FileSpreadsheet } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { FileDropzone } from "@/components/ui/file-dropzone"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import {
  getDouyinCosts,
  saveDouyinCosts,
  exportDouyinCosts,
  importDouyinCosts,
  getDouyinUnmappedProducts,
  type DouyinCost,
} from "@/api/client"

function getDefaultDates() {
  const end = new Date().toISOString().split("T")[0]
  const startDate = new Date()
  startDate.setDate(startDate.getDate() - 30)
  const start = startDate.toISOString().split("T")[0]
  return { start, end }
}

export function DouyinCostsPage() {
  const [costs, setCosts] = useState<DouyinCost[]>([])
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState("")
  const [importFile, setImportFile] = useState<File | null>(null)
  const [unmapped, setUnmapped] = useState<{ product_id: string; product_name: string }[]>([])
  const { start: defaultStart, end: defaultEnd } = getDefaultDates()
  const [umStart, setUmStart] = useState(defaultStart)
  const [umEnd, setUmEnd] = useState(defaultEnd)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const fetchCosts = async () => {
    const data = await getDouyinCosts()
    setCosts(data)
  }

  useEffect(() => {
    fetchCosts()
  }, [])

  const handleSave = async () => {
    setLoading(true)
    setMessage("")
    try {
      await saveDouyinCosts(costs)
      setMessage("保存成功")
      await fetchCosts()
    } catch (err: any) {
      setMessage(err.message)
    } finally {
      setLoading(false)
    }
  }

  const handleAdd = () => {
    setCosts((prev) => [
      ...prev,
      { product_id: "", product_name: "", product_cost: 0, logistics_cost: 0 },
    ])
  }

  const updateRow = (index: number, field: keyof DouyinCost, value: string | number) => {
    setCosts((prev) => {
      const next = [...prev]
      next[index] = { ...next[index], [field]: value }
      return next
    })
  }

  const handleExport = async () => {
    try {
      const blob = await exportDouyinCosts()
      const url = URL.createObjectURL(blob)
      const a = document.createElement("a")
      a.href = url
      a.download = `douyin_costs_${new Date().toISOString().split("T")[0]}.csv`
      document.body.appendChild(a)
      a.click()
      a.remove()
      URL.revokeObjectURL(url)
    } catch (err: any) {
      setMessage(err.message)
    }
  }

  const handleImport = async () => {
    if (!importFile) {
      setMessage("请先选择 CSV 文件")
      return
    }
    setLoading(true)
    setMessage("")
    try {
      const res = await importDouyinCosts(importFile)
      setMessage(`导入成功，更新 ${res.updated} 条记录`)
      setImportFile(null)
      await fetchCosts()
    } catch (err: any) {
      setMessage(err.message)
    } finally {
      setLoading(false)
    }
  }

  const fetchUnmapped = async () => {
    setMessage("")
    try {
      const data = await getDouyinUnmappedProducts(umStart, umEnd)
      setUnmapped(data)
    } catch (err: any) {
      setMessage(err.message)
    }
  }

  const addUnmappedRow = (item: { product_id: string; product_name: string }) => {
    if (costs.some((c) => c.product_id === item.product_id)) return
    setCosts((prev) => [
      ...prev,
      {
        product_id: item.product_id,
        product_name: item.product_name,
        product_cost: 0,
        logistics_cost: 0,
      },
    ])
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <Coins className="h-6 w-6" />
        <h2 className="text-2xl font-bold">抖音成本管理</h2>
      </div>

      {message && (
        <div
          className={`text-sm p-3 rounded-md ${
            message.includes("成功")
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
            <div>
              <CardTitle className="flex items-center gap-2">
                <FileSpreadsheet className="h-4 w-4" />
                商品成本配置
              </CardTitle>
              <CardDescription>按商品 ID 维护商品成本和物流成本</CardDescription>
            </div>
            <div className="flex gap-2">
              <Button variant="outline" size="sm" onClick={handleExport}>
                <Download className="h-4 w-4 mr-1" /> 导出
              </Button>
              <Button variant="outline" size="sm" onClick={handleAdd}>
                <Plus className="h-4 w-4 mr-1" /> 新增
              </Button>
              <Button size="sm" onClick={handleSave} disabled={loading}>
                <Save className="h-4 w-4 mr-1" /> {loading ? "保存中..." : "保存"}
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">批量导入 CSV</label>
              <FileDropzone
                accept=".csv"
                label="点击或拖拽上传成本 CSV"
                description="列：商品ID、商品名称、商品成本、物流成本"
                value={importFile}
                onChange={setImportFile}
              />
            </div>
            <div className="flex items-end">
              <Button onClick={handleImport} disabled={!importFile || loading} className="w-full">
                <Upload className="h-4 w-4 mr-1" /> 导入
              </Button>
            </div>
          </div>

          <div className="overflow-auto max-h-[50vh] border rounded-md">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>商品ID</TableHead>
                  <TableHead>商品名称</TableHead>
                  <TableHead className="text-right">商品成本/件</TableHead>
                  <TableHead className="text-right">物流成本/件</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {costs.map((row, idx) => (
                  <TableRow key={idx}>
                    <TableCell>
                      <Input
                        value={row.product_id}
                        onChange={(e) => updateRow(idx, "product_id", e.target.value)}
                        placeholder="商品ID"
                      />
                    </TableCell>
                    <TableCell>
                      <Input
                        value={row.product_name}
                        onChange={(e) => updateRow(idx, "product_name", e.target.value)}
                        placeholder="商品名称"
                      />
                    </TableCell>
                    <TableCell>
                      <Input
                        type="number"
                        min={0}
                        step={0.01}
                        value={row.product_cost}
                        onChange={(e) => updateRow(idx, "product_cost", parseFloat(e.target.value) || 0)}
                        className="text-right"
                      />
                    </TableCell>
                    <TableCell>
                      <Input
                        type="number"
                        min={0}
                        step={0.01}
                        value={row.logistics_cost}
                        onChange={(e) => updateRow(idx, "logistics_cost", parseFloat(e.target.value) || 0)}
                        className="text-right"
                      />
                    </TableCell>
                  </TableRow>
                ))}
                {costs.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={4} className="text-center text-muted-foreground py-8">
                      暂无成本配置，点击「新增」或「导入」添加
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
          <CardTitle>未维护成本的商品</CardTitle>
          <CardDescription>从指定日期范围的抖音指标中找出没有成本记录的商品</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 items-end">
            <div className="space-y-2">
              <label className="text-sm font-medium">开始日期</label>
              <Input type="date" value={umStart} onChange={(e) => setUmStart(e.target.value)} />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">结束日期</label>
              <Input type="date" value={umEnd} onChange={(e) => setUmEnd(e.target.value)} />
            </div>
            <Button onClick={fetchUnmapped}>查询未维护商品</Button>
          </div>

          <div className="overflow-auto max-h-[40vh] border rounded-md">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>商品ID</TableHead>
                  <TableHead>商品名称</TableHead>
                  <TableHead className="text-right">操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {unmapped.map((item) => (
                  <TableRow key={item.product_id}>
                    <TableCell>{item.product_id}</TableCell>
                    <TableCell>{item.product_name}</TableCell>
                    <TableCell className="text-right">
                      <Button variant="ghost" size="sm" onClick={() => addUnmappedRow(item)}>
                        <Plus className="h-4 w-4 mr-1" /> 添加
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
                {unmapped.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={3} className="text-center text-muted-foreground py-8">
                      暂无未维护商品
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>

      <input ref={fileInputRef} type="file" accept=".csv" className="sr-only" />
    </div>
  )
}

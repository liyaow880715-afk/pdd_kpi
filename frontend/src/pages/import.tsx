import { useEffect, useState } from "react"
import { Upload, Trash2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select } from "@/components/ui/select"
import { FileDropzone } from "@/components/ui/file-dropzone"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { getStores, importData, getRecords, deleteRecord, type Store, type ImportRecord } from "@/api/client"

function getYesterday() {
  const d = new Date()
  d.setDate(d.getDate() - 1)
  return d.toISOString().split("T")[0]
}

export function ImportPage() {
  const [stores, setStores] = useState<Store[]>([])
  const [records, setRecords] = useState<ImportRecord[]>([])
  const [storeName, setStoreName] = useState("")
  const [importDate, setImportDate] = useState(getYesterday())
  const [promoFile, setPromoFile] = useState<File | null>(null)
  const [orderFile, setOrderFile] = useState<File | null>(null)
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState("")

  useEffect(() => {
    getStores().then(setStores)
    fetchRecords()
  }, [])

  const fetchRecords = async () => {
    const data = await getRecords()
    setRecords(data)
  }

  const handleImport = async () => {
    if (!storeName) {
      setMessage("请选择店铺")
      return
    }
    if (!promoFile && !orderFile) {
      setMessage("请至少上传推广数据或订单数据中的一个")
      return
    }
    setLoading(true)
    setMessage("")
    try {
      const formData = new FormData()
      formData.append("store_name", storeName)
      formData.append("import_date", importDate)
      if (promoFile) formData.append("promo_file", promoFile)
      if (orderFile) formData.append("order_file", orderFile)
      const res = await importData(formData)
      if (res.error) {
        setMessage(res.error)
        return
      }
      const parts = []
      if (res.computed) {
        const filterInfo = res.original_order_rows && res.original_order_rows !== res.order_rows
          ? `（订单 CSV 共 ${res.original_order_rows} 行，按日期过滤后保留 ${res.order_rows} 行）`
          : ""
        parts.push(`商品 ${res.product_rows} 行，样式 ${res.style_rows} 行，订单 ${res.order_rows} 行 ${filterInfo}`)
      } else {
        if (res.promo_saved) parts.push("推广数据已保存")
        if (res.orders_saved) parts.push(`订单 ${res.order_rows} 行已保存`)
      }
      const msg = res.message ? `${res.message}` : `导入成功：${parts.join("，")}`
      setMessage(msg)
      setPromoFile(null)
      setOrderFile(null)
      fetchRecords()
    } catch (err: any) {
      setMessage(err.message)
    } finally {
      setLoading(false)
    }
  }

  const handleDelete = async (storeName: string, date: string) => {
    if (!confirm("确定删除该日数据？")) return
    try {
      await deleteRecord(storeName, date)
      fetchRecords()
    } catch (err: any) {
      setMessage(err.message)
    }
  }

  return (
    <div className="space-y-4">
      <h2 className="text-2xl font-bold">数据导入</h2>
      {message && (
        <div className={`text-sm p-3 rounded-md ${message.includes("成功") ? "bg-green-100 text-green-800" : "bg-destructive/10 text-destructive"}`}>
          {message}
        </div>
      )}
      <Card>
        <CardHeader>
          <CardTitle>导入每日数据</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
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
              <Input type="date" value={importDate} onChange={(e) => setImportDate(e.target.value)} />
            </div>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>推广数据 Excel</Label>
              <FileDropzone
                accept=".xls,.xlsx"
                label="点击或拖拽上传推广 Excel"
                description="支持 .xls / .xlsx"
                value={promoFile}
                onChange={setPromoFile}
              />
            </div>
            <div className="space-y-2">
              <Label>订单数据 CSV</Label>
              <FileDropzone
                accept=".csv"
                label="点击或拖拽上传订单 CSV"
                description="支持 .csv"
                value={orderFile}
                onChange={setOrderFile}
              />
            </div>
          </div>
          <Button onClick={handleImport} disabled={loading}>
            <Upload className="h-4 w-4 mr-1" /> {loading ? "导入中..." : "开始导入"}
          </Button>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>导入历史</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>日期</TableHead>
                <TableHead>店铺</TableHead>
                <TableHead>商品/样式/订单</TableHead>
                <TableHead>文件名</TableHead>
                <TableHead className="text-right">操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {records.map((r) => (
                <TableRow key={`${r.store_name}-${r.date}`}>
                  <TableCell>{r.date}</TableCell>
                  <TableCell>{r.store_name}</TableCell>
                  <TableCell>{r.product_rows} / {r.style_rows} / {r.order_rows}</TableCell>
                  <TableCell className="text-xs max-w-xs truncate">
                    {r.promo_file} / {r.order_file}
                  </TableCell>
                  <TableCell className="text-right">
                    <Button variant="ghost" size="sm" onClick={() => handleDelete(r.store_name, r.date)}>
                      <Trash2 className="h-4 w-4 text-destructive" />
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
              {records.length === 0 && (
                <TableRow>
                  <TableCell colSpan={5} className="text-center text-muted-foreground">
                    暂无导入记录
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

import { useEffect, useState } from "react"
import { BarChart3, Store, Upload } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { getStores, getRecords } from "@/api/client"

export function DashboardPage() {
  const [storeCount, setStoreCount] = useState(0)
  const [recordCount, setRecordCount] = useState(0)

  useEffect(() => {
    getStores().then((s) => setStoreCount(s.length))
    getRecords().then((r) => setRecordCount(r.length))
  }, [])

  const cards = [
    { title: "店铺数量", value: storeCount, icon: Store },
    { title: "导入记录", value: recordCount, icon: Upload },
    { title: "功能模块", value: 8, icon: BarChart3 },
  ]

  return (
    <div className="space-y-4">
      <h2 className="text-2xl font-bold">总览</h2>
      <p className="text-muted-foreground">欢迎使用 PDD BI Dashboard。</p>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {cards.map((c) => (
          <Card key={c.title}>
            <CardHeader className="pb-2 flex flex-row items-center justify-between">
              <CardTitle className="text-sm font-medium">{c.title}</CardTitle>
              <c.icon className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold">{c.value}</div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  )
}

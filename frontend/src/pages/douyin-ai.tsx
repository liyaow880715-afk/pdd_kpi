import { useEffect, useState } from "react"
import { Sparkles, TestTube, Save } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select } from "@/components/ui/select"
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs"
import { getStores, getDouyinAiConfig, updateDouyinAiConfig, testDouyinAi, generateDouyinAiReport, type Store } from "@/api/client"

export function DouyinAiPage() {
  const [stores, setStores] = useState<Store[]>([])
  const [config, setConfig] = useState<Record<string, any>>({})
  const [storeName, setStoreName] = useState("")
  const [startDate, setStartDate] = useState(new Date().toISOString().split("T")[0])
  const [endDate, setEndDate] = useState(new Date().toISOString().split("T")[0])
  const [report, setReport] = useState("")
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState("")
  const [activeTab, setActiveTab] = useState("config")

  useEffect(() => {
    getStores("douyin").then(setStores)
    getDouyinAiConfig().then(setConfig)
  }, [])

  const updateConfig = (key: string, value: any) => {
    setConfig((prev) => ({ ...prev, [key]: value }))
  }

  const handleSave = async () => {
    try {
      await updateDouyinAiConfig(config)
      setMessage("配置已保存")
    } catch (err: any) {
      setMessage(err.message)
    }
  }

  const handleTest = async () => {
    try {
      const res = await testDouyinAi(config)
      setMessage(`测试连接：${res.status || JSON.stringify(res)}`)
    } catch (err: any) {
      setMessage(err.message)
    }
  }

  const handleReport = async () => {
    if (!storeName) return
    setLoading(true)
    setReport("")
    try {
      const res = await generateDouyinAiReport(storeName, startDate, endDate, config)
      setReport(res.report || res.content || JSON.stringify(res, null, 2))
    } catch (err: any) {
      setMessage(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-4">
      <h2 className="text-2xl font-bold">抖音 AI</h2>
      {message && (
        <div
          className={`text-sm p-3 rounded-md ${
            message.includes("成功") || message.includes("保存") || message.includes("连接") ? "bg-green-100 text-green-800" : "bg-destructive/10 text-destructive"
          }`}
        >
          {message}
        </div>
      )}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="config">AI 配置</TabsTrigger>
          <TabsTrigger value="report">生成报告</TabsTrigger>
        </TabsList>
        <TabsContent value="config">
          <Card>
            <CardHeader>
              <CardTitle>API 配置</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>API Key</Label>
                  <Input value={config.api_key || ""} onChange={(e) => updateConfig("api_key", e.target.value)} placeholder="sk-..." />
                </div>
                <div className="space-y-2">
                  <Label>Base URL</Label>
                  <Input value={config.base_url || ""} onChange={(e) => updateConfig("base_url", e.target.value)} placeholder="https://api.kimi.com/coding/v1" />
                </div>
                <div className="space-y-2">
                  <Label>模型</Label>
                  <Input value={config.model || ""} onChange={(e) => updateConfig("model", e.target.value)} placeholder="kimi-coding" />
                </div>
                <div className="space-y-2">
                  <Label>Temperature</Label>
                  <Input type="number" value={config.temperature || 1} onChange={(e) => updateConfig("temperature", parseFloat(e.target.value))} />
                </div>
              </div>
              <div className="flex gap-2">
                <Button variant="outline" onClick={handleTest}>
                  <TestTube className="h-4 w-4 mr-1" /> 测试连接
                </Button>
                <Button onClick={handleSave}>
                  <Save className="h-4 w-4 mr-1" /> 保存配置
                </Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
        <TabsContent value="report">
          <Card>
            <CardHeader>
              <CardTitle>生成 AI 报告</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 items-end">
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
                <Button onClick={handleReport} disabled={loading}>
                  <Sparkles className="h-4 w-4 mr-1" /> {loading ? "生成中..." : "生成报告"}
                </Button>
              </div>
              {report && (
                <div className="rounded-md border bg-muted p-4 whitespace-pre-wrap text-sm">
                  {report}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}

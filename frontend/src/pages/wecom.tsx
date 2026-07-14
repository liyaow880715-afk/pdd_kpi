import { useEffect, useState } from "react"
import { Send, Save } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { getWecomConfig, updateWecomConfig, sendWecomReport } from "@/api/client"

export function WecomPage() {
  const [config, setConfig] = useState<Record<string, any>>({})
  const [reportDate, setReportDate] = useState(new Date().toISOString().split("T")[0])
  const [message, setMessage] = useState("")

  useEffect(() => {
    getWecomConfig().then(setConfig)
  }, [])

  const updateConfig = (key: string, value: any) => {
    setConfig((prev) => ({ ...prev, [key]: value }))
  }

  const handleSave = async () => {
    try {
      await updateWecomConfig(config)
      setMessage("配置已保存")
    } catch (err: any) {
      setMessage(err.message)
    }
  }

  const handleSend = async () => {
    try {
      const res = await sendWecomReport(reportDate, config)
      setMessage(`发送结果：${res.status || JSON.stringify(res)}`)
    } catch (err: any) {
      setMessage(err.message)
    }
  }

  return (
    <div className="space-y-4">
      <h2 className="text-2xl font-bold">企业微信配置</h2>
      {message && (
        <div className={`text-sm p-3 rounded-md ${message.includes("成功") || message.includes("保存") || message.includes("发送") ? "bg-green-100 text-green-800" : "bg-destructive/10 text-destructive"}`}>
          {message}
        </div>
      )}
      <Card>
        <CardHeader>
          <CardTitle>机器人配置</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>Bot ID</Label>
              <Input value={config.bot_id || ""} onChange={(e) => updateConfig("bot_id", e.target.value)} />
            </div>
            <div className="space-y-2">
              <Label>Secret</Label>
              <Input value={config.secret || ""} onChange={(e) => updateConfig("secret", e.target.value)} />
            </div>
            <div className="space-y-2">
              <Label>Webhook Key</Label>
              <Input value={config.webhook_key || ""} onChange={(e) => updateConfig("webhook_key", e.target.value)} />
            </div>
            <div className="space-y-2">
              <Label>Chat ID</Label>
              <Input value={config.chat_id || ""} onChange={(e) => updateConfig("chat_id", e.target.value)} />
            </div>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" onClick={handleSave}>
              <Save className="h-4 w-4 mr-1" /> 保存配置
            </Button>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>发送日报</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-end gap-4">
            <div className="space-y-2 w-64">
              <Label>报告日期</Label>
              <Input type="date" value={reportDate} onChange={(e) => setReportDate(e.target.value)} />
            </div>
            <Button onClick={handleSend}>
              <Send className="h-4 w-4 mr-1" /> 发送日报
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

import { useState } from "react"
import { useNavigate, useSearchParams } from "react-router-dom"
import { Lock, ArrowLeft } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { changePassword, logout } from "@/api/auth"

export function ChangePasswordPage() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const [oldPassword, setOldPassword] = useState("")
  const [newPassword, setNewPassword] = useState("")
  const [confirmPassword, setConfirmPassword] = useState("")
  const [error, setError] = useState("")
  const [success, setSuccess] = useState("")
  const [loading, setLoading] = useState(false)
  const forced = searchParams.get("forced") === "1"

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError("")
    setSuccess("")
    if (newPassword.length < 8 || !/[a-zA-Z]/.test(newPassword) || !/\d/.test(newPassword)) {
      setError("新密码至少 8 位且同时包含字母和数字")
      return
    }
    if (newPassword !== confirmPassword) {
      setError("两次输入的新密码不一致")
      return
    }
    setLoading(true)
    try {
      await changePassword(oldPassword, newPassword)
      setSuccess("密码修改成功")
      setTimeout(() => {
        navigate("/", { replace: true })
      }, 800)
    } catch (err: any) {
      setError(err.message || "修改失败")
    } finally {
      setLoading(false)
    }
  }

  const handleBack = () => {
    if (forced) {
      // 强制改密流程不允许返回，只能退出登录
      logout()
    } else {
      navigate(-1)
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-2">
        <Button variant="ghost" size="icon" onClick={handleBack}>
          <ArrowLeft className="h-5 w-5" />
        </Button>
        <h1 className="text-2xl font-bold">修改密码</h1>
      </div>

      <Card className="max-w-md">
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <Lock className="h-4 w-4" />
            {forced ? "首次登录，请修改默认密码" : "修改登录密码"}
          </CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            {error && <div className="text-sm text-destructive">{error}</div>}
            {success && <div className="text-sm text-green-600">{success}</div>}
            {!forced && (
              <div className="space-y-2">
                <Label>原密码</Label>
                <Input
                  type="password"
                  value={oldPassword}
                  onChange={(e) => setOldPassword(e.target.value)}
                  required={!forced}
                />
              </div>
            )}
            <div className="space-y-2">
              <Label>新密码</Label>
              <Input
                type="password"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                required
              />
            </div>
            <div className="space-y-2">
              <Label>确认新密码</Label>
              <Input
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                required
              />
            </div>
            <Button type="submit" className="w-full" disabled={loading}>
              {loading ? "保存中..." : "保存修改"}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  )
}

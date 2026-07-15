import { useEffect, useState } from "react"
import { Plus, Trash2, Edit2, Check, X } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { getStores, createStore, renameStore, deleteStore, type Store } from "@/api/client"

export function StoresPage() {
  const [stores, setStores] = useState<Store[]>([])
  const [newName, setNewName] = useState("")
  const [newPlatform, setNewPlatform] = useState("pdd")
  const [editingId, setEditingId] = useState<string | null>(null)
  const [editName, setEditName] = useState("")
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState("")

  const fetchStores = async () => {
    try {
      setLoading(true)
      const data = await getStores()
      setStores(data)
    } catch (err: any) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchStores()
  }, [])

  const handleCreate = async () => {
    if (!newName.trim()) return
    try {
      await createStore(newName.trim(), newPlatform)
      setNewName("")
      fetchStores()
    } catch (err: any) {
      setError(err.message)
    }
  }

  const handleRename = async (id: string) => {
    if (!editName.trim()) return
    try {
      await renameStore(id, editName.trim())
      setEditingId(null)
      fetchStores()
    } catch (err: any) {
      setError(err.message)
    }
  }

  const handleDelete = async (id: string) => {
    if (!confirm("确定删除该店铺？")) return
    try {
      await deleteStore(id)
      fetchStores()
    } catch (err: any) {
      setError(err.message)
    }
  }

  return (
    <div className="space-y-4">
      <h2 className="text-2xl font-bold">店铺管理</h2>
      {error && <div className="text-sm text-destructive">{error}</div>}
      <Card>
        <CardHeader>
          <CardTitle>新增店铺</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex gap-2">
            <Input
              placeholder="店铺名称"
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleCreate()}
            />
            <select
              className="h-10 rounded-md border border-input bg-background px-3 text-sm"
              value={newPlatform}
              onChange={(e) => setNewPlatform(e.target.value)}
            >
              <option value="pdd">拼多多</option>
              <option value="douyin">抖音</option>
            </select>
            <Button onClick={handleCreate} disabled={loading}>
              <Plus className="h-4 w-4 mr-1" /> 新增
            </Button>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardContent className="pt-6">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>ID</TableHead>
                <TableHead>名称</TableHead>
                <TableHead>平台</TableHead>
                <TableHead>创建时间</TableHead>
                <TableHead className="text-right">操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {stores.map((store) => (
                <TableRow key={store.id}>
                  <TableCell className="font-mono text-xs">{store.id}</TableCell>
                  <TableCell>
                    {editingId === store.id ? (
                      <Input
                        value={editName}
                        onChange={(e) => setEditName(e.target.value)}
                        className="h-8"
                        autoFocus
                      />
                    ) : (
                      store.name
                    )}
                  </TableCell>
                  <TableCell>
                    <span className="rounded bg-muted px-2 py-1 text-xs text-muted-foreground">
                      {store.platform === "douyin" ? "抖音" : "拼多多"}
                    </span>
                  </TableCell>
                  <TableCell>{new Date(store.created_at).toLocaleString()}</TableCell>
                  <TableCell className="text-right">
                    {editingId === store.id ? (
                      <>
                        <Button variant="ghost" size="sm" onClick={() => handleRename(store.id)}>
                          <Check className="h-4 w-4" />
                        </Button>
                        <Button variant="ghost" size="sm" onClick={() => setEditingId(null)}>
                          <X className="h-4 w-4" />
                        </Button>
                      </>
                    ) : (
                      <>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => {
                            setEditingId(store.id)
                            setEditName(store.name)
                          }}
                        >
                          <Edit2 className="h-4 w-4" />
                        </Button>
                        <Button variant="ghost" size="sm" onClick={() => handleDelete(store.id)}>
                          <Trash2 className="h-4 w-4 text-destructive" />
                        </Button>
                      </>
                    )}
                  </TableCell>
                </TableRow>
              ))}
              {stores.length === 0 && (
                <TableRow>
                  <TableCell colSpan={5} className="text-center text-muted-foreground py-8">
                    暂无店铺
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

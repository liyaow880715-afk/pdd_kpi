import { useState } from "react"
import { BrowserRouter, Routes, Route, NavLink } from "react-router-dom"
import {
  LayoutDashboard,
  Store,
  Upload,
  BarChart3,
  ShoppingCart,
  Coins,
  Bot,
  MessageCircle,
  Menu,
  X,
  LogOut,
  Users,
  Settings,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { ThemeToggle } from "@/components/theme-toggle"
import { AuthGuard } from "@/components/auth-guard"
import { canAccessPage, getCurrentUser, isMaster, logout } from "@/api/auth"
import { LoginPage } from "@/pages/login"
import { DashboardPage } from "@/pages/dashboard"
import { StoresPage } from "@/pages/stores"
import { ImportPage } from "@/pages/import"
import { MetricsPage } from "@/pages/metrics"
import { OrdersPage } from "@/pages/orders"
import { CostsPage } from "@/pages/costs"
import { AiPage } from "@/pages/ai"
import { WecomPage } from "@/pages/wecom"
import { UsersPage } from "@/pages/users"
import { ChangePasswordPage } from "@/pages/change-password"

const allNavItems = [
  { id: "overview", to: "/", label: "总览", icon: LayoutDashboard },
  { id: "stores", to: "/stores", label: "店铺", icon: Store },
  { id: "import", to: "/import", label: "导入", icon: Upload },
  { id: "metrics", to: "/metrics", label: "指标", icon: BarChart3 },
  { id: "orders", to: "/orders", label: "订单", icon: ShoppingCart },
  { id: "costs", to: "/costs", label: "成本", icon: Coins },
  { id: "ai", to: "/ai", label: "AI", icon: Bot },
  { id: "wecom", to: "/wecom", label: "企微", icon: MessageCircle },
  { id: "users", to: "/users", label: "用户", icon: Users },
]

function Sidebar({ onClose }: { onClose?: () => void }) {
  const user = getCurrentUser()
  const showMaster = isMaster()
  const navItems = allNavItems.filter((item) =>
    showMaster ? true : canAccessPage(item.id)
  )

  return (
    <aside className="w-64 border-r bg-card min-h-screen p-4 flex flex-col">
      <div className="mb-8 px-2 flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold tracking-tight">PDD BI</h1>
          <p className="text-xs text-muted-foreground mt-1">推广数据看板</p>
        </div>
        {onClose && (
          <Button variant="ghost" size="icon" onClick={onClose} className="md:hidden">
            <X className="h-4 w-4" />
          </Button>
        )}
      </div>
      <nav className="space-y-1">
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            onClick={onClose}
            className={({ isActive }) =>
              `flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors ${
                isActive
                  ? "bg-primary text-primary-foreground"
                  : "text-muted-foreground hover:bg-muted hover:text-foreground"
              }`
            }
          >
            <item.icon className="h-4 w-4" />
            {item.label}
          </NavLink>
        ))}
      </nav>
      <div className="mt-auto pt-4 border-t space-y-2">
        <div className="px-2 text-sm">
          <div className="font-medium">{user?.username || "未知用户"}</div>
          <div className="text-xs text-muted-foreground">
            {user?.role === "master" ? "主账号" : "子账号"}
          </div>
        </div>
        <div className="flex items-center justify-between">
          <NavLink to="/change-password">
            <Button variant="ghost" size="sm" className="text-muted-foreground">
              <Settings className="mr-1 h-4 w-4" />
              改密码
            </Button>
          </NavLink>
          <ThemeToggle />
          <Button variant="ghost" size="icon" onClick={logout}>
            <LogOut className="h-4 w-4 text-muted-foreground" />
          </Button>
        </div>
      </div>
    </aside>
  )
}

function Layout() {
  const [sidebarOpen, setSidebarOpen] = useState(false)

  return (
    <div className="flex min-h-screen bg-background">
      <div className="hidden md:block">
        <Sidebar />
      </div>
      {sidebarOpen && (
        <div className="fixed inset-0 z-50 flex md:hidden">
          <div className="w-64">
            <Sidebar onClose={() => setSidebarOpen(false)} />
          </div>
          <div className="flex-1 bg-black/50" onClick={() => setSidebarOpen(false)} />
        </div>
      )}
      <main className="flex-1 flex flex-col min-h-screen overflow-hidden">
        <header className="md:hidden border-b p-4 flex items-center justify-between bg-card">
          <span className="font-bold">PDD BI</span>
          <Button variant="ghost" size="icon" onClick={() => setSidebarOpen(true)}>
            <Menu className="h-5 w-5" />
          </Button>
        </header>
        <div className="flex-1 p-4 md:p-6 overflow-auto">
          <Routes>
            <Route path="/" element={<DashboardPage />} />
            <Route path="/stores" element={<StoresPage />} />
            <Route path="/import" element={<ImportPage />} />
            <Route path="/metrics" element={<MetricsPage />} />
            <Route path="/orders" element={<OrdersPage />} />
            <Route path="/costs" element={<CostsPage />} />
            <Route path="/ai" element={<AiPage />} />
            <Route path="/wecom" element={<WecomPage />} />
            <Route path="/users" element={<UsersPage />} />
            <Route path="/change-password" element={<ChangePasswordPage />} />
          </Routes>
        </div>
      </main>
    </div>
  )
}

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route
          path="/*"
          element={
            <AuthGuard>
              <Layout />
            </AuthGuard>
          }
        />
      </Routes>
    </BrowserRouter>
  )
}

export default App

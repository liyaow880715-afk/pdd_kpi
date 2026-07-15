import { useEffect, useState } from "react"
import { BrowserRouter, Routes, Route, NavLink, useLocation, useNavigate } from "react-router-dom"
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
import { DouyinDashboardPage } from "@/pages/douyin-dashboard"
import { DouyinImportPage } from "@/pages/douyin-import"
import { DouyinMetricsPage } from "@/pages/douyin-metrics"
import { DouyinOrdersPage } from "@/pages/douyin-orders"
import { DouyinCostsPage } from "@/pages/douyin-costs"
import { DouyinAiPage } from "@/pages/douyin-ai"
import { DouyinWecomPage } from "@/pages/douyin-wecom"
import { ChangePasswordPage } from "@/pages/change-password"

type Platform = "pdd" | "douyin" | "tmall"

interface NavItem {
  id: string
  to: string
  label: string
  icon: React.ComponentType<{ className?: string }>
}

const pddNavItems: NavItem[] = [
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

const douyinNavItems: NavItem[] = [
  { id: "douyin", to: "/douyin", label: "抖音总览", icon: LayoutDashboard },
  { id: "douyin", to: "/douyin/import", label: "抖音导入", icon: Upload },
  { id: "douyin", to: "/douyin/metrics", label: "抖音指标", icon: BarChart3 },
  { id: "douyin", to: "/douyin/orders", label: "抖音订单", icon: ShoppingCart },
  { id: "douyin", to: "/douyin/costs", label: "抖音成本", icon: Coins },
  { id: "douyin", to: "/douyin/ai", label: "抖音 AI", icon: Bot },
  { id: "douyin", to: "/douyin/wecom", label: "抖音企微", icon: MessageCircle },
  { id: "users", to: "/users", label: "用户", icon: Users },
]

const platformTabs: { key: Platform; label: string; defaultTo: string }[] = [
  { key: "pdd", label: "拼多多", defaultTo: "/" },
  { key: "douyin", label: "抖音", defaultTo: "/douyin" },
  { key: "tmall", label: "天猫", defaultTo: "/tmall" },
]

function detectPlatform(pathname: string): Platform {
  if (pathname.startsWith("/douyin")) return "douyin"
  if (pathname.startsWith("/tmall")) return "tmall"
  return "pdd"
}

function PlatformTabs({
  platform,
  onChange,
}: {
  platform: Platform
  onChange: (p: Platform) => void
}) {
  return (
    <div className="px-2 pb-3">
      <div className="flex rounded-lg bg-muted p-1 gap-1">
        {platformTabs.map((tab) => {
          const active = platform === tab.key
          const disabled = tab.key === "tmall"
          return (
            <button
              key={tab.key}
              disabled={disabled}
              onClick={() => onChange(tab.key)}
              className={`flex-1 rounded-md px-2 py-1.5 text-xs font-medium transition-colors ${
                disabled
                  ? "text-muted-foreground/50 cursor-not-allowed"
                  : active
                  ? "bg-background text-foreground shadow-sm"
                  : "text-muted-foreground hover:text-foreground hover:bg-muted/50"
              }`}
            >
              {tab.label}
            </button>
          )
        })}
      </div>
    </div>
  )
}

function Sidebar({
  platform,
  onPlatformChange,
  onClose,
}: {
  platform: Platform
  onPlatformChange: (p: Platform) => void
  onClose?: () => void
}) {
  const user = getCurrentUser()
  const showMaster = isMaster()
  const navItems = platform === "douyin" ? douyinNavItems : pddNavItems
  const visibleItems = navItems.filter((item) => (showMaster ? true : canAccessPage(item.id)))

  return (
    <aside className="w-64 border-r bg-card min-h-screen p-4 flex flex-col">
      <div className="mb-4 px-2 flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold tracking-tight">推广数据看板</h1>
          <p className="text-xs text-muted-foreground mt-1">多平台 BI</p>
        </div>
        {onClose && (
          <Button variant="ghost" size="icon" onClick={onClose} className="md:hidden">
            <X className="h-4 w-4" />
          </Button>
        )}
      </div>

      <PlatformTabs platform={platform} onChange={onPlatformChange} />

      <nav className="space-y-1">
        {visibleItems.map((item) => (
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

function TmallPlaceholder() {
  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] text-muted-foreground">
      <h2 className="text-2xl font-bold mb-2">天猫</h2>
      <p>天猫板块暂未上线，敬请期待</p>
    </div>
  )
}

function Layout() {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const location = useLocation()
  const navigate = useNavigate()
  const [platform, setPlatform] = useState<Platform>(detectPlatform(location.pathname))

  useEffect(() => {
    setPlatform(detectPlatform(location.pathname))
  }, [location.pathname])

  const handlePlatformChange = (p: Platform) => {
    const tab = platformTabs.find((t) => t.key === p)
    if (tab) {
      setPlatform(p)
      navigate(tab.defaultTo)
      setSidebarOpen(false)
    }
  }

  return (
    <div className="flex min-h-screen bg-background">
      <div className="hidden md:block">
        <Sidebar platform={platform} onPlatformChange={handlePlatformChange} />
      </div>
      {sidebarOpen && (
        <div className="fixed inset-0 z-50 flex md:hidden">
          <div className="w-64">
            <Sidebar
              platform={platform}
              onPlatformChange={handlePlatformChange}
              onClose={() => setSidebarOpen(false)}
            />
          </div>
          <div className="flex-1 bg-black/50" onClick={() => setSidebarOpen(false)} />
        </div>
      )}
      <main className="flex-1 flex flex-col min-h-screen overflow-hidden">
        <header className="md:hidden border-b p-4 flex items-center justify-between bg-card">
          <span className="font-bold">{platformTabs.find((t) => t.key === platform)?.label}</span>
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
            <Route path="/douyin" element={<DouyinDashboardPage />} />
            <Route path="/douyin/import" element={<DouyinImportPage />} />
            <Route path="/douyin/metrics" element={<DouyinMetricsPage />} />
            <Route path="/douyin/orders" element={<DouyinOrdersPage />} />
            <Route path="/douyin/costs" element={<DouyinCostsPage />} />
            <Route path="/douyin/ai" element={<DouyinAiPage />} />
            <Route path="/douyin/wecom" element={<DouyinWecomPage />} />
            <Route path="/tmall" element={<TmallPlaceholder />} />
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

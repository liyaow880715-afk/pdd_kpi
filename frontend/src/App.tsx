import { BrowserRouter, Routes, Route, NavLink } from "react-router-dom"
import { LayoutDashboard, Store, Upload, BarChart3, ShoppingCart, Coins, Bot, MessageCircle } from "lucide-react"
import { StoresPage } from "@/pages/stores"
import { ImportPage } from "@/pages/import"
import { MetricsPage } from "@/pages/metrics"
import { OrdersPage } from "@/pages/orders"
import { CostsPage } from "@/pages/costs"
import { AiPage } from "@/pages/ai"
import { WecomPage } from "@/pages/wecom"

const navItems = [
  { to: "/", label: "总览", icon: LayoutDashboard },
  { to: "/stores", label: "店铺", icon: Store },
  { to: "/import", label: "导入", icon: Upload },
  { to: "/metrics", label: "指标", icon: BarChart3 },
  { to: "/orders", label: "订单", icon: ShoppingCart },
  { to: "/costs", label: "成本", icon: Coins },
  { to: "/ai", label: "AI", icon: Bot },
  { to: "/wecom", label: "企微", icon: MessageCircle },
]

function Sidebar() {
  return (
    <aside className="w-64 border-r bg-card min-h-screen p-4 flex flex-col">
      <div className="mb-8 px-2">
        <h1 className="text-xl font-bold tracking-tight">PDD BI Dashboard</h1>
        <p className="text-xs text-muted-foreground mt-1">拼多多推广数据看板</p>
      </div>
      <nav className="space-y-1">
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
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
    </aside>
  )
}

function Dashboard() {
  return (
    <div className="space-y-4">
      <h2 className="text-2xl font-bold">总览</h2>
      <p className="text-muted-foreground">欢迎使用 PDD BI Dashboard。请从左侧菜单选择功能。</p>
    </div>
  )
}

function App() {
  return (
    <BrowserRouter>
      <div className="flex min-h-screen bg-background">
        <Sidebar />
        <main className="flex-1 p-6 overflow-auto">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/stores" element={<StoresPage />} />
            <Route path="/import" element={<ImportPage />} />
            <Route path="/metrics" element={<MetricsPage />} />
            <Route path="/orders" element={<OrdersPage />} />
            <Route path="/costs" element={<CostsPage />} />
            <Route path="/ai" element={<AiPage />} />
            <Route path="/wecom" element={<WecomPage />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  )
}

export default App

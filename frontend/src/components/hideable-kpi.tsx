import { type KeyboardEvent } from "react"
import { Eye } from "lucide-react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"

interface KpiItem {
  key: string
  label: string
}

function formatNumber(value: any, digits = 2) {
  if (value === null || value === undefined || Number.isNaN(value)) return "-"
  if (typeof value === "number") {
    return value.toLocaleString("zh-CN", { maximumFractionDigits: digits })
  }
  return value
}

export function HideableKpiCard({
  label,
  value,
  unit = "",
  onHide,
}: {
  label: string
  value: any
  unit?: string
  onHide: () => void
}) {
  const handleKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault()
      onHide()
    }
  }

  return (
    <Card
      role="button"
      tabIndex={0}
      aria-label={`隐藏${label}`}
      onClick={onHide}
      onKeyDown={handleKeyDown}
      className="cursor-pointer transition-colors hover:bg-muted/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
      title="点击隐藏"
    >
      <CardHeader className="pb-2">
        <CardDescription className="text-xs">{label}</CardDescription>
      </CardHeader>
      <CardContent>
        <CardTitle className="text-xl">
          {formatNumber(value)} {unit && <span className="text-sm font-normal text-muted-foreground">{unit}</span>}
        </CardTitle>
      </CardContent>
    </Card>
  )
}

export function HiddenKpiList({
  items,
  onRestore,
}: {
  items: KpiItem[]
  onRestore: (key: string) => void
}) {
  if (items.length === 0) return null

  return (
    <div className="flex flex-wrap items-center gap-2 pt-2 border-t">
      <span className="text-xs text-muted-foreground">已隐藏：</span>
      {items.map((item) => (
        <button
          key={item.key}
          type="button"
          onClick={() => onRestore(item.key)}
          className="inline-flex items-center gap-1 text-xs px-2 py-1 rounded-full bg-muted hover:bg-muted/80"
          title="点击显示"
        >
          <Eye className="h-3 w-3" />
          {item.label}
        </button>
      ))}
    </div>
  )
}

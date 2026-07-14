import { useEffect } from "react"
import { X } from "lucide-react"
import { Button } from "@/components/ui/button"

interface ErrorToastProps {
  message: string
  onClose: () => void
}

export function ErrorToast({ message, onClose }: ErrorToastProps) {
  useEffect(() => {
    const timer = setTimeout(onClose, 5000)
    return () => clearTimeout(timer)
  }, [onClose])

  if (!message) return null

  return (
    <div className="fixed top-4 right-4 z-50 max-w-sm animate-in slide-in-from-top-2 fade-in duration-200">
      <div className="rounded-lg border bg-destructive text-destructive-foreground shadow-lg p-4 flex items-start gap-3">
        <div className="flex-1 text-sm break-words">{message}</div>
        <Button variant="ghost" size="icon" className="h-6 w-6 shrink-0 text-destructive-foreground hover:bg-destructive/80" onClick={onClose}>
          <X className="h-4 w-4" />
        </Button>
      </div>
    </div>
  )
}

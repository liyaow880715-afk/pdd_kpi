import { useState } from "react"

export function useHiddenKpis(storageKey: string) {
  const [hiddenKpis, setHiddenKpis] = useState<Set<string>>(() => {
    try {
      return new Set(JSON.parse(localStorage.getItem(storageKey) || "[]"))
    } catch {
      return new Set()
    }
  })

  const toggleKpi = (key: string) => {
    setHiddenKpis((previous) => {
      const next = new Set(previous)
      if (next.has(key)) {
        next.delete(key)
      } else {
        next.add(key)
      }
      try {
        localStorage.setItem(storageKey, JSON.stringify(Array.from(next)))
      } catch {
        // Keep the interaction usable when browser storage is unavailable.
      }
      return next
    })
  }

  return { hiddenKpis, toggleKpi }
}

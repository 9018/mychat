// ── localStorage Hook ─────────────────────────────────────────
import { useState, useCallback } from 'react'

export function useLocalStorage<T>(key: string, defaultValue: T): [T, (val: T) => void] {
  const [value, setValue] = useState<T>(() => {
    try {
      const saved = localStorage.getItem(key)
      return saved ? (JSON.parse(saved) as T) : defaultValue
    } catch {
      return defaultValue
    }
  })

  const setStoredValue = useCallback((val: T) => {
    setValue(val)
    try {
      localStorage.setItem(key, JSON.stringify(val))
    } catch { /* quota exceeded, ignore */ }
  }, [key])

  return [value, setStoredValue]
}

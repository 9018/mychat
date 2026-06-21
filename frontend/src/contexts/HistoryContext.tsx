// ── 历史记录上下文 ────────────────────────────────────────────
import { createContext, useContext, useState, useCallback, useEffect, type ReactNode } from 'react'
import type { HistoryItem } from '@/api/types'
import * as HistoryApi from '@/api/history'

interface HistoryContextType {
  items: HistoryItem[]
  refresh: () => Promise<void>
  addItem: (item: HistoryItem) => Promise<void>
  removeItem: (id: string) => Promise<void>
}

const HistoryContext = createContext<HistoryContextType | null>(null)

export function HistoryProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<HistoryItem[]>([])

  const refresh = useCallback(async () => {
    try {
      const data = await HistoryApi.loadHistory()
      if (Array.isArray(data)) setItems(data)
    } catch (err) {
      console.warn('加载历史记录失败:', err)
    }
  }, [])

  const addItem = useCallback(async (item: HistoryItem) => {
    try {
      const result = await HistoryApi.saveHistory(item)
      if (result.success && result.item) {
        setItems(prev => [result.item, ...prev].slice(0, 100))
      }
    } catch (err) {
      console.error('保存历史记录失败:', err)
    }
  }, [])

  const removeItem = useCallback(async (id: string) => {
    try {
      await HistoryApi.deleteHistory(id)
      setItems(prev => prev.filter(h => h.id !== id))
    } catch (err) {
      console.error('删除历史记录失败:', err)
    }
  }, [])

  useEffect(() => { refresh() }, [refresh])

  return (
    <HistoryContext.Provider value={{ items, refresh, addItem, removeItem }}>
      {children}
    </HistoryContext.Provider>
  )
}

export function useHistory() {
  const ctx = useContext(HistoryContext)
  if (!ctx) throw new Error('useHistory must be within HistoryProvider')
  return ctx
}

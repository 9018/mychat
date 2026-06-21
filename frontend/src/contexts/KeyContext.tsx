// ── API Key 上下文 ────────────────────────────────────────────
import { createContext, useContext, useState, useCallback, useEffect, type ReactNode } from 'react'
import { loadApiKeyFromServer, saveApiKeyToServer } from '@/api/key'

interface KeyContextType {
  apiKey: string
  isReady: boolean
  setApiKey: (key: string) => void
  save: (key: string) => Promise<void>
}

const KeyContext = createContext<KeyContextType | null>(null)

export function KeyProvider({ children }: { children: ReactNode }) {
  const [apiKey, setApiKeyState] = useState('')
  const [isReady, setIsReady] = useState(false)

  const setApiKey = useCallback((key: string) => {
    setApiKeyState(key)
  }, [])

  const save = useCallback(async (key: string) => {
    setApiKeyState(key)
    try {
      await saveApiKeyToServer(key)
    } catch (err) {
      console.error('保存 API Key 到服务器失败:', err)
    }
  }, [])

  useEffect(() => {
    ;(async () => {
      try {
        const key = await loadApiKeyFromServer()
        if (key) {
          setApiKeyState(key)
          setIsReady(true)
          return
        }
      } catch { /* 服务器无 key */ }
      setIsReady(false)
    })()
  }, [])

  return (
    <KeyContext.Provider value={{ apiKey, isReady, setApiKey, save }}>
      {children}
    </KeyContext.Provider>
  )
}

export function useKey() {
  const ctx = useContext(KeyContext)
  if (!ctx) throw new Error('useKey must be within KeyProvider')
  return ctx
}

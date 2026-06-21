// ── 应用配置上下文 ────────────────────────────────────────────
import { createContext, useContext, useState, useCallback, useEffect, type ReactNode } from 'react'
import type { AppConfig } from '@/api/types'
import { loadConfig } from '@/api/config'

const DEFAULT_MODELS = [
  { id: 'agnes-video-v2.0', types: ['video'] as Array<'chat' | 'image' | 'video' | 'other'>, enabled: true },
  { id: 'agnes-image-2.1-flash', types: ['image'] as Array<'chat' | 'image' | 'video' | 'other'>, enabled: true },
]

const DEFAULT_CONFIG: AppConfig = {
  baseUrl: 'http://www.9017i.cc:58901/v1',
  videoModel: 'agnes-video-v2.0',
  imageModel: 'agnes-image-2.1-flash',
  chatModel: '',
  modelList: [...DEFAULT_MODELS],
  modelListUpdatedAt: '',
}

interface ConfigContextType {
  config: AppConfig
  setConfig: (c: AppConfig) => void
  refresh: () => Promise<void>
}

const ConfigContext = createContext<ConfigContextType | null>(null)

export function ConfigProvider({ children }: { children: ReactNode }) {
  const [config, setConfig] = useState<AppConfig>(DEFAULT_CONFIG)

  const refresh = useCallback(async () => {
    try {
      const data = await loadConfig()
      if (data && typeof data === 'object' && Object.keys(data).length > 0) {
        setConfig(prev => {
          const merged = { ...prev, ...data }
          if (!Array.isArray(merged.modelList) || merged.modelList.length === 0) {
            merged.modelList = [...DEFAULT_MODELS]
          }
          merged.modelList.forEach(m => {
            if ((m as any).type && !m.types) { m.types = [(m as any).type] }
            if (!m.types || m.types.length === 0) { m.types = ['other'] }
            delete (m as any).type
          })
          return merged
        })
      }
    } catch (err) {
      console.warn('加载配置失败:', err)
    }
  }, [])

  useEffect(() => { refresh() }, [refresh])

  return (
    <ConfigContext.Provider value={{ config, setConfig, refresh }}>
      {children}
    </ConfigContext.Provider>
  )
}

export function useConfig() {
  const ctx = useContext(ConfigContext)
  if (!ctx) throw new Error('useConfig must be within ConfigProvider')
  return ctx
}

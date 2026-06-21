// ── 外观设置上下文 ────────────────────────────────────────────
import { createContext, useContext, useState, useCallback, useEffect, type ReactNode } from 'react'
import type { TweaksState } from '@/api/types'

const ACCENTS: Record<string, number> = {
  violet: 292, indigo: 270, cyan: 210,
  emerald: 158, amber: 72, rose: 18,
}

const STORAGE_KEY = 'agnes_tweaks_settings'

const DEFAULT_TWEAKS: TweaksState = {
  theme: 'dark',
  accent: 'violet',
  density: 'regular',
  uiScale: 100,
}

interface TweaksContextType {
  tweaks: TweaksState
  accentH: number
  setTweaks: (t: Partial<TweaksState>) => void
  toggleTheme: () => void
}

const TweaksContext = createContext<TweaksContextType | null>(null)

export function TweaksProvider({ children }: { children: ReactNode }) {
  const [tweaks, setTweaksState] = useState<TweaksState>(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY)
      if (saved) return { ...DEFAULT_TWEAKS, ...JSON.parse(saved) }
    } catch { /* ignore */ }
    return DEFAULT_TWEAKS
  })

  const accentH = ACCENTS[tweaks.accent] ?? 292

  const setTweaks = useCallback((partial: Partial<TweaksState>) => {
    setTweaksState(prev => {
      const next = { ...prev, ...partial }
      localStorage.setItem(STORAGE_KEY, JSON.stringify(next))
      return next
    })
  }, [])

  const toggleTheme = useCallback(() => {
    setTweaks({ theme: tweaks.theme === 'dark' ? 'light' : 'dark' })
  }, [tweaks.theme, setTweaks])

  // 同步 CSS 变量
  useEffect(() => {
    const root = document.documentElement
    root.setAttribute('data-theme', tweaks.theme)
    root.style.setProperty('--accent-h', String(accentH))

    const densityVal = tweaks.density === 'compact' ? 0.82 : tweaks.density === 'comfy' ? 1.18 : 1
    root.style.setProperty('--density', String(densityVal))

    document.body.style.zoom = tweaks.uiScale === 100 ? '' : String(tweaks.uiScale / 100)
  }, [tweaks, accentH])

  return (
    <TweaksContext.Provider value={{ tweaks, accentH, setTweaks, toggleTheme }}>
      {children}
    </TweaksContext.Provider>
  )
}

export function useTweaks() {
  const ctx = useContext(TweaksContext)
  if (!ctx) throw new Error('useTweaks must be within TweaksProvider')
  return ctx
}

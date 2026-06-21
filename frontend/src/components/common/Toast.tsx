// ── Toast 提示 ─────────────────────────────────────────────────
import { useState, useCallback, useRef, useEffect } from 'react'

let globalShowToast: ((msg: string, type?: 'success' | 'error' | 'warning') => void) | null = null

export function ToastContainer() {
  const [toasts, setToasts] = useState<Array<{ id: number; msg: string; type: string }>>([])
  const idRef = useRef(0)

  const show = useCallback((msg: string, type: 'success' | 'error' | 'warning' = 'success') => {
    const id = ++idRef.current
    setToasts(prev => [...prev, { id, msg, type }])
    setTimeout(() => {
      setToasts(prev => prev.filter(t => t.id !== id))
    }, 3000)
  }, [])

  useEffect(() => {
    globalShowToast = show
    return () => { globalShowToast = null }
  }, [show])

  if (toasts.length === 0) return null

  return (
    <div style={{ position: 'fixed', top: 16, right: 16, zIndex: 2147483647, display: 'flex', flexDirection: 'column', gap: 8 }}>
      {toasts.map(t => (
        <div key={t.id} style={{
          background: t.type === 'error' ? 'var(--error)' : t.type === 'warning' ? 'var(--warning)' : 'var(--success)',
          color: '#fff', padding: '8px 16px', borderRadius: 'var(--r)', fontSize: 13,
          boxShadow: 'var(--shadow-md)', display: 'flex', alignItems: 'center', gap: 8,
          animation: 'fadeIn 0.2s ease-out',
        }}>
          {t.msg}
        </div>
      ))}
    </div>
  )
}

export function showToast(msg: string, type: 'success' | 'error' | 'warning' = 'success') {
  globalShowToast?.(msg, type)
}

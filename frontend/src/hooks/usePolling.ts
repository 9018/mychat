// ── 视频任务轮询 Hook ──────────────────────────────────────────
import { useState, useRef, useCallback } from 'react'
import { apiProxyGet } from '@/api/client'
import type { VideoTaskResult } from '@/api/types'

interface PollingConfig {
  interval?: number
  maxRetries?: number
  onComplete?: (data: VideoTaskResult) => void
  onError?: (error: string) => void
  onProgress?: (status: string, progress: number | null) => void
}

const POLL_INTERVAL = 5000

export function usePolling(apiKey: string) {
  const [isPolling, setIsPolling] = useState(false)
  const [status, setStatus] = useState<string>('')
  const [progress, setProgress] = useState<number | null>(null)
  const [error, setError] = useState<string>('')
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const activeRef = useRef(false)

  const stop = useCallback(() => {
    activeRef.current = false
    if (timerRef.current) {
      clearTimeout(timerRef.current)
      timerRef.current = null
    }
    setIsPolling(false)
  }, [])

  const start = useCallback(async (
    videoId: string | null,
    taskId: string | null,
    model: string,
    config: PollingConfig = {}
  ) => {
    stop()
    activeRef.current = true
    setIsPolling(true)
    setError('')

    const maxRetries = config.maxRetries ?? 10
    let retryCount = 0

    const poll = async () => {
      if (!activeRef.current) return

      try {
        let url: string
        if (videoId) {
          url = `/agnesapi?video_id=${videoId}&model_name=${model}&_t=${Date.now()}`
        } else if (taskId) {
          url = `/v1/videos/${taskId}?_t=${Date.now()}`
        } else {
          throw new Error('没有有效的任务 ID')
        }

        const res = await apiProxyGet(url, apiKey)
        const data: VideoTaskResult & { status?: string; error?: { message?: string } } = await res.json()

        if (!res.ok && !(data as any).status) {
          throw new Error((data as any).error?.message || (data as any).message || `HTTP ${res.status}`)
        }

        if (data.status === 'completed') {
          retryCount = 0
          setStatus('completed')
          setProgress(100)
          setIsPolling(false)
          config.onComplete?.(data)
          return
        }

        if (data.status === 'failed') {
          setStatus('failed')
          setIsPolling(false)
          const reason = data.error?.message || '未知原因'
          setError(`视频生成失败: ${reason}`)
          config.onError?.(reason)
          return
        }

        // 更新进度
        setStatus(data.status || 'in_progress')
        if (data.progress != null && !isNaN(data.progress)) {
          const pct = Math.round(data.progress > 1 ? data.progress : data.progress * 100)
          setProgress(pct)
        }
        retryCount = 0
        config.onProgress?.(data.status || 'in_progress', data.progress ?? null)

      } catch (err: any) {
        const msg = err.message || String(err)
        if (msg.toLowerCase().includes('401') || msg.toLowerCase().includes('unauthorized') || msg.toLowerCase().includes('api key')) {
          setError(`认证失败: ${msg}。请在管理页检查 API Key。`)
          setIsPolling(false)
          config.onError?.(msg)
          return
        }

        retryCount++
        if (retryCount >= maxRetries) {
          setError(`请求失败: ${msg}`)
          setIsPolling(false)
          config.onError?.(msg)
          return
        }
      }

      // 安排下一次轮询
      if (activeRef.current) {
        timerRef.current = setTimeout(poll, config.interval ?? POLL_INTERVAL)
      }
    }

    poll()
  }, [apiKey, stop])

  return { isPolling, status, progress, error, start, stop, setError }
}

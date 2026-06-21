// ── SSE 聊天 Hook ────────────────────────────────────────────
import { useState, useRef, useCallback } from 'react'
import type { ChatMessage, ChatSettings } from '@/api/types'

export type ChatStatus = 'idle' | 'connecting' | 'receiving' | 'streaming' | 'done' | 'error'

export function useSSEChat(apiKey: string) {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [isStreaming, setIsStreaming] = useState(false)
  const [streamContent, setStreamContent] = useState('')
  const [metrics, setMetrics] = useState({ ttfb: 0, ttft: 0, total: 0 })
  const [status, setStatus] = useState<ChatStatus>('idle')
  const abortRef = useRef<AbortController | null>(null)
  const tStartRef = useRef(0)

  const restoreMessages = useCallback((msgs: ChatMessage[]) => {
    setMessages(msgs)
  }, [])

  const send = useCallback(async (model: string, settings: ChatSettings, content: string | ChatMessage['content']) => {
    if (!apiKey || !model) return

    const userMessage: ChatMessage = {
      role: 'user',
      content: content,
    }

    setStatus('connecting')
    setMessages(prev => [...prev, userMessage])
    setIsStreaming(true)
    setStreamContent('')

    tStartRef.current = performance.now()
    let ttft = 0

    const systemMessage = settings.systemPrompt
      ? { role: 'system', content: settings.systemPrompt }
      : null

    // Build API messages: include ALL previous messages for context
    const apiMessages = [
      ...(systemMessage ? [systemMessage] : []),
      ...messages,  // <-- 关键修复：带上历史上下文
      userMessage,
    ].map(m => ({
      role: m.role,
      content: m.content,
    }))

    const body: Record<string, unknown> = {
      model,
      messages: apiMessages,
      stream: settings.stream ?? true,
    }
    if (settings.temperature !== 1.0) body.temperature = settings.temperature
    if (settings.topP !== 1.0) body.top_p = settings.topP
    if (settings.maxTokens !== '' && settings.maxTokens != null) body.max_tokens = settings.maxTokens
    if (settings.enableThinking) {
      body.chat_template_kwargs = { enable_thinking: true }
      if (settings.thinkingBudget > 0) {
        body.thinking = { type: 'enabled', budget_tokens: settings.thinkingBudget }
      }
    }

    abortRef.current = new AbortController()

    try {
      const res = await fetch('/v1/chat/completions', {
        method: 'POST',
        headers: {
          'X-Api-Key': apiKey,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(body),
        signal: abortRef.current.signal,
      })

      const ttfbMs = performance.now() - tStartRef.current
      setMetrics(prev => ({ ...prev, ttfb: Math.round(ttfbMs) }))
      setStatus('receiving')

      if (!res.ok) {
        const data = await res.json()
        throw new Error(data.error?.message || `HTTP ${res.status}`)
      }

      const contentType = res.headers.get('content-type') || ''
      let fullContent = ''

      if (contentType.includes('text/event-stream')) {
        const reader = res.body?.getReader()
        if (!reader) throw new Error('无法读取流')

        const decoder = new TextDecoder()
        let buffer = ''

        while (true) {
          const { done, value } = await reader.read()
          if (done) break

          buffer += decoder.decode(value, { stream: true })
          const lines = buffer.split('\n')
          buffer = lines.pop() || ''

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              const data = line.slice(6).trim()
              if (data === '[DONE]') continue
              try {
                const parsed = JSON.parse(data)
                const delta = parsed.choices?.[0]?.delta?.content
                if (delta) {
                  fullContent += delta
                  if (!ttft) {
                    ttft = performance.now() - tStartRef.current
                    setMetrics(prev => ({ ...prev, ttft: Math.round(ttft) }))
                  }
                  setStreamContent(fullContent)
                  if (ttft) setStatus('streaming')
                }
              } catch { /* skip */ }
            }
          }
        }
      } else {
        const data = await res.json()
        fullContent = data.choices?.[0]?.message?.content || data.content || ''
        if (!ttft) {
          ttft = performance.now() - tStartRef.current
        }
        setStatus('streaming')
        setStreamContent(fullContent)
      }

      const totalMs = Math.round(performance.now() - tStartRef.current)
      setMetrics({ ttfb: Math.round(ttfbMs), ttft: Math.round(ttft), total: totalMs })

      const metricStr = `⚡ TTFB ${Math.round(ttfbMs)}ms · TTFT ${Math.round(ttft)}ms · 总耗时 ${totalMs}ms`
      const assistantMsg: ChatMessage = {
        role: 'assistant',
        content: fullContent,
        metric: metricStr,
      }
      setStatus('done')
      setMessages(prev => [...prev, assistantMsg])
      setStreamContent('')

    } catch (err: any) {
      if (err.name === 'AbortError') { setStatus('idle'); return }
      setStatus('error')
      setStreamContent(`[错误] ${err.message}`)
    } finally {
      const s = status
      setTimeout(() => { if (s === 'done' || s === 'error') setStatus('idle') }, 3000)
      setIsStreaming(false)
      abortRef.current = null
    }
  }, [apiKey, messages])

  const abort = useCallback(() => {
    abortRef.current?.abort()
  }, [])

  const clear = useCallback(() => {
    abort()
    setStatus('idle')
    setMessages([])
    setStreamContent('')
    setMetrics({ ttfb: 0, ttft: 0, total: 0 })
  }, [abort])

  return { messages, isStreaming, streamContent, metrics, status, send, abort, clear, restoreMessages }
}

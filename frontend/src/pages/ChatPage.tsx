// ── 聊天页（SSE 流式对话） ───────────────────────────────────
import { useState, useRef, useEffect } from 'react'
import { useKey } from '@/contexts/KeyContext'
import { useConfig } from '@/contexts/ConfigContext'
import { ModelSelect } from '@/components/common/ModelSelect'
import { Spinner } from '@/components/common/Spinner'
import { showToast } from '@/components/common/Toast'
import { useSSEChat } from '@/hooks/useSSEChat'
import { loadChatSettings, saveChatSettings, loadChatMessages, saveChatMessages, clearChatMessages } from '@/api/chat'
import type { ChatSettings, UploadedFile } from '@/api/types'
import type { ChatStatus } from '@/hooks/useSSEChat'

const DEFAULT_SETTINGS: ChatSettings = {
  systemPrompt: '',
  temperature: 1.0,
  topP: 1.0,
  maxTokens: '',
  stream: true,
  enableThinking: false,
  thinkingBudget: 2048,
}

const FILE_MAX_SIZE = 5 * 1024 * 1024 // 5MB

function getFileCategory(type: string): string {
  if (!type) return 'other'
  if (type.startsWith('image/')) return 'image'
  if (type.startsWith('audio/')) return 'audio'
  if (type.startsWith('video/')) return 'video'
  return 'other'
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

// 从视频 data URL 提取多个关键帧（均匀分布）
// 从视频 data URL 提取关键帧（数量根据时长自适应）
async function extractVideoKeyframes(dataUrl: string): Promise<string[]> {
  return new Promise((resolve) => {
    const video = document.createElement('video')
    video.muted = true
    video.crossOrigin = 'anonymous'
    video.preload = 'auto'
    const frames: string[] = []
    const timeout = setTimeout(() => { video.remove(); resolve(frames) }, 30000)
    let seeking = false

    video.onseeked = () => {
      if (!seeking) return
      try {
        const canvas = document.createElement('canvas')
        const maxDim = 512
        let w = video.videoWidth || 512, h = video.videoHeight || 512
        if (w > maxDim || h > maxDim) { if (w > h) { h = h * maxDim / w; w = maxDim } else { w = w * maxDim / h; h = maxDim } }
        canvas.width = w; canvas.height = h
        const ctx = canvas.getContext('2d')
        if (ctx) { ctx.drawImage(video, 0, 0, w, h); frames.push(canvas.toDataURL('image/jpeg', 0.7)) }
      } catch {}
      seeking = false
      // 触发下一个 seek
      nextSeek()
    }

    let seekIdx = 0
    const seekTimes: number[] = []

    function nextSeek() {
      if (seekIdx < seekTimes.length) {
        seeking = true
        video.currentTime = seekTimes[seekIdx++]
      } else {
        clearTimeout(timeout)
        video.remove()
        resolve(frames)
      }
    }

    video.onloadedmetadata = () => {
      const dur = video.duration || 0
      // 根据时长决定帧数：<3s→3帧, 3-15s→5帧, 15-60s→8帧, >60s→每10s一帧(最多15)
      let count = 3
      if (dur > 60) count = Math.min(15, Math.max(5, Math.round(dur / 10)))
      else if (dur > 15) count = 8
      else if (dur > 3) count = 5
      for (let i = 0; i < count; i++) seekTimes.push(dur * (i + 1) / (count + 1))
      nextSeek()
    }

    video.onerror = () => { clearTimeout(timeout); video.remove(); resolve(frames) }
    video.src = dataUrl
  })
}

// 支持 content 数组（多模态）的模型列表
const MULTIMODAL_MODELS = ['agnes-2.0-flash', 'mimo-auto']

function maybeWarnFileModel(modelName: string, cat: string): boolean {
  if (!modelName || MULTIMODAL_MODELS.includes(modelName)) return true
  // modelName 不匹配列表 → 模型可能不支持文件内容上传
  return false
}

const STATUS_LABEL: Record<ChatStatus, { icon: string; text: string; color: string }> = {
  idle:       { icon: '', text: '', color: '' },
  connecting: { icon: '⏳', text: '正在连接...', color: 'var(--accent-ink)' },
  receiving:  { icon: '📡', text: '正在响应 (首字等待中)', color: 'var(--accent-ink)' },
  streaming:  { icon: '✍', text: '流式输出中', color: 'var(--success)' },
  done:       { icon: '✓', text: '响应完成', color: 'var(--success)' },
  error:      { icon: '✗', text: '响应出错', color: 'var(--error)' },
}

export function ChatPage() {
  const { apiKey } = useKey()
  const { config } = useConfig()
  const { messages, isStreaming, streamContent, metrics, status, send, abort, clear, restoreMessages } = useSSEChat(apiKey)

  const [model, setModel] = useState(config.chatModel)
  const [input, setInput] = useState('')
  const [settings, setSettings] = useState<ChatSettings>(DEFAULT_SETTINGS)
  const [showSettings, setShowSettings] = useState(false)
  const [uploadedFile, setUploadedFile] = useState<UploadedFile | null>(null)
  const [elapsed, setElapsed] = useState(0)
  const [loaded, setLoaded] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const saveTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  // ══ 加载聊天设置 + 消息历史 ══
  useEffect(() => {
    ;(async () => {
      try {
        const [savedSettings, savedMessages] = await Promise.all([
          loadChatSettings(),
          loadChatMessages(),
        ])
        if (savedSettings && typeof savedSettings === 'object') {
          setSettings({ ...DEFAULT_SETTINGS, ...savedSettings })
        }
        if (Array.isArray(savedMessages) && savedMessages.length > 0) {
          const restored = savedMessages.map((m: any) => ({
            role: m.role || 'user',
            content: m.content || '',
          }))
          restoreMessages(restored)
        }
      } catch (err) {
        console.warn('加载聊天数据失败:', err)
      }
      setLoaded(true)
    })()
  }, [])

  // ══ 保存聊天设置（防抖 500ms） ══
  const saveSettingsRef = useRef(settings)
  saveSettingsRef.current = settings

  useEffect(() => {
    if (!loaded) return
    if (saveTimerRef.current) clearTimeout(saveTimerRef.current)
    saveTimerRef.current = setTimeout(() => {
      saveChatSettings(saveSettingsRef.current).catch(() => {})
    }, 500)
    return () => { if (saveTimerRef.current) clearTimeout(saveTimerRef.current) }
  }, [settings, loaded])

  // ══ 保存聊天消息（防抖 1s） ══
  const saveMessagesRef = useRef(messages)
  saveMessagesRef.current = messages

  useEffect(() => {
    if (!loaded || messages.length === 0) return
    if (saveTimerRef.current) clearTimeout(saveTimerRef.current)
    saveTimerRef.current = setTimeout(() => {
      const saved = saveMessagesRef.current.map((m: any) => ({
        role: m.role,
        content: typeof m.content === 'string' ? m.content
          : (m.content as any[]).find((c: any) => c.type === 'text')?.text || '',
      }))
      saveChatMessages(saved).catch(() => {})
    }, 1000)
    return () => { if (saveTimerRef.current) clearTimeout(saveTimerRef.current) }
  }, [messages, loaded])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, streamContent])

  // ══ 计时器 ══
  useEffect(() => {
    if (status === 'connecting' || status === 'receiving' || status === 'streaming') {
      if (!timerRef.current) {
        const t0 = performance.now()
        timerRef.current = setInterval(() => {
          setElapsed(Math.round((performance.now() - t0) / 100) / 10)
        }, 100)
      }
    } else {
      if (timerRef.current) {
        clearInterval(timerRef.current)
        timerRef.current = null
      }
      if (status === 'idle') setElapsed(0)
    }
    return () => { if (timerRef.current) clearInterval(timerRef.current) }
  }, [status])

  const handleFileSelect = () => {
    fileInputRef.current?.click()
  }

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    if (file.size > FILE_MAX_SIZE) {
      showToast(`文件不能超过 5MB（当前 ${formatSize(file.size)}）`, 'error')
      return
    }
    const reader = new FileReader()
    reader.onload = () => {
      setUploadedFile({
        name: file.name,
        type: file.type,
        size: file.size,
        dataUrl: reader.result as string,
      })
    }
    reader.readAsDataURL(file)
    // 清空 input value，保证下次选同一文件也能触发 onChange
    e.target.value = ''
  }

  const handleClearAll = async () => {
    clear()
    try { await clearChatMessages() } catch {}
  }

  const handleSend = async () => {
    if (!apiKey) { showToast('请先在管理页配置 API Key', 'error'); return }
    if (!model && !config.chatModel) { showToast('请选择聊天模型', 'error'); return }
    if (!input.trim() && !uploadedFile) return

    const activeModel = model || config.chatModel
    const trimmedText = input.trim()
    setInput('')

    if (!uploadedFile) {
      await send(activeModel, settings, trimmedText)
    } else {
      const cat = getFileCategory(uploadedFile.type)

      // ══ 音频：先尝试 ASR 转写 ══
      if (cat === 'audio') {
        setUploadedFile(null)
        try {
          const blob = await (await fetch(uploadedFile.dataUrl)).blob()
          const audioFile = new File([blob], uploadedFile.name, { type: uploadedFile.type })
          const formData = new FormData()
          formData.append('file', audioFile)
          formData.append('model', 'whisper-1')
          formData.append('response_format', 'json')
          const asrRes = await fetch('/v1/audio/transcriptions', {
            method: 'POST',
            headers: { 'X-Api-Key': apiKey },
            body: formData,
          })
          if (asrRes.ok) {
            const asrData = await asrRes.json()
            const transcript = (asrData.text || '').trim()
            if (transcript) {
              const msg = (trimmedText || '') + (trimmedText ? '\n\n' : '') + '[音频转写] ' + transcript
              await send(activeModel, settings, msg)
              return
            }
          }
        } catch {}
        // gpt-* 系列（OpenAI 兼容）：Audio API 标准 → 文字描述 + 原音频数据
        if (activeModel.startsWith('gpt-')) {
          // 尝试 input_audio 格式（OpenAI Audio API 标准）
          const inputParts: any[] = [{ type: 'text', text: (trimmedText || '') + '\n\n音频文件: ' + uploadedFile.name + ' (' + formatSize(uploadedFile.size) + ')' }]
          // 从 data URL 提取纯 base64
          const b64data = uploadedFile.dataUrl.replace(/^data:audio\/\w+;base64,/, '')
          const audioFormat = uploadedFile.name.endsWith('.wav') ? 'wav' : uploadedFile.name.endsWith('.mp3') ? 'mp3' : 'wav'
          inputParts.push({ type: 'input_audio', input_audio: { data: b64data, format: audioFormat } })
          await send(activeModel, settings, inputParts)
        } else {
          // 其他模型 → audio_url 兜底
          const audioParts: any[] = [{ type: 'text', text: (trimmedText || '') + '\n\n[音频文件: ' + uploadedFile.name + ' (' + formatSize(uploadedFile.size) + ')]' }]
          audioParts.push({ type: 'audio_url', audio_url: { url: uploadedFile.dataUrl } })
          await send(activeModel, settings, audioParts)
        }
        return
      }

      // ══ 其他文件 ══
      if (!maybeWarnFileModel(activeModel, cat)) {
        showToast('模型 ' + activeModel + ' 可能不支持 ' + cat + ' 内容，建议切换至 agnes-2.0-flash', 'warning')
      }
      const parts: any[] = [{ type: 'text', text: trimmedText || '请分析这个文件。' }]
      if (cat === 'image') {
        parts.push({ type: 'image_url', image_url: { url: uploadedFile.dataUrl } })
      } else if (cat === 'video') {
        const savedUrl = uploadedFile.dataUrl
        const savedName = uploadedFile.name
        setUploadedFile(null)

        // gpt-* 系列（OpenAI 兼容）：走 Vision API 标准格式，跳过 video_url
        if (activeModel.startsWith('gpt-')) {
          const frames = await extractVideoKeyframes(savedUrl)
          if (frames.length > 0) {
            const frameParts: any[] = [{ type: 'text', text: trimmedText || '以下是一个视频的多个关键帧画面，请分析。' }]
            for (const frame of frames) {
              frameParts.push({ type: 'image_url', image_url: { url: frame, detail: 'auto' } })
            }
            await send(activeModel, settings, frameParts)
          } else {
            // 抽帧失败，回退 video_url
            const fallback: any[] = [{ type: 'text', text: trimmedText || '请分析这个视频。' }]
            fallback.push({ type: 'video_url', video_url: { url: savedUrl } })
            await send(activeModel, settings, fallback)
          }
          return
        }

        // 其他模型：先尝试 video_url，失败再降级为关键帧
        const videoParts: any[] = [{ type: 'text', text: trimmedText || '请分析这个视频。' }]
        videoParts.push({ type: 'video_url', video_url: { url: savedUrl } })
        await send(activeModel, settings, videoParts)

        if (status === 'error') {
          const frames = await extractVideoKeyframes(savedUrl)
          if (frames.length > 0) {
            const frameParts: any[] = [{ type: 'text', text: trimmedText || '请分析这个视频（关键帧）。' }]
            for (const frame of frames) {
              frameParts.push({ type: 'image_url', image_url: { url: frame, detail: 'auto' } })
            }
            await send(activeModel, settings, frameParts)
          }
        }
        return
      } else {
        parts[0].text += '\n\n[文件: ' + uploadedFile.name + ' (' + formatSize(uploadedFile.size) + ')]'
      }
      setUploadedFile(null)
      await send(activeModel, settings, parts)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
      e.preventDefault()
      handleSend()
    }
  }

  const statusInfo = STATUS_LABEL[status]

  return (
    <div style={{ display: 'flex', gap: 16, height: '100%' }}>
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        {/* Messages */}
        <div style={{ flex: 1, overflow: 'auto', padding: 16, display: 'flex', flexDirection: 'column', gap: 12 }}>
          {messages.length === 0 && !streamContent ? (
            <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)', fontSize: 13 }}>
              开始一次对话吧 · Ctrl+Enter 发送
            </div>
          ) : (
            <>
              {messages.map((m, idx) => (
                <div key={idx} className={`chat-bubble ${m.role === 'user' ? 'user' : 'assistant'}${m.metric ? ' with-metric' : ''}`}
                  style={{ alignSelf: m.role === 'user' ? 'flex-end' : 'flex-start', maxWidth: '80%' }}>
                  {typeof m.content === 'string' ? (
                    <div style={{ whiteSpace: 'pre-wrap', fontSize: 13 }}>{m.content}</div>
                  ) : (
                    <div>
                      {(m.content as any[]).filter(c => c.type === 'text').map((c, i) => (
                        <div key={i} style={{ whiteSpace: 'pre-wrap', fontSize: 13 }}>{c.text}</div>
                      ))}
                      {(m.content as any[]).filter(c => c.type === 'image_url').map((c, i) => (
                        <img key={i} src={c.image_url?.url} alt="" style={{ maxWidth: 200, borderRadius: 'var(--r-sm)', marginTop: 4 }} />
                      ))}
                      {(m.content as any[]).filter(c => c.type === 'video_url').map((c, i) => (
                        <video key={i} src={c.video_url?.url} controls style={{ maxWidth: 200, maxHeight: 200, borderRadius: 'var(--r-sm)', marginTop: 4 }} />
                      ))}
                      {(m.content as any[]).filter(c => c.type === 'audio_url').map((c, i) => (
                        <audio key={i} src={c.audio_url?.url} controls style={{ width: 200, marginTop: 4 }} />
                      ))}
                    </div>
                  )}
                  {m.metric && <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 4 }}>{m.metric}</div>}
                </div>
              ))}
              {isStreaming && streamContent && (
                <div className="chat-bubble assistant streaming" style={{ alignSelf: 'flex-start', maxWidth: '80%' }}>
                  <div style={{ whiteSpace: 'pre-wrap', fontSize: 13 }}>{streamContent}</div>
                  <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 4 }}>
                    ⚡ TTFB {metrics.ttfb}ms · TTFT {metrics.ttft}ms
                  </div>
                </div>
              )}
            </>
          )}

          {status !== 'idle' && statusInfo.icon && (
            <div style={{
              display: 'flex', alignItems: 'center', gap: 8,
              padding: '6px 12px', borderRadius: 'var(--r-sm)',
              background: status === 'error' ? 'color-mix(in srgb, var(--error) 10%, transparent)' : 'var(--surface-2)',
              fontSize: 12, color: statusInfo.color,
              alignSelf: 'flex-start',
              animation: status === 'streaming' ? 'none' : 'pulse 1.5s ease-in-out infinite',
            }}>
              <span>{statusInfo.icon}</span>
              <span>{statusInfo.text}</span>
              {elapsed > 0 && status !== 'done' && status !== 'error' && (
                <span style={{ color: 'var(--text-muted)', fontSize: 11, marginLeft: 4 }}>{elapsed.toFixed(1)}s</span>
              )}
              {status === 'done' && (
                <span style={{ color: 'var(--text-muted)', fontSize: 11, marginLeft: 4 }}>总耗时 {metrics.total}ms</span>
              )}
              {status === 'error' && streamContent && (
                <span style={{ color: 'var(--error)', fontSize: 11, marginLeft: 4, maxWidth: 300, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {streamContent.replace('[错误] ', '')}
                </span>
              )}
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Input area */}
        <div style={{ borderTop: '1px solid var(--border)', padding: 12, background: 'var(--surface)' }}>
          {uploadedFile && (
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8, padding: 8, background: 'var(--surface-2)', borderRadius: 'var(--r-sm)' }}>
              {getFileCategory(uploadedFile.type) === 'image' ? (
                <img src={uploadedFile.dataUrl} alt="" style={{ height: 40, borderRadius: 4 }} />
              ) : getFileCategory(uploadedFile.type) === 'video' ? (
                <video src={uploadedFile.dataUrl} style={{ height: 40, borderRadius: 4 }} />
              ) : getFileCategory(uploadedFile.type) === 'audio' ? (
                <audio src={uploadedFile.dataUrl} controls style={{ height: 32 }} />
              ) : (
                <span style={{ fontSize: 11, color: 'var(--text-soft)' }}>{uploadedFile.name}</span>
              )}
              <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>{formatSize(uploadedFile.size)}</span>
              <button onClick={() => setUploadedFile(null)} style={{ border: 'none', background: 'transparent', cursor: 'pointer', color: 'var(--text-muted)' }}>×</button>
            </div>
          )}

          <div style={{ display: 'flex', gap: 8 }}>
            <button onClick={handleFileSelect} className="btn btn-subtle" style={{ fontSize: 16, padding: '6px 10px' }} title="上传文件">
              📎
            </button>
            <input ref={fileInputRef} type="file" style={{ display: 'none' }} onChange={handleFileChange}  />
            <textarea value={input} onChange={e => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="输入消息… (Ctrl+Enter 发送)"
              rows={2}
              style={{ flex: 1, resize: 'none', fontSize: 13 }} />
            <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
              <button onClick={handleSend} disabled={isStreaming || (!input.trim() && !uploadedFile)}
                className="btn btn-accent" style={{ padding: '6px 14px', fontSize: 12 }}>
                {isStreaming ? <Spinner size="sm" /> : '发送'}
              </button>
              <button onClick={abort} disabled={!isStreaming}
                className="btn btn-subtle" style={{ padding: '2px 8px', fontSize: 10 }}>
                中止
              </button>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 8 }}>
            <ModelSelect type="chat" value={model || config.chatModel} onChange={setModel} />
            <button onClick={() => setShowSettings(!showSettings)}
              className="btn btn-subtle" style={{ fontSize: 11, padding: '2px 8px' }}>
              {showSettings ? '收起参数' : '参数'}
            </button>
            <button onClick={handleClearAll} className="btn btn-subtle" style={{ fontSize: 11, padding: '2px 8px', marginLeft: 'auto' }}>
              清空对话
            </button>
          </div>

          {showSettings && (
            <div style={{ marginTop: 8, padding: 12, background: 'var(--surface-2)', borderRadius: 'var(--r-sm)', display: 'flex', flexDirection: 'column', gap: 8, fontSize: 12 }}>
              <div>
                <label style={{ color: 'var(--text-muted)', display: 'block', marginBottom: 2 }}>系统提示</label>
                <textarea value={settings.systemPrompt}
                  onChange={e => setSettings({ ...settings, systemPrompt: e.target.value })}
                  rows={2} style={{ width: '100%', resize: 'vertical', fontSize: 12 }} />
              </div>
              <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap' }}>
                <div>
                  <label style={{ color: 'var(--text-muted)' }}>Temperature: {settings.temperature.toFixed(2)}</label>
                  <input type="range" min={0} max={2} step={0.05} value={settings.temperature}
                    onChange={e => setSettings({ ...settings, temperature: parseFloat(e.target.value) })}
                    style={{ width: 120, display: 'block' }} />
                </div>
                <div>
                  <label style={{ color: 'var(--text-muted)' }}>Top P: {settings.topP.toFixed(2)}</label>
                  <input type="range" min={0} max={1} step={0.05} value={settings.topP}
                    onChange={e => setSettings({ ...settings, topP: parseFloat(e.target.value) })}
                    style={{ width: 120, display: 'block' }} />
                </div>
                <div>
                  <label style={{ color: 'var(--text-muted)' }}>Max Tokens</label>
                  <input type="number" value={settings.maxTokens === '' ? '' : settings.maxTokens}
                    onChange={e => setSettings({ ...settings, maxTokens: e.target.value === '' ? '' : parseInt(e.target.value) || '' })}
                    style={{ width: 80, fontSize: 12 }} placeholder="默认" />
                </div>
              </div>
              <div style={{ display: 'flex', gap: 16, alignItems: 'center' }}>
                <label style={{ display: 'flex', alignItems: 'center', gap: 4, cursor: 'pointer' }}>
                  <input type="checkbox" checked={settings.enableThinking}
                    onChange={e => setSettings({ ...settings, enableThinking: e.target.checked })} />
                  <span>Thinking</span>
                </label>
                {settings.enableThinking && (
                  <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                    <span>Budget:</span>
                    <input type="number" value={settings.thinkingBudget}
                      onChange={e => setSettings({ ...settings, thinkingBudget: parseInt(e.target.value) || 0 })}
                      style={{ width: 80, fontSize: 12 }} />
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

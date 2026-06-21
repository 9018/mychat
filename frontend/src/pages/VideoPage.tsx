// ── 视频生成页 ────────────────────────────────────────────────
import { useState, useRef, useCallback } from 'react'
import { useKey } from '@/contexts/KeyContext'
import { useConfig } from '@/contexts/ConfigContext'
import { useHistory } from '@/contexts/HistoryContext'
import { usePolling } from '@/hooks/usePolling'
import { ModelSelect } from '@/components/common/ModelSelect'
import { AspectPicker } from '@/components/common/AspectPicker'
import { Spinner } from '@/components/common/Spinner'
import { StatusCard } from '@/components/common/StatusCard'
import { HistoryStrip } from '@/components/History/HistoryStrip'
import { ImageUploader } from '@/components/common/ImageUploader'
import { showToast } from '@/components/common/Toast'
import { apiProxyPost } from '@/api/client'
import { truncatePrompt, isSafeMediaUrl, normalizeImageInput } from '@/lib/utils'
import type { VideoMode, Aspect } from '@/api/types'

interface VideoPageProps {
  videoMode: VideoMode
  onVideoModeChange?: (mode: VideoMode) => void
}

const VIDEO_ASPECTS: Aspect[] = [
  { id: '16:9', label: '16:9', w: 20, h: 11.25 },
  { id: '9:16', label: '9:16', w: 11.25, h: 20 },
  { id: '1:1', label: '1:1', w: 16, h: 16 },
  { id: '4:3', label: '4:3', w: 18, h: 13.5 },
  { id: '3:4', label: '3:4', w: 13.5, h: 18 },
]

const ASPECT_MAP: Record<string, [number, number]> = {
  '16:9': [1280, 720], '9:16': [720, 1280], '1:1': [1024, 1024],
  '4:3': [1024, 768], '3:4': [768, 1024],
}

const VIDEO_MODE_HINTS: Record<string, { label: string; hint: string; ph: string }> = {
  text: {
    label: '文生视频',
    hint: '仅凭文字描述直接生成视频内容。',
    ph: '描述视频内容、场景、运镜、风格…',
  },
  image: {
    label: '图生视频',
    hint: '提供一张起始参考图，AI 根据提示词让图片动起来。',
    ph: '描述视频中会发生什么动态变化…',
  },
  multi: {
    label: '多图视频',
    hint: '提供多张图片，AI 分析图片内容并生成连贯视频。',
    ph: '描述这组图片之间的故事线…',
  },
  keyframe: {
    label: '关键帧',
    hint: '第一张为起始帧，最后一张为结束帧，AI 生成中间的过渡动画。',
    ph: '描述关键帧之间期待的过渡效果…',
  },
}

export function VideoPage({ videoMode }: VideoPageProps) {
  const { apiKey } = useKey()
  const { config } = useConfig()
  const { addItem } = useHistory()

  const [prompt, setPrompt] = useState('')
  const [aspect, setAspect] = useState('16:9')
  const [width, setWidth] = useState(1280)
  const [height, setHeight] = useState(720)
  const [model, setModel] = useState(config.videoModel)
  const [numFrames, setNumFrames] = useState(121)
  const [frameRate, setFrameRate] = useState(24)
  const [seed, setSeed] = useState('')
  const [negPrompt, setNegPrompt] = useState('')
  const [imageUrl, setImageUrl] = useState('')
  const [imagePreviewUrl, setImagePreviewUrl] = useState('')
  const [imageUrls, setImageUrls] = useState<string[]>([''])
  const [imagePreviews, setImagePreviews] = useState<string[]>([''])

  const [resultUrl, setResultUrl] = useState('')
  const [resultMeta, setResultMeta] = useState('')
  const [error, setError] = useState('')
  const abortRef = useRef<AbortController | null>(null)

  const { isPolling, status, progress, start: startPolling, stop: stopPolling, setError: setPollError } = usePolling(apiKey)

  const handleAspectChange = (id: string) => {
    setAspect(id)
    const dims = ASPECT_MAP[id]
    if (dims) { setWidth(dims[0]); setHeight(dims[1]) }
  }

  const addImageRow = () => {
    setImageUrls(prev => [...prev, ''])
    setImagePreviews(prev => [...prev, ''])
  }

  const updateImageRow = (idx: number, val: string) => {
    setImageUrls(prev => { const n = [...prev]; n[idx] = val; return n })
    setImagePreviews(prev => {
      const n = [...prev]
      n[idx] = val.startsWith('data:image/') ? val : ''
      return n
    })
  }

  const removeImageRow = (idx: number) => {
    setImageUrls(prev => prev.length > 1 ? prev.filter((_, i) => i !== idx) : prev)
    setImagePreviews(prev => prev.length > 1 ? prev.filter((_, i) => i !== idx) : [''])
  }

  const handleSingleImageUpload = (dataUrl: string) => {
    setImageUrl(dataUrl)
    setImagePreviewUrl(dataUrl)
  }

  const handleMultiImageUpload = (idx: number) => (dataUrl: string) => {
    updateImageRow(idx, dataUrl)
  }

  const buildBody = useCallback(() => {
    const body: Record<string, any> = {
      model: model || config.videoModel,
      prompt: prompt.trim(),
      width, height,
      num_frames: numFrames,
      frame_rate: frameRate,
    }
    if (seed) body.seed = parseInt(seed)
    if (negPrompt) body.negative_prompt = negPrompt

    // ══ 模式专用参数注入 ══
    if (videoMode === 'image' && imageUrl) {
      // 图生视频：单张参考图 — 标准化为纯 base64 或 HTTP URL
      body.image = normalizeImageInput(imageUrl, 'base64')
    } else if (videoMode === 'multi') {
      // 多图视频：多张参考图
      const urls = imageUrls.map(u => normalizeImageInput(u.trim(), 'base64')).filter(Boolean)
      if (urls.length > 0) {
        body.extra_body = { image: urls }
      }
    } else if (videoMode === 'keyframe') {
      // 关键帧动画：多张参考图 + keyframe 模式
      const urls = imageUrls.map(u => normalizeImageInput(u.trim(), 'base64')).filter(Boolean)
      if (urls.length > 0) {
        body.extra_body = { image: urls, mode: 'keyframes' }
      }
    }

    return body
  }, [model, config.videoModel, prompt, width, height, numFrames, frameRate, seed, negPrompt, videoMode, imageUrl, imageUrls])

  const handleGenerate = async () => {
    if (!apiKey) { showToast('请先配置 API Key', 'error'); return }
    if (!prompt.trim()) { showToast('请输入提示词', 'error'); return }

    if (videoMode === 'image' && !imageUrl.trim()) {
      showToast('图生视频模式请提供参考图', 'error'); return
    }
    if ((videoMode === 'multi' || videoMode === 'keyframe') && !imageUrls.some(u => u.trim())) {
      showToast('请提供至少一张参考图', 'error'); return
    }

    setError('')
    setResultUrl('')
    abortRef.current = new AbortController()

    const body = buildBody()

    try {
      const res = await apiProxyPost('/v1/videos', body, apiKey, abortRef.current.signal)
      const data = await res.json()
      if (!res.ok) throw new Error(data.error?.message || data.message || `HTTP ${res.status}`)

      const taskId = data.id
      const videoId = data.video_id || null

      startPolling(videoId, taskId, body.model, {
        onComplete: (resultData) => {
          const rawUrl = resultData.video_url || resultData.remixed_from_video_id
          const videoUrl = rawUrl
            ? `/video-proxy?url=${encodeURIComponent(rawUrl)}`
            : ''
          setResultUrl(videoUrl)
          const dur = resultData.seconds ? `时长 ${resultData.seconds}s` : ''
          const size = resultData.size ? `· 分辨率 ${resultData.size}` : ''
          setResultMeta([dur, size].filter(Boolean).join(' '))

          if (body.prompt) {
            addItem({
              id: 'h_' + Date.now(),
              title: truncatePrompt(body.prompt, 20),
              kind: 'video',
              ar: aspect,
              tone: 292,
              prompt: body.prompt,
              model: body.model,
              width: body.width,
              height: body.height,
              url: videoUrl,
            })
          }
        },
        onError: (errMsg) => { setError(errMsg) },
        onProgress: () => {},
      })
    } catch (err: any) {
      if (err.name === 'AbortError') return
      setError(err.message)
      showToast(`提交失败: ${err.message}`, 'error')
    }
  }

  const handleCancel = () => {
    abortRef.current?.abort()
    stopPolling()
    setError('')
  }

  const vh = VIDEO_MODE_HINTS[videoMode] || VIDEO_MODE_HINTS.text

  return (
    <div style={{ display: 'flex', gap: 16, height: '100%' }}>
      <div style={{ flex: '0 0 400px', display: 'flex', flexDirection: 'column', gap: 12, padding: 16, overflow: 'auto' }}>
        <div>
          <label style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 4, display: 'block' }}>模型</label>
          <ModelSelect type="video" value={model || config.videoModel} onChange={setModel} />
        </div>

        <div>
          <label style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 4, display: 'block' }}>
            提示词 <span style={{ color: 'var(--accent-ink)' }}>({vh.label})</span>
          </label>
          <textarea value={prompt} onChange={e => setPrompt(e.target.value)}
            placeholder={vh.ph}
            rows={3} style={{ width: '100%', resize: 'vertical' }} />
        </div>

        {/* 图生视频：单张参考图 */}
        {videoMode === 'image' && (
          <div>
            <label style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 4, display: 'block' }}>参考图</label>
            {imagePreviewUrl && (
              <div style={{
                position: 'relative', marginBottom: 8,
                borderRadius: 'var(--r-sm)', overflow: 'hidden',
                border: '1px solid var(--border)', background: 'var(--surface-2)',
              }}>
                <img src={imagePreviewUrl} alt="" style={{ width: '100%', maxHeight: 200, objectFit: 'contain', display: 'block' }} />
                <button onClick={() => { setImageUrl(''); setImagePreviewUrl('') }}
                  style={{
                    position: 'absolute', top: 4, right: 4,
                    width: 24, height: 24, borderRadius: '50%',
                    border: 'none', background: 'rgba(0,0,0,0.6)', color: '#fff',
                    fontSize: 14, cursor: 'pointer',
                  }}>×</button>
              </div>
            )}
            <div style={{ display: 'flex', gap: 8 }}>
              <input type="text" value={imageUrl} onChange={e => {
                setImageUrl(e.target.value)
                setImagePreviewUrl(e.target.value.startsWith('data:image/') ? e.target.value : '')
              }} placeholder="粘贴图片链接" style={{ flex: 1 }} />
              <ImageUploader onImage={handleSingleImageUpload} onClear={() => { setImageUrl(""); setImagePreviewUrl("") }} compact />
            </div>
            <span style={{ fontSize: 11, color: 'var(--text-muted)', display: 'block', marginTop: 2 }}>{vh.hint}</span>
          </div>
        )}

        {/* 多图 / 关键帧：多张参考图 */}
        {(videoMode === 'multi' || videoMode === 'keyframe') && (
          <div>
            <label style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 4, display: 'block' }}>
              {videoMode === 'keyframe' ? '关键帧（第一张起始，最后一张结束）' : '多张参考图'}
            </label>
            <div id="imageList" style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
              {imageUrls.map((url, idx) => (
                <div key={idx} style={{ display: 'flex', gap: 4, flexDirection: 'column' }}>
                  <div style={{ display: 'flex', gap: 4, alignItems: 'center' }}>
                    <input type="text" value={url} onChange={e => updateImageRow(idx, e.target.value)}
                      placeholder="图片链接" style={{ flex: 1, fontSize: 12 }} />
                    <ImageUploader onImage={handleMultiImageUpload(idx)} onClear={() => removeImageRow(idx)} compact />
                    <button onClick={() => removeImageRow(idx)} className="btn btn-icon" style={{ fontSize: 14 }}>×</button>
                  </div>
                  {imagePreviews[idx] && (
                    <img src={imagePreviews[idx]} alt="" style={{
                      width: '100%', maxHeight: 120, objectFit: 'contain', borderRadius: 'var(--r-sm)',
                      border: '1px solid var(--border)',
                    }} />
                  )}
                </div>
              ))}
              <button onClick={addImageRow} className="btn btn-subtle" style={{ fontSize: 11, padding: '2px 8px', alignSelf: 'flex-start' }}>
                + 添加图片
              </button>
            </div>
            <span style={{ fontSize: 11, color: 'var(--text-muted)', display: 'block', marginTop: 2 }}>{vh.hint}</span>
          </div>
        )}

        <div>
          <label style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 4, display: 'block' }}>比例</label>
          <AspectPicker aspects={VIDEO_ASPECTS} value={aspect} onChange={handleAspectChange} />
          <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
            <input type="number" value={width} onChange={e => setWidth(Number(e.target.value))} style={{ width: 80 }} />
            <span style={{ lineHeight: '36px', color: 'var(--text-muted)' }}>×</span>
            <input type="number" value={height} onChange={e => setHeight(Number(e.target.value))} style={{ width: 80 }} />
          </div>
        </div>

        <details style={{ fontSize: 12 }}>
          <summary style={{ cursor: 'pointer', color: 'var(--text-soft)' }}>高级参数</summary>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginTop: 8 }}>
            <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
              <span style={{ width: 80, color: 'var(--text-muted)' }}>帧数</span>
              <input type="number" value={numFrames} onChange={e => setNumFrames(Number(e.target.value))} style={{ flex: 1 }} />
            </div>
            {/* 帧数预设按钮 */}
            {[81, 121, 161, 241, 441].map(n => (
              <button key={n} onClick={() => setNumFrames(n)}
                style={{
                  fontSize: 11, padding: '2px 6px', borderRadius: 'var(--r-sm)',
                  border: numFrames === n ? '1.5px solid var(--accent)' : '1px solid var(--border)',
                  background: numFrames === n ? 'var(--accent-soft)' : 'var(--surface)',
                  cursor: 'pointer', color: 'var(--text)',
                }}>
                {n}帧 · ~{(n / frameRate).toFixed(1)}s
              </button>
            ))}
            <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
              <span style={{ width: 80, color: 'var(--text-muted)' }}>帧率</span>
              <input type="number" value={frameRate} onChange={e => setFrameRate(Number(e.target.value))} style={{ flex: 1 }} />
            </div>
            <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
              <span style={{ width: 80, color: 'var(--text-muted)' }}>Seed</span>
              <input type="text" value={seed} onChange={e => setSeed(e.target.value)} placeholder="随机" style={{ flex: 1 }} />
            </div>
            <div>
              <span style={{ color: 'var(--text-muted)', marginBottom: 4, display: 'block' }}>负向提示词</span>
              <textarea value={negPrompt} onChange={e => setNegPrompt(e.target.value)} rows={2}
                style={{ width: '100%', resize: 'vertical' }} />
            </div>
          </div>
        </details>

        <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 4 }}>
          预估时长：{(numFrames / frameRate).toFixed(1)} 秒（{numFrames}帧 ÷ {frameRate}fps）
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <button onClick={handleGenerate} disabled={isPolling}
            className="btn btn-accent" style={{ flex: 1, padding: '8px 16px', fontSize: 13 }}>
            {isPolling ? <><Spinner size="sm" /> 生成中…</> : '生成视频'}
          </button>
          {isPolling && (
            <button onClick={handleCancel} className="btn btn-subtle" style={{ padding: '8px 12px', fontSize: 13 }}>
              取消
            </button>
          )}
        </div>
        {error && <div style={{ color: 'var(--error)', fontSize: 12 }}>{error}</div>}
      </div>

      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', padding: 16, overflow: 'auto' }}>
        {isPolling && (
          <StatusCard taskId="" status={status} progress={progress} note="视频生成中…" onCancel={handleCancel} />
        )}
        {!resultUrl && !isPolling && (
          <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)' }}>
            <svg viewBox="0 0 24 24" width={32} height={32} fill="none" stroke="currentColor" strokeWidth="1.6">
              <rect x="3.2" y="4.5" width="17.6" height="15" rx="2.5" />
              <path d="M8 4.5v15M16 4.5v15M3.2 9.5h4.8M16 9.5h4.8M3.2 14.5h4.8M16 14.5h4.8" />
            </svg>
            <p style={{ marginTop: 8, fontSize: 13 }}>输入提示词并生成视频</p>
          </div>
        )}
        {resultUrl && (
          <div style={{ background: 'var(--surface)', borderRadius: 'var(--r-lg)', border: '1px solid var(--border)', padding: 16 }}>
            <video src={resultUrl} controls autoPlay style={{ width: '100%', maxHeight: '60vh', borderRadius: 'var(--r)' }} />
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 8 }}>
              <span style={{ fontSize: 12, color: 'var(--text-soft)' }}>{resultMeta}</span>
              <a href={resultUrl} download className="btn btn-accent" style={{ fontSize: 12, padding: '4px 12px', textDecoration: 'none' }}>
                下载
              </a>
            </div>
          </div>
        )}
        <HistoryStrip currentKind="video" onSelect={(h) => {
          if (h.prompt) setPrompt(h.prompt)
          if (h.ar && ASPECT_MAP[h.ar]) { setAspect(h.ar); setWidth(ASPECT_MAP[h.ar][0]); setHeight(ASPECT_MAP[h.ar][1]) }
          if (h.model) setModel(h.model)
          if (h.url && isSafeMediaUrl(h.url)) setResultUrl(h.url)
        }} />
      </div>
    </div>
  )
}

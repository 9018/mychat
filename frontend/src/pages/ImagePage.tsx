// ── 图像生成页 ────────────────────────────────────────────────
import { useState, useRef } from 'react'
import { useKey } from '@/contexts/KeyContext'
import { useConfig } from '@/contexts/ConfigContext'
import { useHistory } from '@/contexts/HistoryContext'
import { ModelSelect } from '@/components/common/ModelSelect'
import { AspectPicker } from '@/components/common/AspectPicker'
import { Spinner } from '@/components/common/Spinner'
import { StatusCard } from '@/components/common/StatusCard'
import { HistoryStrip } from '@/components/History/HistoryStrip'
import { ImageUploader } from '@/components/common/ImageUploader'
import { showToast } from '@/components/common/Toast'
import { apiProxyPost } from '@/api/client'
import { truncatePrompt, isSafeMediaUrl, normalizeImageInput } from '@/lib/utils'
import type { ImgMode, Aspect } from '@/api/types'

interface ImagePageProps {
  imgMode: ImgMode
  onImgModeChange?: (mode: ImgMode) => void
}

const IMAGE_PRESETS: Aspect[] = [
  { id: '1:1', label: '1:1', w: 16, h: 16 },
  { id: '3:4', label: '3:4', w: 13.5, h: 18 },
  { id: '4:3', label: '4:3', w: 18, h: 13.5 },
  { id: '9:16', label: '9:16', w: 11.25, h: 20 },
  { id: '16:9', label: '16:9', w: 20, h: 11.25 },
  { id: '2:3', label: '2:3', w: 12, h: 18 },
  { id: '3:2', label: '3:2', w: 18, h: 12 },
  { id: '9:21', label: '9:21', w: 8.5, h: 20 },
  { id: '21:9', label: '21:9', w: 20, h: 8.5 },
]

const SIZE_MAP: Record<string, [number, number]> = {
  '1:1': [1024, 1024], '3:4': [768, 1024], '4:3': [1024, 768],
  '9:16': [720, 1280], '16:9': [1280, 720], '9:21': [768, 1792],
  '21:9': [1792, 768], '2:3': [683, 1024], '3:2': [1024, 683],
}

const MODE_HINTS: Record<string, { label: string; hint: string; ph: string }> = {
  txt2img: {
    label: '',
    hint: '',
    ph: '描述图像内容、主体、动作、场景、光线和艺术风格…\n例如：A stunning portrait of a cybernetic goddess, intricate neon makeup, glowing neural pathways, cyberpunk city background, hyperrealistic, octane render, 8k resolution',
  },
  img2img: {
    label: '图生图',
    hint: '提供原图链接，AI 将理解原图内容并根据你的要求重新生成（需两步分析）。',
    ph: '描述你希望对原图进行的修改…\n例如：Change the character style to 3D Pixar animation, high detail, colorful background',
  },
  composition: {
    label: '构图保留',
    hint: '结构/构图保留模式：AI 分析原图构图然后按你的描述生成新内容。',
    ph: '描述你希望生成的新图像内容，将参照原图的构图…\n例如：A highly detailed fantasy castle, sunset lighting, dramatic clouds',
  },
  high_density: {
    label: '高密度优化',
    hint: '高信息密度优化模式：AI 分析原图细节并生成更丰富的版本。',
    ph: '描述你期望的增强方向…\n例如：Professional studio shot, splashing water, dramatic lighting, luxury poster style',
  },
}

export function ImagePage({ imgMode }: ImagePageProps) {
  const { apiKey } = useKey()
  const { config, setConfig } = useConfig()
  const { addItem } = useHistory()

  const [prompt, setPrompt] = useState('')
  const [aspect, setAspect] = useState('16:9')
  const [width, setWidth] = useState(1280)
  const [height, setHeight] = useState(720)
  const [model, setModel] = useState(config.imageModel)
  const [refUrl, setRefUrl] = useState('')
  const [previewUrl, setPreviewUrl] = useState('')
  const [seed, setSeed] = useState('')
  const [steps, setSteps] = useState('')
  const [negPrompt, setNegPrompt] = useState('')
  const [generating, setGenerating] = useState(false)
  const [resultUrl, setResultUrl] = useState('')
  const [resultDimensions, setResultDimensions] = useState({ w: 0, h: 0 })
  const [error, setError] = useState('')
  const [stepLabel, setStepLabel] = useState('')
  const abortRef = useRef<AbortController | null>(null)

  const handleAspectChange = (id: string) => {
    setAspect(id)
    const dims = SIZE_MAP[id]
    if (dims) {
      if (id === 'custom') return
      setWidth(dims[0])
      setHeight(dims[1])
    }
  }

  const handleRefInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value
    setRefUrl(val)
    setPreviewUrl(val.startsWith('data:image/') ? val : '')
  }

  const handleImageUpload = (dataUrl: string, w: number, h: number, filename: string) => {
    setRefUrl(dataUrl)
    setPreviewUrl(dataUrl)
  }

  const handleClearRef = () => {
    setRefUrl('')
    setPreviewUrl('')
  }

  const handleGenerate = async () => {
    if (!apiKey) { showToast('请先配置 API Key', 'error'); return }
    if (!prompt.trim()) { showToast('请输入提示词', 'error'); return }
    if (imgMode !== 'txt2img' && !refUrl.trim()) { showToast('请先输入参考图片 URL', 'error'); return }

    setError('')
    setResultUrl('')
    setGenerating(true)
    setStepLabel('')
    abortRef.current = new AbortController()

    const normImage = refUrl.trim() ? normalizeImageInput(refUrl.trim(), 'url-or-base64') : ''

    // ══ 第一步：非 txt2img 模式，用多模态 chat 分析参考图 ══
    let finalPrompt = prompt.trim()

    if (imgMode !== 'txt2img' && refUrl.trim()) {
      setStepLabel('🔍 AI 正在分析参考图...')

      const modeDesc = {
        img2img: 'Modify this image according to the user\'s request.',
        composition: 'Analyze the composition/layout of this image, then generate a new image with a different subject but similar layout.',
        high_density: 'Enhance the details, texture and information density of this image. Generate a more detailed and richer version.',
      }[imgMode] || 'Analyze this image and generate a modified version.'

      try {
        const chatBody = {
          model: 'agnes-2.0-flash',
          messages: [{
            role: 'user',
            content: [
              { type: 'text', text: `You are an expert image prompt engineer.
I will show you a reference image and give you a modification request.

Reference image analysis request: ${modeDesc}
User's modification request: "${prompt.trim()}"

Your job:
1. Carefully analyze the reference image - describe what you see
2. Generate a SINGLE detailed English image generation prompt that would reproduce the reference image WITH the user's requested modifications applied

Output ONLY the final prompt, no explanations, no numbering, no analysis.
The prompt must be detailed (100-300 words), covering subject, action, scene, lighting, style, colors, composition, camera angle, and mood.` },
              { type: 'image_url', image_url: { url: refUrl } },  // Send full data URL
            ],
          }],
          stream: false,
          max_tokens: 1024,
        }

        const chatRes = await fetch('/v1/chat/completions', {
          method: 'POST',
          headers: { 'X-Api-Key': apiKey, 'Content-Type': 'application/json' },
          body: JSON.stringify(chatBody),
          signal: abortRef.current?.signal,
        })
        const chatData = await chatRes.json()
        if (!chatRes.ok) throw new Error(chatData.error?.message || `Chat analysis failed (HTTP ${chatRes.status})`)

        const analysisResult = chatData.choices?.[0]?.message?.content?.trim()
        if (analysisResult && analysisResult.length > 20) {
          finalPrompt = analysisResult
        }
      } catch (err: any) {
        if (err.name === 'AbortError') { setGenerating(false); return }
        // Fallback: use original prompt if chat analysis fails
        console.warn('图生图分析失败，使用原始提示词:', err.message)
        showToast('图像分析失败，直接使用原始提示词生成', 'warning')
      }
    }

    // ══ 第二步：生图请求 ══
    setStepLabel('🎨 正在生成图像...')

    const body: Record<string, any> = {
      model: model || config.imageModel,
      prompt: finalPrompt,
      size: `${width}x${height}`,
      width, height,
      n: 1,
    }

    if (normImage) {
      body.extra_body = {
        image: [normImage],
        response_format: 'b64_json',
      }
    }

    if (seed) body.seed = parseInt(seed)
    if (steps) body.num_inference_steps = parseInt(steps)
    if (negPrompt) body.negative_prompt = negPrompt

    try {
      const res = await apiProxyPost('/v1/images/generations', body, apiKey, abortRef.current?.signal)
      const data = await res.json()
      if (!res.ok) throw new Error(data.error?.message || `HTTP ${res.status}`)

      const imageUrl = data.data?.[0]?.b64_json
        ? `data:image/png;base64,${data.data[0].b64_json}`
        : data.data?.[0]?.url

      if (!imageUrl) throw new Error('未获取到有效的图像数据')

      setResultUrl(imageUrl)
      setResultDimensions({ w: width, h: height })
      setStepLabel('')

      await addItem({
        id: 'h_' + Date.now(),
        title: truncatePrompt(prompt, 20),
        kind: 'image',
        ar: aspect,
        tone: 292,
        prompt: prompt.trim(),
        model: model || config.imageModel,
        width, height,
        url: imageUrl,
      })
    } catch (err: any) {
      if (err.name === 'AbortError') return
      setError(err.message)
      showToast(`生成失败: ${err.message}`, 'error')
    } finally {
      setStepLabel('')
      setGenerating(false)
      abortRef.current = null
    }
  }

  const handleCancel = () => {
    abortRef.current?.abort()
    setGenerating(false)
    setStepLabel('')
  }

  const handleDownload = async () => {
    if (!resultUrl) return
    try {
      let blobUrl = resultUrl
      if (resultUrl.startsWith('data:')) {
        const parts = resultUrl.split(',')
        const mime = parts[0].match(/:(.*?);/)?.[1] || 'image/png'
        const bstr = atob(parts[1])
        const u8arr = new Uint8Array(bstr.length)
        for (let i = 0; i < bstr.length; i++) u8arr[i] = bstr.charCodeAt(i)
        const blob = new Blob([u8arr], { type: mime })
        blobUrl = URL.createObjectURL(blob)
      } else {
        const proxyUrl = resultUrl.startsWith('http') ? `/video-proxy?url=${encodeURIComponent(resultUrl)}` : resultUrl
        const res = await fetch(proxyUrl)
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        const imgBlob = await res.blob()
        blobUrl = URL.createObjectURL(imgBlob)
      }
      const a = document.createElement('a')
      a.href = blobUrl
      a.download = 'agnes-image.png'
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(blobUrl)
    } catch (err: any) {
      showToast(`下载失败: ${err.message}`, 'error')
    }
  }

  const mh = MODE_HINTS[imgMode] || MODE_HINTS.txt2img

  return (
    <div style={{ display: 'flex', gap: 16, height: '100%' }}>
      <div style={{ flex: '0 0 400px', display: 'flex', flexDirection: 'column', gap: 12, padding: 16, overflow: 'auto' }}>
        <div>
          <label style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 4, display: 'block' }}>模型</label>
          <ModelSelect type="image" value={model || config.imageModel} onChange={setModel} />
        </div>

        <div>
          <label style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 4, display: 'block' }}>
            提示词 {mh.label && <span style={{ color: 'var(--accent-ink)' }}>({mh.label})</span>}
          </label>
          <textarea value={prompt} onChange={e => setPrompt(e.target.value)}
            placeholder={mh.ph}
            rows={4} style={{ width: '100%', resize: 'vertical' }} />
        </div>

        {imgMode !== 'txt2img' && (
          <div>
            <label style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 4, display: 'block' }}>
              参考图 ({mh.label})
            </label>
            {previewUrl && (
              <div style={{
                position: 'relative', marginBottom: 8,
                borderRadius: 'var(--r-sm)', overflow: 'hidden',
                border: '1px solid var(--border)', background: 'var(--surface-2)',
              }}>
                <img src={previewUrl} alt="参考图" style={{
                  width: '100%', maxHeight: 200, objectFit: 'contain', display: 'block',
                }} />
                <button onClick={handleClearRef} title="清除参考图"
                  style={{
                    position: 'absolute', top: 4, right: 4,
                    width: 24, height: 24, borderRadius: '50%',
                    border: 'none', background: 'rgba(0,0,0,0.6)', color: '#fff',
                    fontSize: 14, cursor: 'pointer', lineHeight: '24px', textAlign: 'center',
                  }}>×</button>
              </div>
            )}
            <div style={{ display: 'flex', gap: 8 }}>
              <input type="text" value={refUrl} onChange={handleRefInputChange}
                placeholder="粘贴图片链接" style={{ flex: 1, fontSize: 12 }} />
              <ImageUploader onImage={handleImageUpload} onClear={handleClearRef} compact />
            </div>
            <span style={{ fontSize: 11, color: 'var(--text-muted)', display: 'block', marginTop: 2 }}>{mh.hint}</span>
          </div>
        )}

        <div>
          <label style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 4, display: 'block' }}>尺寸</label>
          <AspectPicker aspects={IMAGE_PRESETS} value={aspect} onChange={handleAspectChange} />
          <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
            <input type="number" value={width} onChange={e => { setWidth(Number(e.target.value)); setAspect('custom') }}
              style={{ width: 80 }} min={256} max={2048} />
            <span style={{ lineHeight: '36px', color: 'var(--text-muted)' }}>×</span>
            <input type="number" value={height} onChange={e => { setHeight(Number(e.target.value)); setAspect('custom') }}
              style={{ width: 80 }} min={256} max={2048} />
          </div>
        </div>

        <details style={{ fontSize: 12 }}>
          <summary style={{ cursor: 'pointer', color: 'var(--text-soft)' }}>高级参数</summary>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginTop: 8 }}>
            <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
              <span style={{ width: 80, color: 'var(--text-muted)' }}>Seed</span>
              <input type="text" value={seed} onChange={e => setSeed(e.target.value)} placeholder="随机" style={{ flex: 1 }} />
            </div>
            <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
              <span style={{ width: 80, color: 'var(--text-muted)' }}>推理步数</span>
              <input type="text" value={steps} onChange={e => setSteps(e.target.value)} placeholder="默认" style={{ flex: 1 }} />
            </div>
            <div>
              <span style={{ color: 'var(--text-muted)', marginBottom: 4, display: 'block' }}>负向提示词</span>
              <textarea value={negPrompt} onChange={e => setNegPrompt(e.target.value)} rows={2}
                style={{ width: '100%', resize: 'vertical' }} />
            </div>
          </div>
        </details>

        <div style={{ display: 'flex', gap: 8 }}>
          <button onClick={handleGenerate} disabled={generating}
            className="btn btn-accent" style={{ flex: 1, padding: '8px 16px', fontSize: 13 }}>
            {generating ? <><Spinner size="sm" /> {stepLabel || '生成中…'}</> : '生成图像'}
          </button>
          {generating && (
            <button onClick={handleCancel} className="btn btn-subtle" style={{ padding: '8px 12px', fontSize: 13 }}>
              取消
            </button>
          )}
        </div>
        {error && <div style={{ color: 'var(--error)', fontSize: 12 }}>{error}</div>}
        {generating && stepLabel && (
          <div style={{ fontSize: 11, color: 'var(--accent-ink)', animation: 'pulse 1.5s ease-in-out infinite' }}>
            {stepLabel}
          </div>
        )}
      </div>

      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', padding: 16, overflow: 'auto' }}>
        {generating && (
          <StatusCard taskId="" status="in_progress" progress={null} note={stepLabel || '正在生成图像…'} onCancel={handleCancel} />
        )}
        {!resultUrl && !generating && (
          <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)' }}>
            <svg viewBox="0 0 24 24" width={32} height={32} fill="none" stroke="currentColor" strokeWidth="1.6">
              <rect x="3.5" y="4.5" width="17" height="15" rx="2.5" />
              <circle cx="8.5" cy="9.5" r="1.6" />
              <path d="m4 17 4.5-4.2a2 2 0 0 1 2.7 0L20 20.5" />
            </svg>
            <p style={{ marginTop: 8, fontSize: 13 }}>输入提示词并生成图像</p>
          </div>
        )}
        {resultUrl && (
          <div style={{ background: 'var(--surface)', borderRadius: 'var(--r-lg)', border: '1px solid var(--border)', padding: 16, overflow: 'hidden' }}>
            <img src={resultUrl} alt="生成结果"
              style={{ maxWidth: '100%', maxHeight: '60vh', borderRadius: 'var(--r)', display: 'block', margin: '0 auto' }} />
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 8 }}>
              <span style={{ fontSize: 12, color: 'var(--text-soft)' }}>
                尺寸: {resultDimensions.w}×{resultDimensions.h} · 格式: PNG
              </span>
              <button onClick={handleDownload} className="btn btn-accent" style={{ fontSize: 12, padding: '4px 12px' }}>
                下载
              </button>
            </div>
          </div>
        )}
        <HistoryStrip currentKind="image" onSelect={(h) => {
          if (h.prompt) setPrompt(h.prompt)
          if (h.ar && SIZE_MAP[h.ar]) { setAspect(h.ar); setWidth(SIZE_MAP[h.ar][0]); setHeight(SIZE_MAP[h.ar][1]) }
          if (h.model) setModel(h.model)
          if (h.url && isSafeMediaUrl(h.url)) { setResultUrl(h.url); setResultDimensions({ w: h.width, h: height }) }
        }} />
      </div>
    </div>
  )
}

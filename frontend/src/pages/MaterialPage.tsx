// ── 素材分析助手页面 ─────────────────────────────────────────
import { useState, useEffect } from 'react'
import { useKey } from '@/contexts/KeyContext'
import { useConfig } from '@/contexts/ConfigContext'
import { Spinner } from '@/components/common/Spinner'
import { showToast } from '@/components/common/Toast'
import { apiProxyPost } from '@/api/client'
import * as MaterialApi from '@/api/material'
import type { MaterialPrompt } from '@/api/types'

const DEFAULT_TEMPLATE = `你是一个专业的 AI 绘图 Prompt 工程师。请分析用户提供的素材，并生成适合 AI 图像生成的 Prompt。

要求：
1. 为每个素材生成 5 个不同风格的 Prompt
2. 每个 Prompt 包含：中文说明、正向提示词、负向提示词
3. 正向提示词用英文撰写，包含主体、动作、场景、光线、风格、渲染方式
4. 输出格式：

Prompt 001:
中文说明：...
Positive Prompt：...
Negative Prompt：...`

export function MaterialPage() {
  const { apiKey } = useKey()
  const { config } = useConfig()

  // Step 1: Template
  const [template, setTemplate] = useState(DEFAULT_TEMPLATE)
  const [genCount, setGenCount] = useState(10)

  // Step 3: Prompts
  const [prompts, setPrompts] = useState<MaterialPrompt[]>([])
  const [importedText, setImportedText] = useState('')

  // Step 4: Batch generation
  const [running, setRunning] = useState(false)
  const [batchResults, setBatchResults] = useState<Array<{ title: string; url: string }>>([])
  const [progress, setProgress] = useState<Array<{ title: string; status: string }>>([])
  const [loaded, setLoaded] = useState(false)

  useEffect(() => {
    ;(async () => {
      try {
        const cfg = await MaterialApi.loadMaterialConfig()
        if (cfg.prompt_template) setTemplate(cfg.prompt_template)
        if (cfg.default_generate_count) setGenCount(cfg.default_generate_count)
        const data = await MaterialApi.loadMaterialPrompts()
        if (data.prompts) setPrompts(data.prompts)
        if (data.imported_text) setImportedText(data.imported_text)
      } catch {}
      setLoaded(true)
    })()
  }, [])

  const handleSaveTemplate = async () => {
    try {
      await MaterialApi.saveMaterialConfig({
        prompt_template: template,
        default_generate_count: genCount,
        saved_template: template,
      } as any)
      showToast('✓ 模板已保存', 'success')
    } catch { showToast('保存失败', 'error') }
  }

  const handleCopy = () => {
    navigator.clipboard.writeText(template).then(() => showToast('✓ 已复制到剪贴板', 'success'))
      .catch(() => showToast('复制失败，请手动复制', 'error'))
  }

  const handleOpenChatGPT = () => window.open('https://chatgpt.com', '_blank')

  const handleParse = () => {
    if (!importedText.trim()) { showToast('请先粘贴 ChatGPT 输出', 'warning'); return }

    const parsed: MaterialPrompt[] = []
    const regex = /Prompt\s*0*(\d+)\s*[:\uFF1A]?\s*\n?([\s\S]*?)(?=(?:Prompt\s*0*\d+\s*[:\uFF1A]?\s*|$))/gi
    let m
    while ((m = regex.exec(importedText)) !== null) {
      const body = m[2].trim()
      let desc = '', pos = '', neg = ''
      const dm = body.match(/(?:Description|中文说明|说明)[\uFF1A:]\s*([^\n]*)/i)
      if (dm) desc = dm[1].trim()
      const pm = body.match(/(?:Positive Prompt|正向提示词|提示词)[\uFF1A:]\s*([\s\S]*?)(?=(?:\n\s*(?:Negative Prompt|负向提示词|Description|中文说明|$)))/i)
      if (pm) pos = pm[1].trim()
      const nm = body.match(/(?:Negative Prompt|负向提示词)[\uFF1A:]\s*([\s\S]*?)(?=(?:\n\s*(?:Positive Prompt|正向提示词|Description|中文说明|$)))/i)
      if (nm) neg = nm[1].trim()
      if (pos) parsed.push({
        id: 'mp_' + Date.now() + '_' + parsed.length,
        title: 'Prompt ' + String(parsed.length + 1).padStart(3, '0'),
        description: desc, positive_prompt: pos, negative_prompt: neg, selected: true,
      })
    }

    // Fallback: line-by-line
    if (parsed.length === 0) {
      let cp = '', cn = '', cd = ''
      importedText.split('\n').forEach(line => {
        const l = line.trim()
        if (!l) return
        const d = l.match(/^(?:Description|中文说明|说明)[\uFF1A:]\s*(.*)/i)
        const p = l.match(/^(?:Positive Prompt|正向提示词|提示词)[\uFF1A:]\s*(.*)/i)
        const n = l.match(/^(?:Negative Prompt|负向提示词)[\uFF1A:]\s*(.*)/i)
        if (d) cd = d[1].trim()
        else if (p) { if (cp) pushPrompt(); cp = p[1].trim() }
        else if (n) cn = n[1].trim()
        else if (cp) cp += ' ' + l
      })
      if (cp) pushPrompt()
      function pushPrompt() {
        parsed.push({
          id: 'mp_' + Date.now() + '_' + parsed.length,
          title: 'Prompt ' + String(parsed.length + 1).padStart(3, '0'),
          description: cd, positive_prompt: cp, negative_prompt: cn, selected: true,
        })
      }
    }

    if (parsed.length > 0) {
      setPrompts(parsed)
      showToast(`✓ 成功解析 ${parsed.length} 条 Prompt`, 'success')
    } else {
      showToast('未能识别出 Prompt 格式', 'warning')
    }
  }

  const handleClearPrompts = () => {
    setPrompts([])
    setImportedText('')
    MaterialApi.clearMaterialPrompts().catch(() => {})
  }

  const toggleAll = (checked: boolean) => {
    setPrompts(prev => prev.map(p => ({ ...p, selected: checked })))
  }

  const toggleOne = (idx: number) => {
    setPrompts(prev => prev.map((p, i) => i === idx ? { ...p, selected: !p.selected } : p))
  }

  const handleSavePrompts = () => {
    MaterialApi.saveMaterialPrompts({ imported_text: importedText, prompts } as any)
    showToast('✓ Prompt 列表已保存', 'success')
  }

  const handleStartBatch = async () => {
    if (!apiKey) { showToast('请先配置 API Key', 'error'); return }
    const selected = prompts.filter(p => p.selected)
    if (selected.length === 0) { showToast('请至少选择一条 Prompt', 'warning'); return }

    const toGen = selected.slice(0, genCount)
    setRunning(true)
    setBatchResults([])
    setProgress(toGen.map(p => ({ title: p.title || p.positive_prompt.slice(0, 30), status: 'waiting' })))

    let done = 0, failed = 0
    for (let i = 0; i < toGen.length; i++) {
      setProgress(prev => { const n = [...prev]; n[i] = { ...n[i], status: 'generating' }; return n })
      const model = config.imageModel || 'agnes-image-2.1-flash'
      try {
        const body = { model, prompt: toGen[i].positive_prompt, size: '1024x1024', width: 1024, height: 1024, n: 1 }
        if (toGen[i].negative_prompt) (body as any).negative_prompt = toGen[i].negative_prompt
        const res = await apiProxyPost('/v1/images/generations', body, apiKey)
        const data = await res.json()
        if (!res.ok) throw new Error(data.error?.message || `HTTP ${res.status}`)
        const url = data.data?.[0]?.b64_json ? `data:image/png;base64,${data.data[0].b64_json}` : data.data?.[0]?.url
        setBatchResults(prev => [...prev, { title: toGen[i].title || String(i), url: url || '' }])
        setProgress(prev => { const n = [...prev]; n[i] = { ...n[i], status: 'done' }; return n })
        done++
      } catch {
        setProgress(prev => { const n = [...prev]; n[i] = { ...n[i], status: 'failed' }; return n })
        failed++
      }
    }

    setRunning(false)
    showToast(`${done} 张成功，${failed} 张失败`, failed > 0 ? 'warning' : 'success')
  }

  const handleDownloadZip = async () => {
    if (batchResults.length === 0) return
    try {
      const files: Array<{ name: string; data: Uint8Array }> = []
      for (const item of batchResults) {
        try {
          const res = await fetch(item.url)
          const blob = await res.blob()
          const ab = await blob.arrayBuffer()
          const ext = blob.type === 'image/png' ? '.png' : '.jpg'
          const safe = (item.title || 'img').replace(/[^a-zA-Z0-9_\u4e00-\u9fff-]/g, '_')
          files.push({ name: safe + ext, data: new Uint8Array(ab) })
        } catch {}
      }
      const zipBlob = makeZipBlob(files)
      const url = URL.createObjectURL(zipBlob)
      const a = document.createElement('a')
      a.href = url
      a.download = 'agnes-material-' + Date.now() + '.zip'
      document.body.appendChild(a); a.click(); document.body.removeChild(a)
      setTimeout(() => URL.revokeObjectURL(url), 10000)
    } catch { showToast('ZIP 下载失败', 'error') }
  }

  return (
    <div style={{ display: 'flex', gap: 16, padding: 16, height: '100%', overflow: 'auto' }}>
      <div style={{ flex: '0 0 420px', display: 'flex', flexDirection: 'column', gap: 16 }}>
        {/* Step 1: Template */}
        <div className="card" style={{ padding: 16, borderRadius: 'var(--r-lg)', background: 'var(--surface)', border: '1px solid var(--border)' }}>
          <h3 style={{ fontSize: 13, fontWeight: 600, marginBottom: 8 }}>Step 1：编辑提示词模板</h3>
          <textarea value={template} onChange={e => setTemplate(e.target.value)} rows={10}
            style={{ width: '100%', resize: 'vertical', fontSize: 12, fontFamily: 'var(--font-mono)' }} />
          <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
            <button onClick={handleSaveTemplate} className="btn btn-accent" style={{ fontSize: 11, padding: '4px 10px' }}>保存</button>
            <button onClick={() => setTemplate(DEFAULT_TEMPLATE)} className="btn btn-subtle" style={{ fontSize: 11, padding: '4px 10px' }}>重置</button>
          </div>
        </div>

        {/* Step 2: Copy to ChatGPT */}
        <div className="card" style={{ padding: 16, borderRadius: 'var(--r-lg)', background: 'var(--surface)', border: '1px solid var(--border)' }}>
          <h3 style={{ fontSize: 13, fontWeight: 600, marginBottom: 8 }}>Step 2：复制到 ChatGPT</h3>
          <p style={{ fontSize: 12, color: 'var(--text-soft)', marginBottom: 8 }}>复制提示词 → 打开 ChatGPT 网页版 → 粘贴 → 上传素材 → 复制分析结果</p>
          <div style={{ display: 'flex', gap: 8 }}>
            <button onClick={handleCopy} className="btn btn-accent" style={{ fontSize: 11, padding: '4px 10px' }}>📋 复制提示词</button>
            <button onClick={handleOpenChatGPT} className="btn btn-subtle" style={{ fontSize: 11, padding: '4px 10px' }}>打开 ChatGPT ↗</button>
          </div>
        </div>

        {/* Step 3: Parse prompts */}
        <div className="card" style={{ padding: 16, borderRadius: 'var(--r-lg)', background: 'var(--surface)', border: '1px solid var(--border)' }}>
          <h3 style={{ fontSize: 13, fontWeight: 600, marginBottom: 8 }}>Step 3：粘贴回并解析</h3>
          <textarea value={importedText} onChange={e => setImportedText(e.target.value)}
            placeholder="在此粘贴 ChatGPT 输出的 Prompt 结果…"
            rows={6} style={{ width: '100%', resize: 'vertical', fontSize: 11, fontFamily: 'var(--font-mono)' }} />
          <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
            <button onClick={handleParse} className="btn btn-accent" style={{ fontSize: 11, padding: '4px 10px' }}>🔍 解析 Prompt</button>
            <button onClick={handleClearPrompts} className="btn btn-subtle" style={{ fontSize: 11, padding: '4px 10px' }}>清空</button>
          </div>
        </div>
      </div>

      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 16, overflow: 'auto' }}>
        {/* Prompt list */}
        {prompts.length > 0 && (
          <div className="card" style={{ padding: 16, borderRadius: 'var(--r-lg)', background: 'var(--surface)', border: '1px solid var(--border)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8, flexWrap: 'wrap', gap: 6 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <input type="checkbox" checked={prompts.every(p => p.selected)} onChange={e => toggleAll(e.target.checked)} />
                <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                  {prompts.filter(p => p.selected).length}/{prompts.length} 条
                </span>
              </div>
              <button onClick={handleSavePrompts} className="btn btn-subtle" style={{ fontSize: 11, padding: '2px 8px' }}>保存</button>
            </div>

            {prompts.map((p, i) => (
              <div key={p.id} style={{ padding: 8, borderBottom: '1px solid var(--border-soft)', fontSize: 12 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                  <input type="checkbox" checked={p.selected} onChange={() => toggleOne(i)} />
                  <span style={{ fontWeight: 600, fontSize: 11 }}>{p.title}</span>
                </div>
                {p.description && <div style={{ color: 'var(--text-muted)', fontSize: 11 }}>📝 {p.description}</div>}
                <div style={{ color: 'var(--text-soft)', fontSize: 11, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {p.positive_prompt?.slice(0, 100)}…
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Step 4: Batch generation */}
        <div className="card" style={{ padding: 16, borderRadius: 'var(--r-lg)', background: 'var(--surface)', border: '1px solid var(--border)' }}>
          <h3 style={{ fontSize: 13, fontWeight: 600, marginBottom: 8 }}>Step 4：批量生图</h3>
          <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
            <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>生成数量:</span>
            <input type="number" value={genCount} onChange={e => setGenCount(parseInt(e.target.value) || 1)}
              min={1} max={100} style={{ width: 60, fontSize: 12 }} />
            <button onClick={handleStartBatch} disabled={running || prompts.length === 0}
              className="btn btn-accent" style={{ fontSize: 12, padding: '4px 12px' }}>
              {running ? <Spinner size="sm" /> : '批量生成'}
            </button>
            {batchResults.length > 0 && (
              <button onClick={handleDownloadZip} className="btn btn-subtle" style={{ fontSize: 12, padding: '4px 12px' }}>
                📦 下载 ZIP
              </button>
            )}
          </div>

          {/* Progress */}
          {progress.length > 0 && (
            <div style={{ marginTop: 8, display: 'flex', flexDirection: 'column', gap: 4 }}>
              {progress.map((p, i) => (
                <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 11 }}>
                  <span style={{
                    width: 6, height: 6, borderRadius: '50%', display: 'inline-block',
                    background: p.status === 'done' ? 'var(--success)' : p.status === 'failed' ? 'var(--error)' : p.status === 'generating' ? 'var(--accent)' : 'var(--surface-3)',
                  }} />
                  <span style={{ color: 'var(--text-soft)' }}>{p.title}</span>
                  <span style={{ color: 'var(--text-muted)' }}>
                    {p.status === 'done' ? '✓' : p.status === 'failed' ? '✗' : p.status === 'generating' ? '生成中…' : '等待'}
                  </span>
                </div>
              ))}
            </div>
          )}

          {/* Results */}
          {batchResults.length > 0 && (
            <div style={{ marginTop: 12, display: 'flex', flexDirection: 'column', gap: 8 }}>
              {batchResults.map((r, i) => (
                <div key={i} style={{ display: 'flex', gap: 8, padding: 8, borderRadius: 'var(--r-sm)', background: 'var(--surface-2)', alignItems: 'center' }}>
                  {r.url && <img src={r.url} alt="" style={{ width: 48, height: 48, borderRadius: 4, objectFit: 'cover' }} />}
                  <span style={{ fontSize: 11, color: 'var(--text-soft)', flex: 1 }}>{r.title}</span>
                  {r.url && (
                    <a href={r.url} download className="btn btn-ghost btn-sm" style={{ fontSize: 10, padding: '2px 6px' }}>下载</a>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

function makeZipBlob(files: Array<{ name: string; data: Uint8Array }>): Blob {
  function c32(d: Uint8Array) {
    let c = 0xffffffff
    for (let i = 0; i < d.length; i++) { c ^= d[i]; for (let j = 0; j < 8; j++) c = (c >>> 1) ^ (c & 1 ? 0xedb88320 : 0) }
    return ~c >>> 0
  }
  function s8(s: string) { return new TextEncoder().encode(s) }
  function u32(v: number) { return new Uint8Array([v & 255, v >> 8 & 255, v >> 16 & 255, v >> 24 & 255]) }
  function u16(v: number) { return new Uint8Array([v & 255, v >> 8 & 255]) }

  const hd: Uint8Array[] = []
  const cd: Uint8Array[] = []
  let off = 0

  for (const f of files) {
    const n = s8(f.name)
    const d = f.data
    const c = c32(d)
    const s = d.length
    const lh = new Uint8Array(30 + n.length)
    lh.set([80, 75, 3, 4], 0)
    lh.set(u16(20), 4)
    lh.set(u32(c), 14)
    lh.set(u32(s), 18)
    lh.set(u32(s), 22)
    lh.set(u16(n.length), 26)
    lh.set(n, 30)
    hd.push(lh, d)
    off += lh.length + s

    const ce = new Uint8Array(46 + n.length)
    ce.set([80, 75, 1, 2], 0)
    ce.set(u16(20), 10)
    ce.set(u16(20), 12)
    ce.set(u32(c), 20)
    ce.set(u32(s), 24)
    ce.set(u32(s), 28)
    ce.set(u16(n.length), 30)
    ce.set(n, 46)
    cd.push(ce)
  }

  let cl = 0
  for (const c of cd) { hd.push(c); cl += c.length }

  const eo = new Uint8Array(22)
  eo.set([80, 75, 5, 6], 0)
  eo.set(u16(cd.length), 8)
  eo.set(u16(cd.length), 10)
  eo.set(u32(cl), 12)
  eo.set(u32(off), 16)
  hd.push(eo)

  return new Blob(hd as BlobPart[], { type: 'application/zip' })
}

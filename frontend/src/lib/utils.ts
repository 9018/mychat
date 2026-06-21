// ── 工具函数 ──────────────────────────────────────────────────

export function isSafeMediaUrl(value: string | null | undefined): boolean {
  if (!value || typeof value !== 'string') return false
  const trimmed = value.trim()
  if (!trimmed) return false
  if (trimmed.startsWith('/outputs/')) return true
  if (/^data:image\/(png|jpe?g|webp|gif);base64,/i.test(trimmed)) return true
  if (trimmed.startsWith('/video-proxy?')) return true
  try {
    const url = new URL(trimmed, window.location.origin)
    return ['http:', 'https:', 'blob:'].includes(url.protocol)
  } catch {
    return false
  }
}

export function truncatePrompt(str: string, len = 12): string {
  if (!str) return ''
  if (str.length <= len) return str
  return str.slice(0, len - 1) + '…'
}

export function getBaseUrl(): string {
  return ''
}

export function escapeHtml(s: string): string {
  return String(s).replace(/[&<>"']/g, c => {
    const m: Record<string, string> = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }
    return m[c] || c
  })
}

export function guessModelType(id: string): string {
  const lower = String(id).toLowerCase()
  if (lower.includes('video')) return 'video'
  if (lower.includes('image') || lower.includes('flash') || lower.includes('dall') || lower.includes('sd')) return 'image'
  if (lower.includes('embed')) return 'other'
  if (lower.includes('chat') || lower.includes('text') || lower.includes('gpt') || lower.includes('llama')
    || lower.includes('claude') || lower.includes('qwen') || lower.includes('mistral') || lower.includes('gemini')
    || lower.includes('deepseek') || lower.includes('agnes-1') || lower.includes('agnes-2') || lower.includes('agnes-3')) return 'chat'
  return 'other'
}

export function isHttpUrl(s: string): boolean {
  return /^https?:\/\//i.test(s)
}

export function isDataImageUrl(s: string): boolean {
  return /^data:image\//i.test(s)
}

export function stripDataImagePrefix(s: string): string {
  // data:image/png;base64,ABC123 → ABC123
  return s.replace(/^data:image\/[a-z0-9]+;base64,/i, '').replace(/\s+/g, '')
}

export function normalizeImageInput(value: string, mode: 'base64' | 'url-or-base64' = 'url-or-base64'): string {
  if (!value) return value
  const raw = String(value).trim()
  if (mode === 'url-or-base64') {
    if (isHttpUrl(raw)) return raw
    if (isDataImageUrl(raw)) return stripDataImagePrefix(raw)
    // Treat as pure base64 — ensure padding
    let data = raw.replace(/\s+/g, '')
    const pad = (4 - (data.length % 4)) % 4
    if (pad > 0) data += '='.repeat(pad)
    return data
  }
  // mode: 'base64' — strip data URI prefix
  if (isDataImageUrl(raw)) return stripDataImagePrefix(raw)
  return raw // HTTP URL or already-pure base64
}

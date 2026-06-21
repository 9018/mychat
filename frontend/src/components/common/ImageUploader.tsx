// ── 图片上传组件（点击/粘贴/拖放） ──────────────────────────
import { useRef, useState, useCallback } from 'react'

interface ImageUploaderProps {
  onImage: (dataUrl: string, width: number, height: number, filename: string) => void
  onClear?: () => void
  compact?: boolean
}

export function ImageUploader({ onImage, onClear, compact }: ImageUploaderProps) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [preview, setPreview] = useState<string | null>(null)
  const [filename, setFilename] = useState('')

  const processFile = useCallback((file: File) => {
    if (!file.type.startsWith('image/')) return
    const reader = new FileReader()
    reader.onload = (e) => {
      const dataUrl = e.target?.result as string
      const img = new Image()
      img.onload = () => {
        setPreview(dataUrl)
        setFilename(file.name)
        onImage(dataUrl, img.naturalWidth, img.naturalHeight, file.name)
      }
      img.src = dataUrl
    }
    reader.readAsDataURL(file)
  }, [onImage])

  const handleClick = () => inputRef.current?.click()
  const handlePaste = useCallback((e: React.ClipboardEvent) => {
    const items = e.clipboardData?.items
    if (!items) return
    for (let i = 0; i < items.length; i++) {
      if (items[i].kind === 'file' && items[i].type.startsWith('image/')) {
        const file = items[i].getAsFile()
        if (file) { processFile(file); e.preventDefault(); break }
      }
    }
  }, [processFile])

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    const files = e.dataTransfer.files
    if (files.length > 0 && files[0].type.startsWith('image/')) {
      processFile(files[0])
    }
  }, [processFile])

  const handleClear = () => {
    setPreview(null)
    setFilename('')
    if (inputRef.current) inputRef.current.value = ''
    onClear?.()
  }

  return (
    <div onPaste={handlePaste} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
      <input ref={inputRef} type="file" accept="image/*" style={{ display: 'none' }}
        onChange={e => { const f = e.target.files?.[0]; if (f) processFile(f) }} />
      <button type="button" onClick={handleClick}
        onDragOver={e => e.preventDefault()}
        onDrop={handleDrop}
        style={{
          padding: compact ? '4px 8px' : '8px 12px', borderRadius: 'var(--r-sm)',
          border: '1px dashed var(--border)', background: 'var(--surface)',
          color: 'var(--text-soft)', cursor: 'pointer', fontSize: 12,
        }}>
        选择 / 粘贴 / 拖入图片
      </button>
      {preview && (
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <img src={preview} alt="" style={{ height: 32, borderRadius: 4 }} />
          <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>{filename}</span>
          <button type="button" onClick={handleClear} style={{
            border: 'none', background: 'var(--surface-2)', borderRadius: '50%',
            width: 18, height: 18, fontSize: 12, cursor: 'pointer', lineHeight: '18px',
            textAlign: 'center',
          }}>×</button>
        </div>
      )}
    </div>
  )
}

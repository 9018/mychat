import { useHistory } from '@/contexts/HistoryContext'
import { isSafeMediaUrl, truncatePrompt } from '@/lib/utils'

interface HistoryStripProps {
  currentKind: 'video' | 'image'
  onSelect: (item: any) => void
}

export function HistoryStrip({ currentKind, onSelect }: HistoryStripProps) {
  const { items, removeItem } = useHistory()
  const filtered = items.filter(h => h.kind === currentKind)

  if (filtered.length === 0) return null

  return (
    <div style={{ display: 'flex', gap: 8, overflowX: 'auto', padding: '8px 0' }}>
      {filtered.slice(0, 8).map(h => {
        const mediaUrl = h.url && isSafeMediaUrl(h.url) ? h.url : null
        const tone = parseInt(String(h.tone)) || 292

        return (
          <div key={h.id} onClick={() => onSelect(h)}
            style={{
              flexShrink: 0, width: 80, borderRadius: 'var(--r-sm)',
              overflow: 'hidden', cursor: 'pointer', position: 'relative',
              background: mediaUrl ? 'none' : `radial-gradient(120% 120% at 30% 20%, oklch(0.5 0.15 ${tone}), oklch(0.28 0.09 ${tone + 40}) 70%)`,
              border: '1px solid var(--border)',
            }}>
            {mediaUrl && h.kind === 'video' ? (
              <video src={mediaUrl} preload="metadata" muted playsInline
                style={{ width: 80, height: 60, objectFit: 'cover', display: 'block' }} />
            ) : mediaUrl ? (
              <div style={{ width: 80, height: 60, backgroundImage: `url(${mediaUrl})`, backgroundSize: 'cover', backgroundPosition: 'center' }} />
            ) : (
              <div style={{ width: 80, height: 60 }} />
            )}
            <div style={{ padding: '2px 4px', fontSize: 10, color: 'var(--text)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
              {truncatePrompt(h.title || h.prompt || '', 12)}
            </div>
            <button onClick={(e) => { e.stopPropagation(); removeItem(h.id) }}
              style={{
                position: 'absolute', top: 2, right: 2, width: 16, height: 16,
                borderRadius: '50%', border: 'none', background: 'rgba(0,0,0,0.5)',
                color: '#fff', fontSize: 10, lineHeight: '16px', textAlign: 'center',
                cursor: 'pointer', zIndex: 2,
              }}>×</button>
          </div>
        )
      })}
    </div>
  )
}

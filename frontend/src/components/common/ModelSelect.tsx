// ── 模型下拉选择器 ─────────────────────────────────────────────
import { useConfig } from '@/contexts/ConfigContext'

interface ModelSelectProps {
  type: 'video' | 'image' | 'chat'
  value: string
  onChange: (id: string) => void
  id?: string
}

export function ModelSelect({ type, value, onChange, id }: ModelSelectProps) {
  const { config } = useConfig()
  const models = (config.modelList || [])
    .filter(m => m.enabled && m.types?.includes(type) && m.id)
    .map(m => m.id)

  if (models.length === 0) {
    return (
      <select disabled style={{ opacity: 0.5 }}>
        <option>(无可用模型)</option>
      </select>
    )
  }

  return (
    <select
      id={id}
      value={value}
      onChange={e => onChange(e.target.value)}
      style={{ maxWidth: 240 }}
    >
      {models.map(mid => (
        <option key={mid} value={mid}>{mid}</option>
      ))}
    </select>
  )
}

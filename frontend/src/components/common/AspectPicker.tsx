// ── 宽高比选择器 ──────────────────────────────────────────────
import { useState } from 'react'

export interface Aspect {
  id: string
  label: string
  w: number
  h: number
}

interface AspectPickerProps {
  aspects: Aspect[]
  value: string
  onChange: (id: string) => void
}

export function AspectPicker({ aspects, value, onChange }: AspectPickerProps) {
  return (
    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
      {aspects.map(a => (
        <button
          key={a.id}
          type="button"
          onClick={() => onChange(a.id)}
          style={{
            display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4,
            padding: '6px 8px', borderRadius: 'var(--r-sm)', cursor: 'pointer',
            border: value === a.id ? '1.5px solid var(--accent)' : '1px solid var(--border)',
            background: value === a.id ? 'var(--accent-soft)' : 'var(--surface)',
            color: 'var(--text)', transition: 'all 0.15s',
          }}
        >
          <div style={{
            width: a.w, height: a.h,
            border: '1.5px solid currentColor', opacity: 0.7,
            borderRadius: 1,
          }} />
          <span style={{ fontSize: 10, fontWeight: 600 }}>{a.label}</span>
        </button>
      ))}
    </div>
  )
}

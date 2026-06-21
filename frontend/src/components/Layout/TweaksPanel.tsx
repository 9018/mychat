// ── 浮动外观面板 ──────────────────────────────────────────────
import { useTweaks } from '@/contexts/TweaksContext'

const ACCENTS: Record<string, string> = {
  violet: '#8b6fff', indigo: '#6f7bff', cyan: '#1fb6c9',
  emerald: '#1fa86a', amber: '#d99413', rose: '#e0556a',
}
const ACCENT_LABEL: Record<string, string> = {
  violet: '紫', indigo: '靛', cyan: '青',
  emerald: '翠', amber: '琥', rose: '玫',
}
const DENSITIES = ['compact', 'regular', 'comfy'] as const

export function TweaksPanel() {
  const { tweaks, setTweaks } = useTweaks()

  return (
    <div className="twk-panel" style={{ display: 'flex' }}>
      <div className="twk-hd" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '8px 12px' }}>
        <b style={{ fontSize: 12 }}>外观</b>
      </div>
      <div className="twk-body" style={{ padding: '0 12px 12px', display: 'flex', flexDirection: 'column', gap: 10 }}>
        {/* Theme */}
        <div className="twk-row">
          <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>主题</span>
          <div style={{ display: 'flex', gap: 4 }}>
            <button onClick={() => setTweaks({ theme: 'dark' })}
              style={{
                flex: 1, padding: '4px 0', borderRadius: 6, fontSize: 11, cursor: 'pointer',
                border: tweaks.theme === 'dark' ? '1px solid var(--accent)' : '1px solid transparent',
                background: tweaks.theme === 'dark' ? 'var(--accent-soft)' : 'var(--surface-2)',
                color: 'var(--text)',
              }}>暗色</button>
            <button onClick={() => setTweaks({ theme: 'light' })}
              style={{
                flex: 1, padding: '4px 0', borderRadius: 6, fontSize: 11, cursor: 'pointer',
                border: tweaks.theme === 'light' ? '1px solid var(--accent)' : '1px solid transparent',
                background: tweaks.theme === 'light' ? 'var(--accent-soft)' : 'var(--surface-2)',
                color: 'var(--text)',
              }}>亮色</button>
          </div>
        </div>

        {/* Density */}
        <div className="twk-row">
          <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>密度</span>
          <div style={{ display: 'flex', gap: 4 }}>
            {DENSITIES.map(d => (
              <button key={d} onClick={() => setTweaks({ density: d })}
                style={{
                  flex: 1, padding: '4px 0', borderRadius: 6, fontSize: 11, cursor: 'pointer',
                  border: tweaks.density === d ? '1px solid var(--accent)' : '1px solid transparent',
                  background: tweaks.density === d ? 'var(--accent-soft)' : 'var(--surface-2)',
                  color: 'var(--text)',
                }}>
                {d === 'compact' ? '紧凑' : d === 'regular' ? '常规' : '舒适'}
              </button>
            ))}
          </div>
        </div>

        {/* Scale */}
        <div className="twk-row">
          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>缩放</span>
            <span style={{ fontSize: 11, color: 'var(--text-soft)' }}>{tweaks.uiScale}%</span>
          </div>
          <input type="range" min={80} max={120} step={5} value={tweaks.uiScale}
            onChange={e => setTweaks({ uiScale: Number(e.target.value) })}
            style={{ width: '100%' }} />
        </div>

        {/* Accent color */}
        <div className="twk-row">
          <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>强调色</span>
          <div style={{ display: 'flex', gap: 6 }}>
            {Object.entries(ACCENTS).map(([key, color]) => (
              <button key={key} onClick={() => setTweaks({ accent: key })}
                title={ACCENT_LABEL[key]}
                style={{
                  width: 28, height: 28, borderRadius: '50%', border: 'none', cursor: 'pointer',
                  background: color,
                  outline: tweaks.accent === key ? '2px solid var(--accent)' : 'none',
                  outlineOffset: 2,
                }}>
                {tweaks.accent === key && (
                  <svg viewBox="0 0 14 14" style={{ width: 14, height: 14 }}>
                    <path d="M3 7.2 L5.8 10 L11 4.2" fill="none" stroke={key === 'amber' ? '#000' : '#fff'}
                      strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                )}
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}

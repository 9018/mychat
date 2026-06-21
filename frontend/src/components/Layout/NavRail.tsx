// ── 左侧导航栏 ────────────────────────────────────────────────
import type { TabType } from '@/api/types'

interface NavRailProps {
  activeTab: TabType
  onTabChange: (tab: TabType) => void
  onTweaksToggle: () => void
  isKeyReady: boolean
}

const TABS: Array<{ id: TabType; icon: string; label: string }> = [
  { id: 'video', icon: '▶', label: '视频' },
  { id: 'image', icon: '🖼', label: '图像' },
  { id: 'chat', icon: '💬', label: '聊天' },
  { id: 'material', icon: '📦', label: '素材' },
  { id: 'admin', icon: '⚙', label: '管理' },
]

export function NavRail({ activeTab, onTabChange, onTweaksToggle, isKeyReady }: NavRailProps) {
  return (
    <nav className="nav-rail" style={{
      width: 56, display: 'flex', flexDirection: 'column', alignItems: 'center',
      padding: '8px 0', gap: 4, background: 'var(--rail)', flexShrink: 0,
      borderRight: '1px solid var(--border)',
    }}>
      {TABS.map(tab => (
        <button key={tab.id}
          onClick={() => onTabChange(tab.id)}
          className={`nav-btn${activeTab === tab.id ? ' active' : ''}`}
          title={tab.label}
          style={{
            width: 42, height: 42, borderRadius: 'var(--r)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            border: 'none', background: activeTab === tab.id ? 'var(--surface-2)' : 'transparent',
            color: activeTab === tab.id ? 'var(--accent-ink)' : 'var(--text-muted)',
            fontSize: 18, cursor: 'pointer', transition: 'all 0.15s',
          }}
        >
          {tab.icon}
        </button>
      ))}
      <div style={{ flex: 1 }} />
      <div style={{ width: 42, height: 42, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <span className={`api-pill ${isKeyReady ? 'ok' : 'warn'}`}
          style={{ width: 8, height: 8, borderRadius: '50%', display: 'block', background: isKeyReady ? 'var(--success)' : 'var(--warning)' }}
        />
      </div>
      <button
        id="navTweaks"
        onClick={onTweaksToggle}
        className="nav-btn"
        title="外观"
        style={{
          width: 42, height: 42, borderRadius: 'var(--r)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          border: 'none', background: 'transparent',
          color: 'var(--text-muted)', fontSize: 16, cursor: 'pointer',
        }}
      >
        ◐
      </button>
    </nav>
  )
}

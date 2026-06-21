// ── 移动端底部导航栏 ────────────────────────────────────────
import type { TabType } from '@/api/types'

interface MobileNavProps {
  activeTab: TabType
  onTabChange: (tab: TabType) => void
  isKeyReady: boolean
  onTweaksToggle: () => void
}

const TABS: Array<{ id: TabType; icon: string; label: string }> = [
  { id: 'video', icon: '▶', label: '视频' },
  { id: 'image', icon: '🖼', label: '图像' },
  { id: 'chat', icon: '💬', label: '聊天' },
  { id: 'material', icon: '📦', label: '素材' },
  { id: 'admin', icon: '⚙', label: '管理' },
]

export function MobileNav({ activeTab, onTabChange, isKeyReady, onTweaksToggle }: MobileNavProps) {
  return (
    <nav className="mobile-nav" style={{
      position: 'fixed', bottom: 0, left: 0, right: 0, zIndex: 100,
      display: 'flex', alignItems: 'center', justifyContent: 'space-around',
      height: 56, background: 'var(--rail)',
      borderTop: '1px solid var(--border)',
      paddingBottom: 'env(safe-area-inset-bottom, 0)',
    }}>
      {TABS.map(tab => (
        <button key={tab.id}
          onClick={() => onTabChange(tab.id)}
          style={{
            display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 2,
            padding: '4px 8px', border: 'none', background: 'transparent',
            color: activeTab === tab.id ? 'var(--accent-ink)' : 'var(--text-muted)',
            fontSize: 10, cursor: 'pointer', position: 'relative', minWidth: 48,
          }}
        >
          <span style={{ fontSize: 20, lineHeight: 1.2 }}>{tab.icon}</span>
          <span style={{ fontWeight: activeTab === tab.id ? 600 : 400 }}>{tab.label}</span>
          {tab.id === 'admin' && (
            <span style={{
              position: 'absolute', top: 2, right: 4, width: 6, height: 6,
              borderRadius: '50%', background: isKeyReady ? 'var(--success)' : 'var(--warning)',
            }} />
          )}
        </button>
      ))}
      <button onClick={onTweaksToggle} style={{
        display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 2,
        padding: '4px 8px', border: 'none', background: 'transparent',
        color: 'var(--text-muted)', fontSize: 10, cursor: 'pointer', minWidth: 48,
      }}>
        <span style={{ fontSize: 20, lineHeight: 1.2 }}>◐</span>
        <span>外观</span>
      </button>
    </nav>
  )
}

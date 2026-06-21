// ── 顶部栏 ────────────────────────────────────────────────────
import type { TabType, VideoMode, ImgMode } from '@/api/types'

interface TopBarProps {
  activeTab: TabType
  videoMode: VideoMode
  imgMode: ImgMode
  onVideoModeChange: (mode: VideoMode) => void
  onImgModeChange: (mode: ImgMode) => void
  currentSection: string
}

const TOPBAR_MAP: Record<string, { title: string; sub: string }> = {
  video: { title: '视频生成', sub: 'Text-to-Video · Image-to-Video · 关键帧动画' },
  image: { title: '图像生成', sub: 'Text-to-Image · Image-to-Image · 构图保留 · 高密度优化' },
  chat: { title: '对话', sub: '多模型流式 SSE 对话' },
  admin: { title: '管理', sub: 'API 令牌 · 模型配置' },
  material: { title: '素材分析助手', sub: 'ChatGPT 联动工作流 · 批量生图' },
}

const VIDEO_MODES: Array<{ id: VideoMode; label: string }> = [
  { id: 'text', label: '文生视频' },
  { id: 'image', label: '图生视频' },
  { id: 'multi', label: '多图视频' },
  { id: 'keyframe', label: '关键帧' },
]

const IMG_MODES: Array<{ id: ImgMode; label: string }> = [
  { id: 'txt2img', label: '文生图' },
  { id: 'img2img', label: '图生图' },
  { id: 'composition', label: '构图保留' },
  { id: 'high_density', label: '高密度' },
]

export function TopBar({ activeTab, videoMode, imgMode, onVideoModeChange, onImgModeChange }: TopBarProps) {
  const info = TOPBAR_MAP[activeTab] || { title: '', sub: '' }

  return (
    <div className="topbar" style={{
      display: 'flex', alignItems: 'center', height: 48, padding: '0 16px',
      borderBottom: '1px solid var(--border)', background: 'var(--bg)', flexShrink: 0, gap: 16,
    }}>
      {/* Title */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 0, flexShrink: 0 }}>
        <span style={{ fontSize: 14, fontWeight: 600, color: 'var(--text)' }}>{info.title}</span>
        <span style={{ fontSize: 10, color: 'var(--text-muted)' }}>{info.sub}</span>
      </div>

      {/* Video mode tabs */}
      {activeTab === 'video' && (
        <div style={{ display: 'flex', gap: 2, marginLeft: 'auto' }}>
          {VIDEO_MODES.map(m => (
            <button key={m.id} onClick={() => onVideoModeChange(m.id)}
              className={`tab${videoMode === m.id ? ' active' : ''}`}
              style={{
                padding: '4px 12px', borderRadius: 'var(--r-sm)', fontSize: 12,
                border: 'none', cursor: 'pointer', fontWeight: 500,
                background: videoMode === m.id ? 'var(--surface-2)' : 'transparent',
                color: videoMode === m.id ? 'var(--accent-ink)' : 'var(--text-soft)',
              }}>
              {m.label}
            </button>
          ))}
        </div>
      )}

      {/* Image mode tabs */}
      {activeTab === 'image' && (
        <div style={{ display: 'flex', gap: 2, marginLeft: 'auto' }}>
          {IMG_MODES.map(m => (
            <button key={m.id} onClick={() => onImgModeChange(m.id)}
              className={`tab${imgMode === m.id ? ' active' : ''}`}
              style={{
                padding: '4px 12px', borderRadius: 'var(--r-sm)', fontSize: 12,
                border: 'none', cursor: 'pointer', fontWeight: 500,
                background: imgMode === m.id ? 'var(--surface-2)' : 'transparent',
                color: imgMode === m.id ? 'var(--accent-ink)' : 'var(--text-soft)',
              }}>
              {m.label}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

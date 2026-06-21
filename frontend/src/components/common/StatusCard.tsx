// ── 进度状态卡片 ──────────────────────────────────────────────
interface StatusCardProps {
  taskId: string
  status: string
  progress: number | null
  note: string
  onCancel?: () => void
}

const STATUS_META: Record<string, { label: string; cls: string; pulse: boolean }> = {
  queued: { label: '排队等待', cls: 'badge-queued', pulse: false },
  in_progress: { label: '生成中', cls: 'badge-in_progress', pulse: true },
  completed: { label: '已完成', cls: 'badge-completed', pulse: false },
  failed: { label: '失败', cls: 'badge-failed', pulse: false },
}

export function StatusCard({ taskId, status, progress, note, onCancel }: StatusCardProps) {
  const meta = STATUS_META[status] || { label: status || '等待中', cls: '', pulse: false }
  const pct = progress != null ? Math.min(100, Math.max(0, progress)) : 0
  const isFinal = status === 'completed' || status === 'failed'

  return (
    <div className="status-card visible" style={{ display: 'block', padding: 20, borderRadius: 'var(--r-lg)', background: 'var(--surface)', border: '1px solid var(--border)', marginBottom: 16 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 12 }}>
        <span className={`status-dot${meta.pulse ? ' pulse' : ''}`} style={{
          width: 8, height: 8, borderRadius: '50%',
          background: status === 'completed' ? 'var(--success)' : status === 'failed' ? 'var(--error)' : 'var(--accent)',
        }} />
        <span className={`status-badge ${meta.cls}`} style={{ fontSize: 12, fontWeight: 600 }}>{meta.label}</span>
        {taskId && <span style={{ fontSize: 11, color: 'var(--text-muted)', marginLeft: 'auto' }}>ID: {taskId.slice(0, 12)}…</span>}
      </div>

      <div style={{ height: 6, background: 'var(--surface-2)', borderRadius: 99, overflow: 'hidden', marginBottom: 8 }}>
        <div style={{
          width: `${isFinal ? 100 : pct}%`, height: '100%',
          background: isFinal ? 'var(--success)' : 'var(--accent)',
          borderRadius: 99, transition: 'width 0.5s ease',
          opacity: status === 'failed' ? 0.3 : 1,
        }} />
      </div>

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span style={{ fontSize: 13, color: 'var(--text-soft)' }}>{isFinal ? '100%' : `${pct}%`}</span>
        {!isFinal && onCancel && (
          <button onClick={onCancel} style={{
            fontSize: 11, color: 'var(--text-muted)', background: 'var(--surface-2)',
            border: '1px solid var(--border)', borderRadius: 'var(--r-sm)', padding: '4px 10px',
            cursor: 'pointer',
          }}>取消任务</button>
        )}
      </div>

      {note && <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 8 }}>{note}</div>}
    </div>
  )
}

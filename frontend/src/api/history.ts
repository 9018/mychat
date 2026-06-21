// ── 历史记录接口 ──────────────────────────────────────────────
import type { HistoryItem } from './types'
import { apiGet, apiPost, apiDelete } from './client'

export async function loadHistory(): Promise<HistoryItem[]> {
  return apiGet<HistoryItem[]>('/api/history')
}

export async function saveHistory(item: HistoryItem): Promise<{ success: boolean; item: HistoryItem }> {
  return apiPost('/api/history', item)
}

export async function deleteHistory(id: string): Promise<void> {
  await apiDelete(`/api/history?id=${id}`)
}

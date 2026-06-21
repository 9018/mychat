// ── 配置接口 ──────────────────────────────────────────────────
import type { AppConfig } from './types'
import { apiGet, apiPost } from './client'

export async function loadConfig(): Promise<AppConfig> {
  return apiGet<AppConfig>('/api/config')
}

export async function saveConfig(config: AppConfig): Promise<void> {
  await apiPost('/api/config', config)
}

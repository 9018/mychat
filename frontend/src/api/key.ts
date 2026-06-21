// ── API Key 接口 ──────────────────────────────────────────────
import { apiGet, apiPost } from './client'

export async function loadApiKeyFromServer(): Promise<string> {
  const data = await apiGet<{ apiKey: string }>('/api/key')
  return data.apiKey
}

export async function saveApiKeyToServer(apiKey: string): Promise<void> {
  await apiPost('/api/key', { apiKey })
}

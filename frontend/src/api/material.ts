// ── 素材分析接口 ──────────────────────────────────────────────
import { apiGet, apiPost, apiDelete } from './client'

export interface MaterialConfig {
  prompt_template: string
  default_generate_count: number
  saved_template: string
}

export interface MaterialPrompts {
  imported_text: string
  prompts: Array<{
    id: string
    title: string
    description: string
    positive_prompt: string
    negative_prompt: string
    selected: boolean
  }>
}

export async function loadMaterialConfig(): Promise<MaterialConfig> {
  return apiGet<MaterialConfig>('/api/material/config')
}

export async function saveMaterialConfig(config: MaterialConfig): Promise<void> {
  await apiPost('/api/material/config', config)
}

export async function loadMaterialPrompts(): Promise<MaterialPrompts> {
  return apiGet<MaterialPrompts>('/api/material/prompts')
}

export async function saveMaterialPrompts(data: MaterialPrompts): Promise<void> {
  await apiPost('/api/material/prompts', data)
}

export async function clearMaterialPrompts(): Promise<void> {
  await apiDelete('/api/material/prompts')
}

// ── 聊天数据 API（设置 + 消息历史 → 服务端持久化） ──────────
import { apiGet, apiPost, apiDelete } from './client'
import type { ChatSettings, ChatMessage } from './types'

export async function loadChatSettings(): Promise<ChatSettings> {
  return apiGet<ChatSettings>('/api/chat/settings')
}

export async function saveChatSettings(settings: ChatSettings): Promise<void> {
  await apiPost('/api/chat/settings', settings)
}

export async function loadChatMessages(): Promise<ChatMessage[]> {
  return apiGet<ChatMessage[]>('/api/chat/messages')
}

export async function saveChatMessages(messages: ChatMessage[]): Promise<void> {
  await apiPost('/api/chat/messages', messages)
}

export async function clearChatMessages(): Promise<void> {
  await apiDelete('/api/chat/messages')
}

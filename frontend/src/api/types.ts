// ── 核心类型定义 ────────────────────────────────────────────────

export interface Model {
  id: string
  types: Array<'chat' | 'image' | 'video' | 'other'>
  enabled: boolean
}

export interface AppConfig {
  baseUrl: string
  videoModel: string
  imageModel: string
  chatModel: string
  modelList: Model[]
  modelListUpdatedAt: string
}

export interface HistoryItem {
  id: string
  title: string
  kind: 'video' | 'image'
  ar: string
  tone: number
  prompt: string
  model: string
  width: number
  height: number
  url: string
  filename?: string | null
  seconds?: string
}

export type ImgMode = 'txt2img' | 'img2img' | 'composition' | 'high_density'
export type VideoMode = 'text' | 'image' | 'multi' | 'keyframe'
export type TabType = 'video' | 'image' | 'chat' | 'admin' | 'material'

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string | ChatContentPart[]
  metric?: string
}

export interface ChatContentPart {
  type: 'text' | 'image_url' | 'audio_url' | 'video_url' | 'input_audio'
  text?: string
  image_url?: { url: string; detail?: 'auto' | 'low' | 'high' }
  audio_url?: { url: string }
  video_url?: { url: string }
  input_audio?: { data: string; format: string }
}

export interface ChatSettings {
  systemPrompt: string
  temperature: number
  topP: number
  maxTokens: number | ''
  stream: boolean
  enableThinking: boolean
  thinkingBudget: number
}

export interface TweaksState {
  theme: 'dark' | 'light'
  accent: string
  density: 'compact' | 'regular' | 'comfy'
  uiScale: number
}

export interface VideoTaskResult {
  video_url?: string
  remixed_from_video_id?: string
  seconds?: string
  size?: string
  status?: string
  progress?: number
  usage?: { duration_seconds?: number }
}

export interface MaterialPrompt {
  id: string
  title: string
  description: string
  positive_prompt: string
  negative_prompt: string
  selected: boolean
}

export interface UploadedFile {
  name: string
  type: string
  size: number
  dataUrl: string
}

export interface Aspect {
  id: string
  label: string
  w: number
  h: number
}

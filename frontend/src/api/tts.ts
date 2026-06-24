// ── MiMo TTS API 模块 ──────────────────────────────────────────
import { apiGet, apiPost } from './client'

// ── API Key ────────────────────────────────────────────────
export async function getMimoApiKey(): Promise<string> {
  const data = await apiGet<{ apiKey: string }>('/api/mimo-key')
  return data.apiKey || ''
}

export async function setMimoApiKey(key: string): Promise<void> {
  await apiPost('/api/mimo-key', { apiKey: key })
}

// ── TTS Generation ─────────────────────────────────────────
export interface TTSRequest {
  model: string
  text: string
  voice?: string
  styleInstruction?: string
  format?: 'wav' | 'pcm16' | 'mp3'
  stream?: boolean
  optimizeText?: boolean
  voiceSample?: string // base64 data URI for voice clone
}

export async function generateSpeech(params: TTSRequest, apiKey: string): Promise<ArrayBuffer> {
  const messages: Array<{ role: string; content: string }> = []

  // ── Map internal voice IDs to API-expected names ──────────
  // The API expects Chinese characters for Chinese voices (e.g. '冰糖', not 'bingtang')
  // while English voices and mimo_default use their ID directly.
  const VOICE_API_NAMES: Record<string, string> = {
    'bingtang': '冰糖',
    'moli': '茉莉',
    'soda': '苏打',
    'baihua': '白桦',
  }
  // Style instruction goes in user message
  if (params.styleInstruction) {
    messages.push({ role: 'user', content: params.styleInstruction })
  }

  // For voice design, the voice description goes first in user message
  if (params.model === 'mimo-v2.5-tts-voicedesign' && params.voice) {
    messages.unshift({ role: 'user', content: params.voice })
  }

  // The text to speak goes in assistant message
  messages.push({ role: 'assistant', content: params.text })

  const audioPayload: Record<string, unknown> = { format: params.format || 'wav' }

  if (params.model === 'mimo-v2.5-tts' && params.voice) {
    audioPayload.voice = VOICE_API_NAMES[params.voice] || params.voice
  }

  if (params.model === 'mimo-v2.5-tts-voiceclone' && params.voiceSample) {
    // Ensure clean data URI (strip any MIME type parameters like ;codecs=opus)
    const raw = params.voiceSample
    const [header, data] = raw.split(',')
    if (data) {
      const baseMime = header.split(';')[0].split(':')[1] || 'audio/wav'
      audioPayload.voice = `data:${baseMime};base64,${data}`
    } else {
      audioPayload.voice = raw
    }
  }

  const body: Record<string, unknown> = {
    model: params.model,
    messages,
    audio: audioPayload,
  }

  if (params.stream && params.format === 'pcm16') {
    body.stream = true
  }

  const res = await fetch('/mimo/v1/chat/completions', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Api-Key': apiKey,
    },
    body: JSON.stringify(body),
  })

  if (!res.ok) {
    const err = await res.text()
    throw new Error(`TTS API error (${res.status}): ${err}`)
  }

  const data = await res.json()
  const audioBase64 = data?.choices?.[0]?.message?.audio?.data
  if (!audioBase64) {
    throw new Error('No audio data in response')
  }

  // Convert base64 to ArrayBuffer
  const binaryStr = atob(audioBase64)
  const bytes = new Uint8Array(binaryStr.length)
  for (let i = 0; i < binaryStr.length; i++) {
    bytes[i] = binaryStr.charCodeAt(i)
  }
  return bytes.buffer
}

// ── Voice Data ──────────────────────────────────────────────
export interface VoiceInfo {
  id: string
  name: string
  lang: string
  gender: string
}

export const PRESET_VOICES: VoiceInfo[] = [
  { id: 'mimo_default', name: 'MiMo-默认', lang: '混合', gender: '混合' },
  { id: 'bingtang', name: '冰糖', lang: '中文', gender: '女性' },
  { id: 'moli', name: '茉莉', lang: '中文', gender: '女性' },
  { id: 'soda', name: '苏打', lang: '中文', gender: '男性' },
  { id: 'baihua', name: '白桦', lang: '中文', gender: '男性' },
  { id: 'Mia', name: 'Mia', lang: '英文', gender: '女性' },
  { id: 'Chloe', name: 'Chloe', lang: '英文', gender: '女性' },
  { id: 'Milo', name: 'Milo', lang: '英文', gender: '男性' },
  { id: 'Dean', name: 'Dean', lang: '英文', gender: '男性' },
]

// ── Style Tags Reference ───────────────────────────────────
export const STYLE_TAGS: Record<string, string[]> = {
  emotions: ['开心', '悲伤', '愤怒', '恐惧', '惊讶', '兴奋', '委屈', '平静', '冷漠',
    '怅然', '欣慰', '无奈', '愧疚', '释然', '嫉妒', '厌倦', '忐忑', '动情'],
  tones: ['温柔', '高冷', '活泼', '严肃', '慵懒', '俏皮', '深沉', '干练', '凌厉'],
  timbre: ['磁性', '醇厚', '清亮', '空灵', '稚嫩', '苍老', '甜美', '沙哑', '醇雅'],
  character: ['夹子音', '御姐音', '正太音', '大叔音', '台湾腔'],
  dialects: ['东北话', '四川话', '河南话', '粤语'],
  roleplay: ['孙悟空', '林黛玉'],
  special: ['唱歌'],
}

export const AUDIO_TAGS: Record<string, string[]> = {
  speed_rhythm: ['吸气', '深呼吸', '叹气', '长叹一口气', '喘息', '屏息'],
  emotion_state: ['紧张', '害怕', '激动', '疲惫', '委屈', '撒娇', '心虚', '震惊', '不耐烦'],
  voice_features: ['颤抖', '声音颤抖', '变调', '破音', '鼻音', '气声', '沙哑'],
  laugh_cry: ['笑', '轻笑', '大笑', '冷笑', '抽泣', '呜咽', '哽咽', '嚎啕大哭'],
  speed: ['语速加快', '语速放慢', '语速极快', '语速极慢', '碎碎念'],
}

export const DESIGN_EXAMPLES: string[] = [
  'Heavy Russian accent, gruff middle-aged male, blunt and matter-of-fact.',
  'Young female, extreme close-up with a binaural, ear-to-ear ASMR feel. Audible breathing, subtle swallowing, and soft natural lip sounds.',
  '一位年迈的老先生，说带北方口音的普通话，语速缓慢而沉稳，嗓音略带沙哑和沧桑感。',
  'Warm and confident podcast host, mid-30s female, clear articulation with a slight smile in her voice.',
  '1940s film noir narrator, deep and smoky, deliberate pacing, every word feels weighted with mystery.',
]

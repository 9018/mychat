// ── TTS 语音合成页面 ──────────────────────────────────────────
import { useState, useRef, useCallback, useEffect } from 'react'
import { generateSpeech, PRESET_VOICES, STYLE_TAGS, AUDIO_TAGS, DESIGN_EXAMPLES, getMimoApiKey, setMimoApiKey } from '@/api/tts'
import type { VoiceInfo } from '@/api/tts'
import { useKey } from '@/contexts/KeyContext'
import { showToast as showToastGlobal } from '@/components/common/Toast'

type TTSMode = 'preset' | 'design' | 'clone' | 'guide'

function AudioPlayer({ audioData, format }: { audioData: ArrayBuffer | null; format?: string }) {
  const [url, setUrl] = useState<string | null>(null)
  const [duration, setDuration] = useState(0)

  useEffect(() => {
    if (!audioData) { setUrl(null); return }
    const mime = format === 'mp3' ? 'audio/mpeg' : audioData.byteLength > 44 && new Uint8Array(audioData.slice(0, 4)).reduce((s, b) => s + String.fromCharCode(b), '') === 'RIFF' ? 'audio/wav' : 'audio/wav'
    const blob = new Blob([audioData], { type: mime })
    const objUrl = URL.createObjectURL(blob)
    setUrl(objUrl)
    return () => URL.revokeObjectURL(objUrl)
  }, [audioData, format])

  const handleDownload = () => {
    if (!url || !audioData) return
    const ext = format === 'mp3' ? '.mp3' : '.wav'
    const ts = new Date().toISOString().slice(0, 19).replace(/[:-]/g, '')
    const a = document.createElement('a')
    a.href = url
    a.download = `tts-${ts}${ext}`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
  }

  useEffect(() => {
    if (!url) return
    const audio = new Audio(url)
    audio.addEventListener('loadedmetadata', () => setDuration(audio.duration))
  }, [url])

  if (!audioData || !url) return null

  return (
    <div style={{
      background: 'var(--surface-2)', border: '1px solid var(--border)',
      borderRadius: 'var(--r)', padding: 16, marginTop: 16,
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
        <span style={{ fontSize: 13, color: 'var(--text-soft)' }}>Generated Audio</span>
        {duration > 0 && <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>{duration.toFixed(1)}s</span>}
        <button onClick={handleDownload} style={{
          background: 'none', border: '1px solid var(--border)', borderRadius: 'var(--r-sm)',
          padding: '2px 8px', fontSize: 11, cursor: 'pointer', color: 'var(--text-soft)', fontFamily: 'inherit'
        }}>
          ⬇ 下载
        </button>
      </div>
      <audio src={url} controls controlsList="nodownload" style={{ width: '100%', display: 'block' }} />
    </div>
  )
}

// ── Preset TTS Mode ────────────────────────────────────────
function PresetTTS({ apiKey, showToast }: { apiKey: string; showToast: (msg: string, type?: string) => void }) {
  const [text, setText] = useState('')
  const [voiceId, setVoiceId] = useState('mimo_default')
  const [styleInstruction, setStyleInstruction] = useState('')
  const [tagInput, setTagInput] = useState('')
  const [format, setFormat] = useState<'wav' | 'pcm16' | 'mp3'>('wav')
  const [loading, setLoading] = useState(false)
  const [audioData, setAudioData] = useState<ArrayBuffer | null>(null)

  const handleGenerate = async () => {
    if (!apiKey) { showToast('Please set your MIMO API key first', 'error'); return }
    if (!text.trim()) { showToast('Please enter text to speak', 'error'); return }
    setLoading(true); setAudioData(null)
    try {
      let finalText = text.trim()
      if (tagInput.trim()) finalText = `(${tagInput.trim()})${finalText}`
      const result = await generateSpeech({
        model: 'mimo-v2.5-tts', text: finalText, voice: voiceId,
        styleInstruction: styleInstruction || undefined, format,
        stream: format === 'pcm16',
      }, apiKey)
      setAudioData(result)
      showToast('Speech generated!', 'success')
    } catch (e: any) { showToast(`Error: ${e.message}`, 'error')
    } finally { setLoading(false) }
  }

  const insertTag = (tag: string) => setTagInput(prev => prev ? `${prev}, ${tag}` : tag)

  return (
    <div>
      <div style={{ marginBottom: 16, fontSize: 13, color: 'var(--text-soft)', lineHeight: 1.5 }}>
        使用 8 种预置精品音色，配合自然语言风格描述和音频标签，快速合成自然生动的语音。支持唱歌模式（添加 (唱歌) 标签）。
      </div>

      <div className="form-group">
        <label className="form-label">音色 Voice</label>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(120px, 1fr))', gap: 6, marginBottom: 12 }}>
          {PRESET_VOICES.map(v => (
            <div key={v.id} onClick={() => setVoiceId(v.id)} style={{
              padding: '8px 10px', background: voiceId === v.id ? 'var(--accent-soft)' : 'var(--surface)',
              border: `2px solid ${voiceId === v.id ? 'var(--accent-line)' : 'var(--border)'}`,
              borderRadius: 'var(--r-sm)', cursor: 'pointer', textAlign: 'center',
              transition: 'all 0.15s',
            }}>
              <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text)' }}>{v.name}</div>
              <div style={{ fontSize: 10, color: 'var(--text-muted)' }}>{v.lang} · {v.gender}</div>
            </div>
          ))}
        </div>
      </div>

      <div style={{ display: 'grid', gap: 12 }}>
        <div>
          <label className="form-label">合成文本 Text to Speak</label>
          <textarea className="form-input" style={{ width: '100%', minHeight: 80, resize: 'vertical' }}
            placeholder="Enter the text you want to convert to speech..."
            value={text} onChange={e => setText(e.target.value)} />
        </div>

        <div>
          <label className="form-label">风格标签 Style Tags <span style={{ color: 'var(--text-muted)', fontWeight: 400 }}>(可选)</span></label>
          <input className="form-input" style={{ width: '100%' }}
            placeholder="e.g., 开心, 语速加快, (怅然) ..."
            value={tagInput} onChange={e => setTagInput(e.target.value)} />
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4, marginTop: 6 }}>
            {['开心', '悲伤', '兴奋', '温柔', '活泼', '慵懒', '俏皮', '严肃',
              '语速加快', '语速放慢', '唱歌', '御姐音', '大叔音', '台湾腔',
              '东北话', '四川话', '粤语'].map(tag => (
              <span key={tag} className="tag" onClick={() => insertTag(tag)}
                style={{ cursor: 'pointer', padding: '2px 8px', fontSize: 12,
                  background: 'var(--surface)', border: '1px solid var(--border-soft)',
                  borderRadius: 12, color: 'var(--text-soft)' }}>{tag}</span>
            ))}
          </div>
        </div>

        <div>
          <label className="form-label">自然语言风格描述 <span style={{ color: 'var(--text-muted)', fontWeight: 400 }}>(可选)</span></label>
          <textarea className="form-input" style={{ width: '100%', minHeight: 60, resize: 'vertical' }}
            placeholder="Describe the speaking style in natural language..."
            value={styleInstruction} onChange={e => setStyleInstruction(e.target.value)} />
        </div>

        <div style={{ display: 'flex', gap: 8, alignItems: 'end' }}>
          <div style={{ flex: '0 0 120px' }}>
            <label className="form-label">格式</label>
            <select className="form-input" style={{ width: '100%' }} value={format}
              onChange={e => setFormat(e.target.value as any)}>
              <option value="wav">WAV</option>
              <option value="pcm16">PCM16</option>
              <option value="mp3">MP3</option>
            </select>
          </div>
          <div style={{ flex: 1 }} />
          <button className="btn btn-accent" onClick={handleGenerate}
            disabled={loading || !text.trim()}
            style={{ padding: '8px 20px', fontSize: 13 }}>
            {loading ? <><span className="spinner" /> Generating...</> : '🎤 生成语音'}
          </button>
        </div>
      </div>

      <AudioPlayer audioData={audioData} format={format} />
    </div>
  )
}

// ── Voice Designer Mode ────────────────────────────────────
function VoiceDesigner({ apiKey, showToast }: { apiKey: string; showToast: (msg: string, type?: string) => void }) {
  const [voiceDesc, setVoiceDesc] = useState('')
  const [text, setText] = useState('')
  const [format, setFormat] = useState<'wav' | 'pcm16' | 'mp3'>('wav')
  const [optimize, setOptimize] = useState(true)
  const [loading, setLoading] = useState(false)
  const [audioData, setAudioData] = useState<ArrayBuffer | null>(null)

  const handleGenerate = async () => {
    if (!apiKey) { showToast('Please set your MIMO API key first', 'error'); return }
    if (!voiceDesc.trim()) { showToast('Please describe the voice', 'error'); return }
    setLoading(true); setAudioData(null)
    try {
      const result = await generateSpeech({
        model: 'mimo-v2.5-tts-voicedesign', voice: voiceDesc.trim(),
        text: text.trim() || 'Hello, this is a custom-designed voice.',
        format, optimizeText: optimize, stream: format === 'pcm16',
      }, apiKey)
      setAudioData(result)
      showToast('Custom voice speech generated!', 'success')
    } catch (e: any) { showToast(`Error: ${e.message}`, 'error')
    } finally { setLoading(false) }
  }

  return (
    <div>
      <div style={{ marginBottom: 16, fontSize: 13, color: 'var(--text-soft)', lineHeight: 1.5 }}>
        用自然语言描述任意音色——年龄、性别、质感、口音、情绪、语速，模型即可生成与之匹配的语音。无需音频样本。
      </div>

      <div style={{ display: 'grid', gap: 12 }}>
        <div>
          <label className="form-label">音色描述 Voice Description</label>
          <textarea className="form-input" style={{ width: '100%', minHeight: 100, resize: 'vertical' }}
            placeholder="Describe the voice in detail..."
            value={voiceDesc} onChange={e => setVoiceDesc(e.target.value)} />
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4, marginTop: 6 }}>
            {DESIGN_EXAMPLES.map((ex, i) => (
              <span key={i} className="tag" onClick={() => setVoiceDesc(ex)}
                style={{ cursor: 'pointer', padding: '2px 8px', fontSize: 11,
                  background: 'var(--surface)', border: '1px solid var(--border-soft)',
                  borderRadius: 12, color: 'var(--text-soft)', maxWidth: 280,
                  whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}
                title={ex}>{ex.slice(0, 50)}...</span>
            ))}
          </div>
        </div>

        <div>
          <label className="form-label">合成文本</label>
          <textarea className="form-input" style={{ width: '100%', minHeight: 60, resize: 'vertical' }}
            placeholder="Enter the text this voice should speak..."
            value={text} onChange={e => setText(e.target.value)} />
        </div>

        <div style={{ display: 'flex', gap: 12, alignItems: 'end' }}>
          <div style={{ flex: '0 0 120px' }}>
            <label className="form-label">格式</label>
            <select className="form-input" style={{ width: '100%' }} value={format}
              onChange={e => setFormat(e.target.value as any)}>
              <option value="wav">WAV</option>
              <option value="pcm16">PCM16</option>
              <option value="mp3">MP3</option>
            </select>
          </div>
          <label className="toggle" onClick={() => setOptimize(!optimize)}
            style={{ display: 'flex', alignItems: 'center', gap: 6, cursor: 'pointer', fontSize: 12, padding: '4px 0' }}>
            <div style={{ width: 32, height: 18, background: optimize ? 'var(--accent)' : 'var(--border)', borderRadius: 9, position: 'relative', transition: '0.15s' }}>
              <div style={{ width: 14, height: 14, background: '#fff', borderRadius: '50%', position: 'absolute', top: 2, left: optimize ? 16 : 2, transition: '0.15s' }} />
            </div>
            自动优化文本
          </label>
          <div style={{ flex: 1 }} />
          <button className="btn btn-accent" onClick={handleGenerate}
            disabled={loading || !voiceDesc.trim()}
            style={{ padding: '8px 20px', fontSize: 13 }}>
            {loading ? <><span className="spinner" /> Generating...</> : '🎨 生成自定义音色'}
          </button>
        </div>
      </div>

      <AudioPlayer audioData={audioData} format={format} />
    </div>
  )
}

// ── Voice Cloner Mode ──────────────────────────────────────
function VoiceCloner({ apiKey, showToast }: { apiKey: string; showToast: (msg: string, type?: string) => void }) {
  const [sampleFile, setSampleFile] = useState<File | null>(null)
  const [sampleBase64, setSampleBase64] = useState('')
  const [mimeType, setMimeType] = useState('')
  const [text, setText] = useState('')
  const [styleInstruction, setStyleInstruction] = useState('')
  const [format, setFormat] = useState<'wav' | 'pcm16' | 'mp3'>('wav')
  const [loading, setLoading] = useState(false)
  const [audioData, setAudioData] = useState<ArrayBuffer | null>(null)
  const fileRef = useRef<HTMLInputElement>(null)
  // Recording state
  const [isRecording, setIsRecording] = useState(false)
  const [recordingDuration, setRecordingDuration] = useState(0)
  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const chunksRef = useRef<Blob[]>([])
  const recordingTimerRef = useRef<number | null>(null)

  const handleFile = (file: File | null) => {
    if (!file) return
    if (file.size > 10 * 1024 * 1024) { showToast('File too large (max 10MB)', 'error'); return }
    if (!file.name.match(/\.(mp3|wav)$/i)) { showToast('Only MP3/WAV supported', 'error'); return }
    setSampleFile(file)
    const mime = file.name.endsWith('.mp3') ? 'audio/mpeg' : 'audio/wav'
    setMimeType(mime)
    const reader = new FileReader()
    reader.onload = () => setSampleBase64((reader.result as string).split(',')[1])
    reader.readAsDataURL(file)
  }

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      // Create AudioContext during user gesture (needed for WAV conversion on iOS)
      const audioCtx = new (window.AudioContext || (window as any).webkitAudioContext)()
      // Try MIME types in order of preference (Chrome webm -> Firefox ogg -> Safari mp4)
      const mimeTypes = [
        'audio/webm;codecs=opus',
        'audio/webm',
        'audio/ogg;codecs=opus',
        'audio/mp4',
        'audio/aac',
      ]
      const mt = mimeTypes.find(t => MediaRecorder.isTypeSupported(t)) || ''

      if (!mt) {
        throw new Error('Your browser does not support audio recording (no compatible MIME type found)')
      }

      const recorder = new MediaRecorder(stream, { mimeType: mt })
      mediaRecorderRef.current = recorder
      chunksRef.current = []

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data)
      }

      recorder.onstop = () => {
        (async () => {
          const blob = new Blob(chunksRef.current, { type: mt })
          stream.getTracks().forEach(t => t.stop())

          try {
            // Convert to WAV (API only supports wav/mp3)
            const arrayBuffer = await blob.arrayBuffer()
            if (audioCtx.state === 'suspended') await audioCtx.resume()
            const audioBuffer = await audioCtx.decodeAudioData(arrayBuffer)
            const wavBlob = audioBufferToWav(audioBuffer)

            const reader = new FileReader()
            reader.onload = () => {
              const base64 = (reader.result as string).split(',')[1]
              setSampleBase64(base64)
              setMimeType('audio/wav')
              setSampleFile(new File([wavBlob], 'recording.wav', { type: 'audio/wav' }))
            }
            reader.readAsDataURL(wavBlob)
          } catch (err) {
            showToast('Failed to process recording. Please try uploading a file instead.', 'error')
          }

          if (recordingTimerRef.current) {
            clearInterval(recordingTimerRef.current)
            recordingTimerRef.current = null
          }
          setRecordingDuration(0)
        })()
      }

      recorder.start()
      setIsRecording(true)

      recordingTimerRef.current = window.setInterval(() => {
        setRecordingDuration(prev => prev + 1)
      }, 1000)

    } catch (err: any) {
      const msg = err?.message || err?.name || 'Unknown error'
      // Distinguish between permission denied vs browser support vs HTTPS
      if (msg.includes('PermissionDenied') || msg.includes('NotAllowedError')) {
        showToast('Microphone permission denied. Please allow microphone access in your browser settings.', 'error')
      } else if (msg.includes('NotFoundError') || msg.includes('NotReadableError')) {
        showToast('No microphone found. Please connect a microphone and try again.', 'error')
      } else if (location.protocol !== 'https:' && location.hostname !== 'localhost' && location.hostname !== '127.0.0.1') {
        showToast('Microphone access requires HTTPS. Use https:// or localhost.', 'error')
      } else {
        showToast(msg.length < 80 ? msg : 'Microphone recording failed. Please try uploading a file instead.', 'error')
      }
    }
  }

  const stopRecording = () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      mediaRecorderRef.current.stop()
      setIsRecording(false)
    }
  }

  const handleGenerate = async () => {
    if (!apiKey) { showToast('Please set MIMO API key first', 'error'); return }
    if (!sampleBase64) { showToast('Please upload a voice sample', 'error'); return }
    if (!text.trim()) { showToast('Please enter text to speak', 'error'); return }
    setLoading(true); setAudioData(null)
    try {
      const result = await generateSpeech({
        model: 'mimo-v2.5-tts-voiceclone', text: text.trim(),
        voiceSample: `data:${mimeType.split(';')[0].trim()};base64,${sampleBase64}`,
        styleInstruction: styleInstruction || undefined,
        format, stream: format === 'pcm16',
      }, apiKey)
      setAudioData(result)
      showToast('Voice cloned and speech generated!', 'success')
    } catch (e: any) { showToast(`Error: ${e.message}`, 'error')
    } finally { setLoading(false) }
  }

  const fmtSize = (b: number) => b < 1024 ? `${b}B` : b < 1048576 ? `${(b/1024).toFixed(1)}KB` : `${(b/1048576).toFixed(1)}MB`

  return (
    <div>
      <div style={{ marginBottom: 16, fontSize: 13, color: 'var(--text-soft)', lineHeight: 1.5 }}>
        上传音频样本（MP3/WAV，不超过 10MB），模型即可精准复刻音色并生成任意内容的语音。
      </div>

      <div style={{ display: 'grid', gap: 12 }}>
        <div>
          <label className="form-label">音频样本 Voice Sample</label>
          <input ref={fileRef} type='file' accept='.mp3,.wav,audio/mpeg,audio/wav' style={{ display: 'none' }}
            onChange={e => handleFile(e.target.files?.[0] || null)} />
          {!sampleFile ? (
            <div style={{
              border: '2px dashed var(--border)', borderRadius: 'var(--r)',
              padding: 24, textAlign: 'center', transition: '0.15s',
            }}>
              {isRecording ? (
                <>
                  <div style={{ fontSize: 28, marginBottom: 6 }}>🔴</div>
                  <div style={{ fontSize: 13, color: 'var(--text-soft)', marginBottom: 4 }}>
                    {String(Math.floor(recordingDuration / 60)).padStart(2, '0')}:{String(recordingDuration % 60).padStart(2, '0')}
                  </div>
                  <button className="btn" onClick={stopRecording}
                    style={{ padding: '8px 24px', fontSize: 13, marginTop: 8,
                      background: '#e74c3c', color: '#fff', border: 'none',
                      borderRadius: 'var(--r-sm)', cursor: 'pointer', fontFamily: 'inherit' }}>
                    ⏹ 停止录音
                  </button>
                </>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                  <div onClick={() => fileRef.current?.click()} style={{ cursor: 'pointer' }}>
                    <div style={{ fontSize: 28, marginBottom: 6 }}>🎵</div>
                    <div style={{ fontSize: 13, color: 'var(--text-soft)' }}>点击上传音频样本</div>
                    <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4 }}>MP3 或 WAV，最大 10MB</div>
                  </div>
                  <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>— 或 —</div>
                  <div style={{ display: 'flex', gap: 8, justifyContent: 'center' }}>
                    <button className="btn btn-ghost" onClick={startRecording}
                      style={{ padding: '8px 24px', fontSize: 13 }}>
                      🎤 开始录音
                    </button>
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '8px 12px',
              background: 'var(--surface)', borderRadius: 'var(--r-sm)', border: '1px solid var(--border)' }}>
              <span>{sampleFile.name.startsWith('recording.') ? '🎤' : '🎵'}</span>
              <span style={{ flex: 1, fontSize: 12 }}>{sampleFile.name}</span>
              <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>{fmtSize(sampleFile.size)}</span>
              <button className='btn btn-ghost btn-sm' onClick={() => { setSampleFile(null); setSampleBase64(''); setIsRecording(false) }}>✕</button>
            </div>
          )}
        </div>

        <div>
          <label className="form-label">合成文本</label>
          <textarea className="form-input" style={{ width: '100%', minHeight: 80, resize: 'vertical' }}
            placeholder="Enter text for the cloned voice to speak..."
            value={text} onChange={e => setText(e.target.value)} />
        </div>

        <div>
          <label className="form-label">风格描述 <span style={{ color: 'var(--text-muted)', fontWeight: 400 }}>(可选)</span></label>
          <textarea className="form-input" style={{ width: '100%', minHeight: 50, resize: 'vertical' }}
            placeholder="Optional style instructions..."
            value={styleInstruction} onChange={e => setStyleInstruction(e.target.value)} />
        </div>

        <div style={{ display: 'flex', gap: 8, alignItems: 'end' }}>
          <div style={{ flex: '0 0 120px' }}>
            <label className="form-label">格式</label>
            <select className="form-input" style={{ width: '100%' }} value={format}
              onChange={e => setFormat(e.target.value as any)}>
              <option value="wav">WAV</option>
              <option value="pcm16">PCM16</option>
              <option value="mp3">MP3</option>
            </select>
          </div>
          <div style={{ flex: 1 }} />
          <button className="btn btn-accent" onClick={handleGenerate}
            disabled={loading || !sampleBase64 || !text.trim()}
            style={{ padding: '8px 20px', fontSize: 13 }}>
            {loading ? <><span className="spinner" /> Cloning...</> : '📋 克隆并生成语音'}
          </button>
        </div>
      </div>

      <AudioPlayer audioData={audioData} format={format} />
    </div>
  )
}


// ── Helper: convert AudioBuffer to WAV blob ────────────────
function audioBufferToWav(buffer: AudioBuffer): Blob {
  const numChannels = 1  // mono for voice clone
  const sampleRate = buffer.sampleRate
  const bitDepth = 16
  const bytesPerSample = bitDepth / 8
  const blockAlign = numChannels * bytesPerSample

  // Mix all channels down to mono
  const channelData: Float32Array[] = []
  for (let c = 0; c < buffer.numberOfChannels; c++) {
    channelData.push(buffer.getChannelData(c))
  }

  const length = buffer.length
  const dataLength = length * bytesPerSample
  const headerLength = 44
  const totalLength = headerLength + dataLength

  const arrayBuffer = new ArrayBuffer(totalLength)
  const view = new DataView(arrayBuffer)

  // WAV header
  const w = (off: number, s: string) => {
    for (let k = 0; k < s.length; k++) view.setUint8(off + k, s.charCodeAt(k))
  }
  w(0, 'RIFF')
  view.setUint32(4, totalLength - 8, true)
  w(8, 'WAVE')
  w(12, 'fmt ')
  view.setUint32(16, 16, true)
  view.setUint16(20, 1, true)
  view.setUint16(22, numChannels, true)
  view.setUint32(24, sampleRate, true)
  view.setUint32(28, sampleRate * blockAlign, true)
  view.setUint16(32, blockAlign, true)
  view.setUint16(34, bitDepth, true)
  w(36, 'data')
  view.setUint32(40, dataLength, true)

  // Write PCM samples (mono)
  let offset = 44
  for (let i = 0; i < length; i++) {
    let sample = 0
    for (let c = 0; c < channelData.length; c++) {
      sample += channelData[c][i]
    }
    sample /= channelData.length
    sample = Math.max(-1, Math.min(1, sample))
    view.setInt16(offset, sample < 0 ? sample * 0x8000 : sample * 0x7FFF, true)
    offset += 2
  }

  return new Blob([arrayBuffer], { type: 'audio/wav' })
}
// ── Style Guide Mode ────────────────────────────────────────
function StyleGuideView() {
  return (
    <div>
      <div style={{ marginBottom: 16, fontSize: 13, color: 'var(--text-soft)', lineHeight: 1.5 }}>
        MiMo TTS 支持两种风格控制方式：<strong>自然语言描述</strong>（放在 user 消息中）和
        <strong>标签控制</strong>（放在 assistant 消息文本中）。
      </div>

      <div style={{ display: 'grid', gap: 16 }}>
        {/* Natural Language */}
        <div style={{ background: 'var(--surface)', borderRadius: 'var(--r)', padding: 16, border: '1px solid var(--border)' }}>
          <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 8 }}>自然语言控制</div>
          <div style={{ fontSize: 12, color: 'var(--text-soft)', marginBottom: 8 }}>
            像导演指导演员一样描述所需风格。示例：
          </div>
          {[
            'Bright, bouncy, slightly sing-song tone — like you\'re bursting with good news.',
            '一位年迈的老先生，说带北方口音的普通话，语速缓慢而沉稳，嗓音略带沙哑和沧桑感。',
            '用轻快上扬的语调向领导报喜，语速稍快，带着查到成绩后压抑不住的激动与小骄傲。',
          ].map((ex, i) => (
            <div key={i} style={{
              background: 'var(--surface-2)', padding: '8px 12px', borderRadius: 'var(--r-sm)',
              fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--text-soft)',
              marginBottom: 6, lineHeight: 1.5,
            }}>{ex}</div>
          ))}
        </div>

        {/* Style Tags */}
        {Object.entries(STYLE_TAGS).map(([category, tags]) => (
          <div key={category} style={{
            background: 'var(--surface)', borderRadius: 'var(--r)', padding: 16,
            border: '1px solid var(--border)',
          }}>
            <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 6, textTransform: 'capitalize' }}>
              ({category}) 风格标签
            </div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
              {tags.map(tag => (
                <span key={tag} style={{
                  padding: '2px 8px', fontSize: 11, background: 'var(--surface-2)',
                  border: '1px solid var(--border-soft)', borderRadius: 12,
                  color: 'var(--text-soft)',
                }}>{tag}</span>
              ))}
            </div>
          </div>
        ))}

        {/* Audio Tags */}
        {Object.entries(AUDIO_TAGS).map(([category, tags]) => (
          <div key={category} style={{
            background: 'var(--surface)', borderRadius: 'var(--r)', padding: 16,
            border: '1px solid var(--border)',
          }}>
            <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 6, textTransform: 'capitalize' }}>
              [{category}] 音频标签
            </div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
              {tags.map(tag => (
                <span key={tag} style={{
                  padding: '2px 8px', fontSize: 11, background: 'var(--surface-2)',
                  border: '1px solid var(--border-soft)', borderRadius: 12,
                  color: 'var(--text-soft)',
                }}>[{tag}]</span>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

// ── Main TTS Page ──────────────────────────────────────────
const TTS_MODES: Array<{ id: TTSMode; label: string; icon: string }> = [
  { id: 'preset', label: 'Quick TTS', icon: '⚡' },
  { id: 'design', label: 'Voice Designer', icon: '🎨' },
  { id: 'clone', label: 'Voice Cloner', icon: '📋' },
  { id: 'guide', label: 'Style Guide', icon: '📖' },
]

export default function TTSPage() {
  const [mode, setMode] = useState<TTSMode>('preset')
  const { apiKey, isReady } = useKey()
  const [mimoApiKey, setMimoApiKeyState] = useState('')
  const [showKeyModal, setShowKeyModal] = useState(false)
  const [keyInput, setKeyInput] = useState('')
  // Use imported showToast directly

  useEffect(() => {
    getMimoApiKey().then(k => { if (k) setMimoApiKeyState(k) }).catch(() => {})
  }, [])

  const saveKey = async () => {
    await setMimoApiKey(keyInput.trim())
    setMimoApiKeyState(keyInput.trim())
    setShowKeyModal(false)
  }

  const showToast = useCallback((msg: string, type?: string) => {
    showToastGlobal(msg, (type || 'success') as 'success' | 'error' | 'warning')
  }, [])

  return (
    <div style={{ padding: 20 }}>
      {/* Key banner + mode tabs */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 16 }}>
        <div style={{ display: 'flex', gap: 2, background: 'var(--surface)', padding: 3,
          borderRadius: 'var(--r-sm)', flex: 1 }}>
          {TTS_MODES.map(m => (
            <button key={m.id} onClick={() => setMode(m.id)}
              style={{
                flex: 1, padding: '8px 12px', border: 'none', borderRadius: 'var(--r-sm)',
                background: mode === m.id ? 'var(--accent)' : 'transparent',
                color: mode === m.id ? '#fff' : 'var(--text-soft)',
                fontSize: 12, fontWeight: 500, cursor: 'pointer', fontFamily: 'inherit',
                transition: '0.15s',
              }}>
              {m.icon} {m.label}
            </button>
          ))}
        </div>
        <button className="btn btn-ghost" style={{ fontSize: 12, flexShrink: 0 }}
          onClick={() => { setKeyInput(mimoApiKey); setShowKeyModal(true) }}>
          🔑 {mimoApiKey ? 'Key ✓' : 'Set MIMO Key'}
        </button>
      </div>

      {/* Mode content */}
      <div style={{
        background: 'var(--surface)', borderRadius: 'var(--r)', padding: 20,
        border: '1px solid var(--border)',
      }}>
        {mode === 'preset' && <PresetTTS apiKey={mimoApiKey} showToast={showToast} />}
        {mode === 'design' && <VoiceDesigner apiKey={mimoApiKey} showToast={showToast} />}
        {mode === 'clone' && <VoiceCloner apiKey={mimoApiKey} showToast={showToast} />}
        {mode === 'guide' && <StyleGuideView />}
      </div>

      {/* Key Modal */}
      {showKeyModal && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }}
          onClick={() => setShowKeyModal(false)}>
          <div style={{ background: 'var(--surface)', borderRadius: 'var(--r-lg)', padding: 24, width: 400, maxWidth: '90vw', border: '1px solid var(--border)' }}
            onClick={e => e.stopPropagation()}>
            <h3 style={{ fontSize: 16, fontWeight: 600, marginBottom: 8 }}>MiMo API Key</h3>
            <p style={{ fontSize: 12, color: 'var(--text-soft)', marginBottom: 16 }}>
              Get your key from <a href="https://mimo.mi.com" target="_blank" rel="noreferrer" style={{ color: 'var(--accent-ink)' }}>mimo.mi.com</a>.
              Stored in .env as MIMO_API_KEY alongside your Agnes API key.
            </p>
            <input className="form-input" style={{ width: '100%', marginBottom: 16 }}
              placeholder="Enter MIMO_API_KEY"
              value={keyInput} onChange={e => setKeyInput(e.target.value)} />
            <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
              <button className="btn btn-ghost" onClick={() => setShowKeyModal(false)}>Cancel</button>
              <button className="btn btn-accent" onClick={saveKey} disabled={!keyInput.trim()}>Save</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

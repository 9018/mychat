// ── 管理页（API Key + 模型管理 + 配置） ─────────────────────
import { useState, useEffect } from 'react'
import { useKey } from '@/contexts/KeyContext'
import { useConfig } from '@/contexts/ConfigContext'
import { saveConfig } from '@/api/config'
import type { Model } from '@/api/types'
import { ModelSelect } from '@/components/common/ModelSelect'
import { showToast } from '@/components/common/Toast'
import { apiProxyGet } from '@/api/client'
import { guessModelType } from '@/lib/utils'



export function AdminPage() {
  const { apiKey, setApiKey, save, isReady } = useKey()
  const { config, setConfig, refresh } = useConfig()
  const [baseUrl, setBaseUrl] = useState(config.baseUrl)
  const [keyInput, setKeyInput] = useState(apiKey)
  const [fetching, setFetching] = useState(false)
  const [showDisabled, setShowDisabled] = useState(false)

  useEffect(() => {
    setKeyInput(apiKey)
    setBaseUrl(config.baseUrl)
  }, [apiKey, config.baseUrl])

  const handleSaveKey = async () => {
    await save(keyInput)
    await saveConfig({ ...config, baseUrl })
    showToast('✓ API Token 配置已保存', 'success')
  }

  const handleFetchModels = async () => {
    if (!keyInput) { showToast('请先填写 API Key', 'error'); return }
    setFetching(true)
    try {
      const res = await apiProxyGet('/v1/models', keyInput)
      const data = await res.json()
      if (!res.ok) throw new Error(data.error?.message || `HTTP ${res.status}`)
      const list = data.data || data.models || []
      const existingMap = new Map(config.modelList.map(m => [m.id, m]))
      const merged: Model[] = list.map((m: any) => {
        const id = m.id || m.name
        const existing = existingMap.get(id)
        return {
          id,
          types: existing?.types || [guessModelType(id) as Model['types'][number]],
          enabled: existing?.enabled !== undefined ? existing.enabled : true,
        }
      })
      const updated = { ...config, modelList: merged, modelListUpdatedAt: new Date().toISOString() }
      setConfig(updated)
      showToast(`✓ 已拉取 ${merged.length} 个模型`, 'success')
    } catch (err: any) {
      showToast(`拉取失败: ${err.message}`, 'error')
    } finally {
      setFetching(false)
    }
  }
  const updateModel = (idx: number, field: string, value: any) => {
    const list = [...config.modelList]
    const m = { ...list[idx] }
    if (field === 'types') {
      // value is { type: string, checked: boolean }
      const types = [...m.types]
      if (value.checked) { if (!types.includes(value.type)) types.push(value.type) }
      else { const i = types.indexOf(value.type); if (i >= 0) types.splice(i, 1) }
      m.types = types.length ? types : ['other']
    } else {
      (m as any)[field] = value
    }
    list[idx] = m
    setConfig({ ...config, modelList: list })
  }

  const addModel = () => {
    const list = [...config.modelList, { id: '', types: ['chat'] as Model['types'], enabled: true }]
    setConfig({ ...config, modelList: list })
  }

  const deleteModel = (idx: number) => {
    const list = config.modelList.filter((_, i) => i !== idx)
    setConfig({ ...config, modelList: list })
  }

  const saveAllConfig = async () => {
    const updated = {
      ...config,
      baseUrl,
      videoModel: config.videoModel,
      imageModel: config.imageModel,
      chatModel: config.chatModel,
    }
    await saveConfig(updated)
    showToast('✓ 配置已保存', 'success')
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16, padding: 16 }}>
      {/* API Key */}
      <div className="card" style={{ padding: 16, borderRadius: 'var(--r-lg)', background: 'var(--surface)', border: '1px solid var(--border)' }}>
        <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 12 }}>API Token</h3>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
          <input type="password" value={keyInput}
            onChange={e => setKeyInput(e.target.value)}
            placeholder="输入 API Key"
            style={{ flex: 1, minWidth: 200 }} />
          <button onClick={handleSaveKey} className="btn btn-accent" style={{ padding: '6px 16px', fontSize: 13 }}>
            保存
          </button>
          <span id="keyStatus" style={{ fontSize: 12, display: 'flex', alignItems: 'center', gap: 6 }}>
            <span style={{
              width: 7, height: 7, borderRadius: '50%', display: 'inline-block',
              background: isReady ? 'var(--success)' : 'var(--warning)',
            }} />
            <span style={{ color: isReady ? 'var(--success)' : 'var(--warning)' }}>
              {isReady ? '密钥已配置' : '密钥未配置'}
            </span>
          </span>
        </div>
      </div>

      {/* Base URL */}
      <div className="card" style={{ padding: 16, borderRadius: 'var(--r-lg)', background: 'var(--surface)', border: '1px solid var(--border)' }}>
        <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 12 }}>Base URL</h3>
        <input type="text" value={baseUrl}
          onChange={e => setBaseUrl(e.target.value)}
          placeholder="https://apihub.agnes-ai.com/v1"
          style={{ width: '100%' }} />
      </div>

      {/* Model Management */}
      <div className="card" style={{ padding: 16, borderRadius: 'var(--r-lg)', background: 'var(--surface)', border: '1px solid var(--border)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12, flexWrap: 'wrap', gap: 8 }}>
          <h3 style={{ fontSize: 14, fontWeight: 600 }}>模型列表 <span style={{ fontSize: 11, fontWeight: 400, color: 'var(--text-muted)' }}>已启用 {config.modelList.filter(m => m.enabled).length} / 共 {config.modelList.length}</span></h3>
          <div style={{ display: 'flex', gap: 6 }}>
            <button onClick={handleFetchModels} disabled={fetching} className="btn btn-subtle" style={{ fontSize: 12, padding: '4px 10px' }}>
              {fetching ? '拉取中…' : '🔄 拉取'}
            </button>
            <button onClick={addModel} className="btn btn-subtle" style={{ fontSize: 12, padding: '4px 10px' }}>+ 添加</button>
            <button onClick={saveAllConfig} className="btn btn-accent" style={{ fontSize: 12, padding: '4px 10px' }}>💾 保存配置</button>
            <button onClick={() => setShowDisabled(!showDisabled)} className="btn btn-subtle" style={{ fontSize: 12, padding: '4px 10px' }}>
              {showDisabled ? '🙈 隐藏禁用' : '👁 显示全部'}
            </button>
          </div>
        </div>

        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
          <thead>
            <tr style={{ borderBottom: '1px solid var(--border)' }}>
              <th style={{ textAlign: 'left', padding: '6px 8px', color: 'var(--text-muted)', fontWeight: 500 }}>模型 ID</th>
              <th style={{ textAlign: 'left', padding: '6px 8px', color: 'var(--text-muted)', fontWeight: 500 }}>类型</th>
              <th style={{ textAlign: 'center', padding: '6px 8px', color: 'var(--text-muted)', fontWeight: 500 }}>启用</th>
              <th style={{ padding: '6px 8px', width: 40 }}></th>
            </tr>
          </thead>
          <tbody>
            {config.modelList.length === 0 ? (
              <tr><td colSpan={4} style={{ textAlign: 'center', padding: 24, color: 'var(--text-muted)' }}>暂无模型，点击上方按钮拉取或手动添加</td></tr>
            ) : config.modelList.filter(m2 => showDisabled || m2.enabled).map((m) => (
              <tr key={config.modelList.indexOf(m)} style={{ borderBottom: '1px solid var(--border-soft)' }}>
                <td style={{ padding: '4px 8px' }}>
                  <input type="text" value={m.id} onChange={e => updateModel(config.modelList.indexOf(m), 'id', e.target.value)}
                    placeholder="模型 ID" style={{ width: '100%', minWidth: 120, fontSize: 12 }} />
                </td>
                <td style={{ padding: '4px 8px' }}>
                  <div style={{ display: 'flex', gap: 8 }}>
                    {['chat', 'image', 'video', 'other'].map(t => (
                      <label key={t} style={{ display: 'flex', alignItems: 'center', gap: 3, cursor: 'pointer' }}>
                        <input type="checkbox" checked={m.types.includes(t as any)}
                          onChange={e => updateModel(config.modelList.indexOf(m), 'types', { type: t, checked: e.target.checked })} />
                        <span>{t}</span>
                      </label>
                    ))}
                  </div>
                </td>
                <td style={{ textAlign: 'center', padding: '4px 8px' }}>
                  <input type="checkbox" checked={m.enabled}
                    onChange={e => updateModel(config.modelList.indexOf(m), 'enabled', e.target.checked)} />
                </td>
                <td style={{ padding: '4px 8px' }}>
                  <button onClick={() => deleteModel(config.modelList.indexOf(m))} className="btn btn-icon" style={{ fontSize: 14 }}>×</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Default Models */}
      <div className="card" style={{ padding: 16, borderRadius: 'var(--r-lg)', background: 'var(--surface)', border: '1px solid var(--border)' }}>
        <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 12 }}>默认模型</h3>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{ fontSize: 12, width: 80, color: 'var(--text-soft)' }}>视频模型</span>
            <ModelSelect type="video" value={config.videoModel} onChange={v => setConfig({ ...config, videoModel: v })} />
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{ fontSize: 12, width: 80, color: 'var(--text-soft)' }}>图像模型</span>
            <ModelSelect type="image" value={config.imageModel} onChange={v => setConfig({ ...config, imageModel: v })} />
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{ fontSize: 12, width: 80, color: 'var(--text-soft)' }}>聊天模型</span>
            <ModelSelect type="chat" value={config.chatModel} onChange={v => setConfig({ ...config, chatModel: v })} />
          </div>
        </div>
      </div>
    </div>
  )
}

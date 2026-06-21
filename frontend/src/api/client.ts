// ── 通用 HTTP 客户端 ──────────────────────────────────────────
// 封装 fetch，统一错误处理、超时、认证头

const BASE_URL = '' // 走 Vite proxy，空字符串表示同源

export class ApiError extends Error {
  status: number
  constructor(message: string, status: number) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

export async function apiGet<T>(path: string, options?: { signal?: AbortSignal }): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    method: 'GET',
    headers: { 'Content-Type': 'application/json' },
    signal: options?.signal,
  })
  const data = await res.json()
  if (!res.ok) {
    throw new ApiError(data.error?.message || data.message || `HTTP ${res.status}`, res.status)
  }
  return data as T
}

export async function apiPost<T>(path: string, body?: unknown, options?: { signal?: AbortSignal }): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: body ? JSON.stringify(body) : undefined,
    signal: options?.signal,
  })
  const data = await res.json()
  if (!res.ok) {
    throw new ApiError(data.error?.message || data.message || `HTTP ${res.status}`, res.status)
  }
  return data as T
}

export async function apiDelete<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    method: 'DELETE',
  })
  const data = await res.json()
  if (!res.ok) {
    throw new ApiError(data.error?.message || data.message || `HTTP ${res.status}`, res.status)
  }
  return data as T
}

export async function apiProxyPost(path: string, body: unknown, apiKey: string, signal?: AbortSignal): Promise<Response> {
  return fetch(`${BASE_URL}${path}`, {
    method: 'POST',
    headers: {
      'X-Api-Key': apiKey,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(body),
    signal,
  })
}

export async function apiProxyGet(path: string, apiKey: string, signal?: AbortSignal): Promise<Response> {
  return fetch(`${BASE_URL}${path}`, {
    method: 'GET',
    headers: { 'X-Api-Key': apiKey },
    signal,
  })
}

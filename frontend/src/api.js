const BASE = '/api'

// ─── TEFAS veri çekme ──────────────────────────────────────────────
export async function trackFund(fundCode) {
  const res = await fetch(`${BASE}/funds/track`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ fundCode }),
  })
  const data = await res.json()
  if (!res.ok) throw new Error(data.detail || 'Fon eklenemedi')
  return data
}

export async function refreshFund(fundCode) {
  const res = await fetch(`${BASE}/funds/${fundCode}/refresh`, { method: 'POST' })
  if (!res.ok) throw new Error('Güncelleme başarısız')
  return res.json()
}

// ─── PDF analizi ───────────────────────────────────────────────────
export async function analyzePDF(fundCode, file) {
  const form = new FormData()
  form.append('file', file)
  const res = await fetch(`${BASE}/funds/${fundCode}/analyze-pdf`, { method: 'POST', body: form })
  const data = await res.json()
  if (!res.ok) throw new Error(data.detail || 'PDF analizi başarısız')
  return data
}

// ─── Fon listesi & detay ───────────────────────────────────────────
export async function getFunds() {
  const res = await fetch(`${BASE}/funds`)
  if (!res.ok) throw new Error('Fonlar alınamadı')
  return res.json()
}

export async function getFund(code) {
  const res = await fetch(`${BASE}/funds/${code}`)
  if (!res.ok) throw new Error('Fon bulunamadı')
  return res.json()
}

export async function deleteFund(fundCode) {
  await fetch(`${BASE}/funds/${fundCode}`, { method: 'DELETE' })
}

// ─── Evolver ───────────────────────────────────────────────────────
export async function getEvolver(fundCode) {
  const res = await fetch(`${BASE}/evolver/${fundCode}`)
  if (!res.ok) return []
  return res.json()
}

export async function learnManualPrice(fundCode, data) {
  const res = await fetch(`${BASE}/evolver/${fundCode}/manual-price`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  if (!res.ok) return null
  return res.json()
}

// ─── Benchmark & stats ─────────────────────────────────────────────
export async function getBenchmarks() {
  const res = await fetch(`${BASE}/benchmarks`)
  if (!res.ok) return null
  return res.json()
}

export async function getStats() {
  const res = await fetch(`${BASE}/stats`)
  if (!res.ok) return {}
  return res.json()
}

import { useState, useEffect } from 'react'
import { getForecast } from '../api.js'

export default function ForecastPanel({ onSelectFund }) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [lastUpdated, setLastUpdated] = useState(null)
  const [search, setSearch] = useState('')

  const load = async () => {
    setLoading(true); setError(null)
    try {
      const d = await getForecast()
      setData(d); setLastUpdated(new Date())
    } catch (e) { setError(e.message) }
    finally { setLoading(false) }
  }

  useEffect(() => { load() }, [])

  if (loading) return (
    <div style={{ textAlign: 'center', color: '#475569', padding: 60, fontSize: 14 }}>
      ⏳ TimesFM tahminleri hesaplanıyor...
    </div>
  )
  if (error) return (
    <div style={{ textAlign: 'center', color: '#EF476F', padding: 60 }}>
      ❌ {error}
      <br />
      <button onClick={load} style={{ marginTop: 12, background: 'rgba(239,71,111,0.1)', color: '#EF476F', border: '1px solid rgba(239,71,111,0.3)', borderRadius: 8, padding: '8px 16px', cursor: 'pointer', fontSize: 13 }}>Tekrar Dene</button>
    </div>
  )
  if (!data) return null

  const filtered = (data.all || []).filter(f =>
    !search || f.code.toLowerCase().includes(search.toLowerCase())
  )

  return (
    <div style={{ padding: '24px 0' }}>

      {/* Başlık + Özet */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 24, flexWrap: 'wrap', gap: 12 }}>
        <div>
          <div style={{ fontSize: 16, fontWeight: 700, color: '#f1f5f9' }}>🤖 TimesFM Tahmin Raporu</div>
          <div style={{ fontSize: 12, color: '#475569', marginTop: 4 }}>
            {data.total} fon analiz edildi · 5 günlük horizon
            {lastUpdated && ` · ${lastUpdated.toLocaleTimeString('tr-TR')}`}
          </div>
        </div>
        <div style={{ display: 'flex', gap: 12, alignItems: 'center', flexWrap: 'wrap' }}>
          {[
            ['Toplam', data.total, '148,163,184'],
            ['↑ Yükseliş', data.upCount, '0,194,168'],
            ['↓ Düşüş', data.downCount, '239,71,111'],
          ].map(([label, val, rgb]) => (
            <div key={label} style={{ textAlign: 'center', background: `rgba(${rgb},0.08)`, border: `1px solid rgba(${rgb},0.2)`, borderRadius: 10, padding: '10px 16px', minWidth: 72 }}>
              <div style={{ fontSize: 20, fontWeight: 800, color: `rgb(${rgb})` }}>{val}</div>
              <div style={{ fontSize: 10, color: '#475569', marginTop: 2 }}>{label}</div>
            </div>
          ))}
          <button onClick={load} style={{ background: 'rgba(0,194,168,0.1)', color: '#00C2A8', border: '1px solid rgba(0,194,168,0.25)', borderRadius: 10, padding: '10px 16px', cursor: 'pointer', fontSize: 12, fontWeight: 600 }}>
            🔄 Yenile
          </button>
        </div>
      </div>

      {/* Top Yükseliş / Düşüş */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20, marginBottom: 24 }}>
        {[
          { title: '🚀 En Yüksek Yükseliş', items: data.topUp, rgb: '0,194,168', color: '#00C2A8' },
          { title: '⚠️ En Yüksek Düşüş', items: data.topDown, rgb: '239,71,111', color: '#EF476F' },
        ].map(({ title, items, rgb, color }) => (
          <div key={title} style={{ background: `rgba(${rgb},0.04)`, border: `1px solid rgba(${rgb},0.18)`, borderRadius: 12, padding: '20px 20px' }}>
            <div style={{ color, fontSize: 12, fontWeight: 700, textTransform: 'uppercase', letterSpacing: 1, marginBottom: 14 }}>{title}</div>
            {items.map((f, i) => (
              <div key={f.code}
                onClick={() => onSelectFund?.(f.code)}
                style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '9px 10px', borderRadius: 8, cursor: 'pointer', transition: 'background 0.15s', background: i % 2 === 0 ? 'rgba(255,255,255,0.02)' : 'transparent' }}
                onMouseEnter={e => e.currentTarget.style.background = `rgba(${rgb},0.08)`}
                onMouseLeave={e => e.currentTarget.style.background = i % 2 === 0 ? 'rgba(255,255,255,0.02)' : 'transparent'}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                  <div style={{ width: 22, height: 22, borderRadius: 6, background: `rgba(${rgb},0.15)`, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 11, color, fontWeight: 700 }}>{i + 1}</div>
                  <span style={{ fontWeight: 700, fontSize: 14 }}>{f.code}</span>
                  <span style={{ fontSize: 15 }}>{f.trendEmoji}</span>
                </div>
                <div style={{ fontWeight: 800, fontSize: 15, color }}>
                  {f.totalChange >= 0 ? '+' : ''}{f.totalChange}%
                </div>
              </div>
            ))}
          </div>
        ))}
      </div>

      {/* Tüm Fonlar */}
      <div style={{ background: '#0f172a', borderRadius: 12, border: '1px solid #1e293b', overflow: 'hidden' }}>
        <div style={{ padding: '14px 20px', borderBottom: '1px solid #1e293b', display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12 }}>
          <div style={{ fontSize: 12, fontWeight: 700, color: '#475569', textTransform: 'uppercase', letterSpacing: 1 }}>
            Tüm Fonlar ({filtered.length})
          </div>
          <input
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="🔍 Fon kodu ara..."
            style={{ background: '#1e293b', border: '1px solid #334155', borderRadius: 7, padding: '6px 12px', color: '#f1f5f9', fontSize: 12, outline: 'none', width: 160 }}
          />
        </div>
        <div style={{ maxHeight: 420, overflowY: 'auto' }}>
          {/* Tablo başlığı */}
          <div style={{ display: 'grid', gridTemplateColumns: '40px 80px 1fr 110px 110px', padding: '8px 20px', borderBottom: '1px solid #1e293b', fontSize: 10, color: '#334155', fontWeight: 700, textTransform: 'uppercase', letterSpacing: 1 }}>
            <div>#</div><div>Kod</div><div>Trend</div><div style={{ textAlign: 'right' }}>5G Fiyat</div><div style={{ textAlign: 'right' }}>Değişim</div>
          </div>
          {filtered.map((f, i) => (
            <div key={f.code}
              onClick={() => onSelectFund?.(f.code)}
              style={{ display: 'grid', gridTemplateColumns: '40px 80px 1fr 110px 110px', padding: '9px 20px', borderBottom: '1px solid #0a0f1e', cursor: 'pointer', alignItems: 'center', transition: 'background 0.12s' }}
              onMouseEnter={e => e.currentTarget.style.background = '#1e293b'}
              onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
            >
              <div style={{ color: '#334155', fontSize: 11 }}>{i + 1}</div>
              <div style={{ fontWeight: 700, fontSize: 13 }}>{f.code}</div>
              <div style={{ fontSize: 16 }}>{f.trendEmoji}</div>
              <div style={{ textAlign: 'right', fontSize: 12, color: '#64748b' }}>{f.day5Price?.toLocaleString('tr-TR', { minimumFractionDigits: 2, maximumFractionDigits: 4 })} ₺</div>
              <div style={{ textAlign: 'right', fontWeight: 700, fontSize: 13, color: f.totalChange >= 0 ? '#00C2A8' : '#EF476F' }}>
                {f.totalChange >= 0 ? '+' : ''}{f.totalChange}%
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

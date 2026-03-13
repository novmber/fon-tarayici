import { useState, useEffect } from 'react'
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, Legend
} from 'recharts'
import { getEvolver, deleteFund } from '../api.js'
import ManualPrice from './ManualPrice.jsx'
import InfoCard from './InfoCard.jsx'
import { getFund } from '../api.js'

const COLORS = ['#00C2A8','#3A86FF','#FFD166','#EF476F','#8338EC','#06D6A0','#FB5607','#FFBE0B','#43AA8B','#F72585']
const ttStyle = { background: '#1e293b', border: 'none', borderRadius: 8, color: '#f1f5f9', fontSize: 12 }

function Badge({ children, color = '#00C2A8' }) {
  return <span style={{ background: `${color}22`, color, borderRadius: 6, padding: '2px 8px', fontSize: 12, fontWeight: 600 }}>{children}</span>
}

function PriceChart({ history }) {
  if (!history || history.length < 2) return (
    <div style={{ color: '#475569', textAlign: 'center', padding: 32 }}>📂 Grafik için en az 2 günlük veri gerekli</div>
  )
  const data = history.slice(-90) // son 90 gün
  return (
    <ResponsiveContainer width="100%" height={240}>
      <LineChart data={data}>
        <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
        <XAxis dataKey="date" tick={{ fill: '#64748b', fontSize: 10 }} interval={Math.floor(data.length / 6)} />
        <YAxis tick={{ fill: '#64748b', fontSize: 10 }} domain={['auto', 'auto']} />
        <Tooltip contentStyle={ttStyle} formatter={v => [`${v?.toFixed(6)} TL`, 'Fiyat']} />
        <Line type="monotone" dataKey="price" stroke="#00C2A8" strokeWidth={2} dot={false} />
      </LineChart>
    </ResponsiveContainer>
  )
}

function PortfolioChart({ items }) {
  if (!items?.length) return <div style={{ color: '#475569', textAlign: 'center', padding: 32 }}>Portföy verisi yok</div>
  const grouped = [
    { name: 'Hisse', value: items.filter(i => i.category === 'equity').reduce((s, i) => s + i.value, 0) },
    { name: 'Borçlanma', value: items.filter(i => i.category === 'bond').reduce((s, i) => s + i.value, 0) },
    { name: 'Repo', value: items.filter(i => i.category === 'repo').reduce((s, i) => s + i.value, 0) },
    { name: 'Mevduat', value: items.filter(i => i.category === 'deposit').reduce((s, i) => s + i.value, 0) },
    { name: 'Fon', value: items.filter(i => i.category === 'fund').reduce((s, i) => s + i.value, 0) },
    { name: 'Emtia', value: items.filter(i => i.category === 'commodity').reduce((s, i) => s + i.value, 0) },
    { name: 'Diğer', value: items.filter(i => i.category === 'other').reduce((s, i) => s + i.value, 0) },
  ].filter(i => i.value > 0.5)
  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20 }}>
      <div>
        <p style={{ color: '#64748b', fontSize: 11, textTransform: 'uppercase', letterSpacing: 1, margin: '0 0 8px' }}>Ana Sınıflar</p>
        <ResponsiveContainer width="100%" height={220}>
          <PieChart>
            <Pie data={grouped} dataKey="value" nameKey="name" cx="50%" cy="50%" innerRadius={50} outerRadius={85} paddingAngle={3}>
              {grouped.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
            </Pie>
            <Tooltip formatter={v => `${v?.toFixed(1)}%`} contentStyle={ttStyle} />
            <Legend wrapperStyle={{ color: '#94a3b8', fontSize: 11 }} />
          </PieChart>
        </ResponsiveContainer>
      </div>
      <div>
        <p style={{ color: '#64748b', fontSize: 11, textTransform: 'uppercase', letterSpacing: 1, margin: '0 0 8px' }}>Detaylı</p>
        <ResponsiveContainer width="100%" height={220}>
          <PieChart>
            <Pie data={items.filter(i => i.value > 0.5)} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={85} paddingAngle={2}>
              {items.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
            </Pie>
            <Tooltip formatter={v => `${v?.toFixed(1)}%`} contentStyle={ttStyle} />
            <Legend wrapperStyle={{ color: '#94a3b8', fontSize: 10 }} />
          </PieChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}

function TwitterPanel({ text, fund, latest, onAnalyze }) {
  const [copied, setCopied] = useState(false)
  const [generating, setGenerating] = useState(false)
  if (!text) return (
    <div style={{ textAlign: 'center', padding: 32 }}>
      <p style={{ color: '#475569', fontSize: 13, marginBottom: 16 }}>Henüz tweet metni yok. TEFAS verisiyle otomatik üretilebilir.</p>
      <button onClick={async () => {
        setGenerating(true)
        await onAnalyze?.()
        setGenerating(false)
      }} disabled={generating} style={{ background: 'rgba(29,155,240,0.15)', color: '#1d9bf0', border: '1px solid rgba(29,155,240,0.3)', borderRadius: 20, padding: '10px 22px', cursor: 'pointer', fontSize: 13, fontWeight: 600 }}>
        {generating ? '⏳ Üretiliyor...' : '𝕏 Tweet Metni Üret'}
      </button>
    </div>
  )
  return (
    <div style={{ maxWidth: 520 }}>
      {/* Kullanım rehberi */}
      <div style={{ background: 'rgba(0,194,168,0.08)', border: '1px solid rgba(0,194,168,0.2)', borderRadius: 12, padding: '12px 16px', marginBottom: 16, fontSize: 12, color: '#94a3b8', lineHeight: 1.6 }}>
        💡 <strong style={{ color: '#00C2A8' }}>Nasıl paylaşılır?</strong> Tweet metnini kopyala → İnfografiği indir → X'te görsel ile birlikte paylaş. Detay görselde, metin kısa kalır.
      </div>
      {/* Tweet önizleme */}
      <div style={{ background: '#0a0a0a', border: '1px solid #2f3336', borderRadius: 16, padding: 20, marginBottom: 12 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 14 }}>
          <div style={{ width: 40, height: 40, borderRadius: '50%', background: 'linear-gradient(135deg,#00C2A8,#118AB2)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 18 }}>📊</div>
          <div>
            <div style={{ color: "#f1f5f9", fontWeight: 700, fontSize: 14 }}>GridBotman</div>
            <div style={{ color: '#64748b', fontSize: 12 }}>@GridBotman</div>
          </div>
        </div>
        <pre style={{ color: '#e7e9ea', fontSize: 14, lineHeight: 1.7, whiteSpace: 'pre-wrap', margin: 0, fontFamily: 'system-ui' }}>{text}</pre>
        {/* Görsel placeholder */}
        <div style={{ marginTop: 14, border: '1px solid #2f3336', borderRadius: 12, padding: '10px 14px', display: 'flex', alignItems: 'center', gap: 10, color: '#64748b', fontSize: 12 }}>
          🖼️ İnfografik görseli buraya eklenir
        </div>
      </div>
      {/* Butonlar */}
      <div style={{ display: 'flex', gap: 10 }}>
        <button onClick={() => {
          try {
            if (navigator.clipboard && window.isSecureContext) {
              navigator.clipboard.writeText(text)
            } else {
              const el = document.createElement('textarea')
              el.value = text
              el.style.position = 'fixed'
              el.style.opacity = '0'
              document.body.appendChild(el)
              el.focus()
              el.select()
              document.execCommand('copy')
              document.body.removeChild(el)
            }
            setCopied(true)
            setTimeout(() => setCopied(false), 2000)
          } catch(e) { console.error(e) }
        }}
          style={{ flex: 1, background: copied ? '#00C2A8' : '#1d9bf0', color: 'white', border: 'none', borderRadius: 20, padding: '10px 22px', cursor: 'pointer', fontSize: 13, fontWeight: 600 }}>
          {copied ? '✓ Kopyalandı!' : "📋 Tweet Metnini Kopyala"}
        </button>
        <button onClick={() => {
          // InfoCard'daki download fonksiyonunu tetikle
          document.getElementById('infografik-download-btn')?.click()
        }}
          style={{ background: 'rgba(255,209,102,0.15)', color: '#FFD166', border: '1px solid rgba(255,209,102,0.3)', borderRadius: 20, padding: '10px 18px', cursor: 'pointer', fontSize: 13, fontWeight: 600 }}>
          🖼️ İnfografik İndir
        </button>
      </div>
    </div>
  )
}

function EvolverPanel({ fundCode }) {
  const [memories, setMemories] = useState([])
  useEffect(() => { getEvolver(fundCode).then(setMemories) }, [fundCode])

  const byType = (t) => memories.filter(m => m.type === t)
  const patterns = byType('price_pattern')
  const insights = byType('insight')
  const priceUpdates = memories.filter(m => m.type === 'price_update' || m.type === 'price_insight')

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
      {patterns.map((p, i) => {
        let data = {}; try { data = JSON.parse(p.content) } catch {}
        return (
          <div key={i} style={{ background: '#1e293b', borderRadius: 12, padding: 16 }}>
            <p style={{ color: '#8338EC', fontSize: 12, fontWeight: 600, margin: '0 0 10px' }}>🔮 Fiyat Analizi ({data.sample_count} gün · güven %{Math.round(p.confidence * 100)})</p>
            {/* Satır 1: Ana metrikler */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: 8, marginBottom: 8 }}>
              {[
                ['Trend', data.trend === 'yukarı' ? '📈 Yukarı' : '📉 Aşağı', data.trend === 'yukarı' ? '#00C2A8' : '#EF476F'],
                ['Ort. Günlük', `${(data.avg_daily_return > 0 ? '+' : '')}${data.avg_daily_return}%`, data.avg_daily_return >= 0 ? '#00C2A8' : '#EF476F'],
                ['Toplam Getiri', `${data.total_return > 0 ? '+' : ''}${data.total_return}%`, data.total_return >= 0 ? '#00C2A8' : '#EF476F'],
              ].map(([l, v, c]) => (
                <div key={l} style={{ background: '#0f172a', borderRadius: 8, padding: '10px 12px' }}>
                  <div style={{ color: '#64748b', fontSize: 10 }}>{l}</div>
                  <div style={{ color: c, fontWeight: 700, fontSize: 14, marginTop: 2 }}>{v}</div>
                </div>
              ))}
            </div>
            {/* Satır 2: Risk metrikleri */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: 8, marginBottom: 8 }}>
              {[
                ['Yıllık Volatilite', `${data.annual_volatility}%`, '#FFD166'],
                ['Max Drawdown', `-${data.max_drawdown}%`, '#EF476F'],
                ['Sharpe Oranı', data.sharpe_ratio != null ? data.sharpe_ratio.toFixed(2) : '—', data.sharpe_ratio >= 1 ? '#00C2A8' : data.sharpe_ratio >= 0 ? '#FFD166' : '#EF476F'],
              ].map(([l, v, c]) => (
                <div key={l} style={{ background: '#0f172a', borderRadius: 8, padding: '10px 12px' }}>
                  <div style={{ color: '#64748b', fontSize: 10 }}>{l}</div>
                  <div style={{ color: c, fontWeight: 700, fontSize: 14, marginTop: 2 }}>{v}</div>
                </div>
              ))}
            </div>
            {/* Satır 3: Momentum + pozitif gün */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: 8, marginBottom: 8 }}>
              {[
                ['Momentum (30g)', `${data.momentum_30d > 0 ? '+' : ''}${data.momentum_30d}%`, data.momentum_30d >= 0 ? '#00C2A8' : '#EF476F'],
                ['Pozitif Gün', `%${data.positive_days_pct}`, data.positive_days_pct >= 50 ? '#00C2A8' : '#EF476F'],
                ['Güncel Fiyat', `${data.latest_price?.toFixed(4)} ₺`, '#94a3b8'],
              ].map(([l, v, c]) => (
                <div key={l} style={{ background: '#0f172a', borderRadius: 8, padding: '10px 12px' }}>
                  <div style={{ color: '#64748b', fontSize: 10 }}>{l}</div>
                  <div style={{ color: c, fontWeight: 700, fontSize: 14, marginTop: 2 }}>{v}</div>
                </div>
              ))}
            </div>
            {/* En iyi / kötü ay */}
            {(data.best_month || data.worst_month) && (
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                {data.best_month && (
                  <div style={{ background: 'rgba(0,194,168,0.08)', border: '1px solid rgba(0,194,168,0.2)', borderRadius: 8, padding: '10px 12px' }}>
                    <div style={{ color: '#64748b', fontSize: 10 }}>🏆 En İyi Ay</div>
                    <div style={{ color: '#00C2A8', fontWeight: 700, fontSize: 13, marginTop: 2 }}>{data.best_month.month} · +{data.best_month.return}%</div>
                  </div>
                )}
                {data.worst_month && (
                  <div style={{ background: 'rgba(239,71,111,0.08)', border: '1px solid rgba(239,71,111,0.2)', borderRadius: 8, padding: '10px 12px' }}>
                    <div style={{ color: '#64748b', fontSize: 10 }}>📉 En Kötü Ay</div>
                    <div style={{ color: '#EF476F', fontWeight: 700, fontSize: 13, marginTop: 2 }}>{data.worst_month.month} · {data.worst_month.return}%</div>
                  </div>
                )}
              </div>
            )}
          </div>
        )
      })}

      {insights.length > 0 && (
        <div style={{ background: '#1e293b', borderRadius: 12, padding: 16 }}>
          <p style={{ color: '#00C2A8', fontSize: 12, fontWeight: 600, margin: '0 0 10px' }}>🧠 Tekrar Eden Tespitler</p>
          {insights.map((ins, i) => (
            <div key={i} style={{ display: 'flex', gap: 8, marginBottom: 8, alignItems: 'flex-start' }}>
              <div style={{ width: 5, height: 5, borderRadius: '50%', background: '#00C2A8', marginTop: 6, flexShrink: 0 }} />
              <div>
                <div style={{ color: '#cbd5e1', fontSize: 13 }}>{ins.content}</div>
                <div style={{ color: '#475569', fontSize: 11, marginTop: 2 }}>{ins.occurrenceCount}x · güven %{Math.round(ins.confidence*100)}</div>
              </div>
            </div>
          ))}
        </div>
      )}

      {priceUpdates.length > 0 && (
        <div style={{ background: '#1e293b', borderRadius: 12, padding: 16 }}>
          <p style={{ color: '#8338EC', fontSize: 12, fontWeight: 600, margin: '0 0 10px' }}>📡 Manuel Fiyat Öğrenimi</p>
          {priceUpdates.map((p, i) => (
            <div key={i} style={{ color: '#cbd5e1', fontSize: 13, marginBottom: 6 }}>
              {p.type === 'price_insight' ? p.content : (() => {
                try { const d = JSON.parse(p.content); return `PDF: ${d.pdf_price?.toFixed(4)} → Güncel: ${d.current_price?.toFixed(4)} TL (${d.change_pct > 0 ? '+' : ''}${d.change_pct}%)` } catch { return p.content }
              })()}
            </div>
          ))}
        </div>
      )}

      {/* Sinyaller */}
      {byType('signal').map((s, i) => {
        let data = {}; try { data = JSON.parse(s.content) } catch {}
        const signals = data.signals || []
        const colorMap = { pozitif: '#00C2A8', negatif: '#EF476F', uyarı: '#FFD166' }
        const iconMap = { pozitif: '✅', negatif: '🔴', uyarı: '⚠️' }
        return (
          <div key={i} style={{ background: '#1e293b', borderRadius: 12, padding: 16 }}>
            <p style={{ color: '#3A86FF', fontSize: 12, fontWeight: 600, margin: '0 0 12px' }}>
              🧠 Öğrenilen Sinyaller ({data.snapshot_count} snapshot)
            </p>
            {/* Trend özeti */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2,1fr)', gap: 8, marginBottom: 12 }}>
              {[
                ['Sharpe Trendi', data.sharpe_trend],
                ['Momentum', data.momentum_trend],
                ['Volatilite', data.volatility_trend],
                ['Drawdown', data.drawdown_trend],
              ].map(([l, v]) => (
                <div key={l} style={{ background: '#0f172a', borderRadius: 8, padding: '8px 12px', display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: '#64748b', fontSize: 11 }}>{l}</span>
                  <span style={{ color: v === 'artıyor' || v === 'güçleniyor' || v === 'iyileşiyor' ? '#00C2A8' : v === 'azalıyor' || v === 'zayıflıyor' || v === 'kötüleşiyor' ? '#EF476F' : '#FFD166', fontSize: 11, fontWeight: 700 }}>{v}</span>
                </div>
              ))}
            </div>
            {/* Sinyaller */}
            {signals.length > 0 ? signals.map((sig, j) => (
              <div key={j} style={{ display: 'flex', gap: 8, marginBottom: 8, alignItems: 'flex-start', background: '#0f172a', borderRadius: 8, padding: '10px 12px' }}>
                <span style={{ fontSize: 14 }}>{iconMap[sig.type] || '•'}</span>
                <span style={{ color: colorMap[sig.type] || '#94a3b8', fontSize: 12 }}>{sig.msg}</span>
              </div>
            )) : (
              <div style={{ color: '#475569', fontSize: 12 }}>Henüz sinyal üretilmedi — daha fazla snapshot gerekiyor.</div>
            )}
            <div style={{ color: '#334155', fontSize: 10, marginTop: 8 }}>Güven: %{Math.round(s.confidence * 100)} · {s.occurrenceCount}x güncellendi</div>
          </div>
        )
      })}

      {memories.length === 0 && (
        <div style={{ color: '#475569', fontSize: 13, textAlign: 'center', padding: 32 }}>
          🤖 Evolver henüz öğrenmedi. TEFAS verisi çekildikçe otomatik öğrenir.
        </div>
      )}
    </div>
  )
}


function RiskScoreInput({ fundCode, onSaved }) {
  const [editing, setEditing] = useState(false)
  const [val, setVal] = useState('')
  const [saving, setSaving] = useState(false)

  const save = async () => {
    const r = parseInt(val)
    if (!r || r < 1 || r > 7) return
    setSaving(true)
    try {
      await fetch(`/api/funds/${fundCode}/set-risk`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ risk_score: r })
      })
      onSaved(r)
      setEditing(false)
    } catch(e) { console.error(e) }
    setSaving(false)
  }

  if (!editing) return (
    <div onClick={() => setEditing(true)} style={{ color: '#64748b', fontWeight: 700, fontSize: 14, marginTop: 3, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 4 }}>
      <span>—</span><span style={{ fontSize: 10, color: '#475569' }}>✏️ gir</span>
    </div>
  )

  return (
    <div style={{ display: 'flex', gap: 4, marginTop: 3 }}>
      <input type="number" min="1" max="7" value={val} onChange={e => setVal(e.target.value)}
        style={{ width: 40, background: '#0f172a', border: '1px solid #334155', color: '#f1f5f9', borderRadius: 4, padding: '2px 4px', fontSize: 13 }}
        autoFocus placeholder="1-7" />
      <button onClick={save} disabled={saving}
        style={{ background: '#10b981', border: 'none', color: '#fff', borderRadius: 4, padding: '2px 8px', fontSize: 12, cursor: 'pointer' }}>
        {saving ? '...' : '✓'}
      </button>
      <button onClick={() => setEditing(false)}
        style={{ background: '#334155', border: 'none', color: '#94a3b8', borderRadius: 4, padding: '2px 6px', fontSize: 12, cursor: 'pointer' }}>✕</button>
    </div>
  )
}

export default function FundDetail({ fundCode, onClose, onDeleteFund, onRefresh }) {
  const [fund, setFund] = useState(null)
  const [tab, setTab] = useState('trend')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    getFund(fundCode).then(f => { setFund(f); setLoading(false) })
  }, [fundCode])

  const [refreshing, setRefreshing] = useState(false)
  const [analyzing, setAnalyzing] = useState(false)
  const handleRefresh = async () => {
    setRefreshing(true)
    await onRefresh?.(fundCode)
    const f = await getFund(fundCode)
    setFund(f)
    setRefreshing(false)
  }
  if (loading) return (
    <div onClick={onClose} style={{ position: 'fixed', inset: 0, background: 'rgba(2,8,23,0.93)', zIndex: 100, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <div style={{ color: '#00C2A8', fontSize: 16 }}>⏳ Yükleniyor...</div>
    </div>
  )
  if (!fund) return null

  const tabs = [
    { id: 'trend', label: '📈 Fiyat Trendi' },
    { id: 'portfolio', label: '🥧 Portföy' },
    { id: 'infografik', label: '🖼️ İnfografik' },
    { id: 'canli', label: '📡 Canlı Fiyat' },
    { id: 'dexter', label: '🤖 Dexter' },
    { id: 'evolver', label: '🔮 Evolver' },
    { id: 'twitter', label: '𝕏 Tweet' },
  ]

  // Sekmeler için latest benzeri obje
  const latest = {
    unitPrice: fund.unitPrice, totalValue: fund.totalValue,
    participantCount: fund.participantCount, monthlyReturn: fund.monthlyReturn,
    yearlyReturn: fund.yearlyReturn, avgMaturity: fund.avgMaturity,
    monthlyTurnover: fund.monthlyTurnover, riskScore: fund.riskScore,
    stopajRate: fund.stopajRate, valor: fund.valor, fundType: fund.fundType,
    portfolioItems: fund.portfolioItems, topHoldings: fund.topHoldings,
    expenses: fund.expenses, month: fund.latestDate,
  }

  return (
    <div onClick={e => e.target === e.currentTarget && onClose()} style={{ position: 'fixed', inset: 0, background: 'rgba(2,8,23,0.93)', zIndex: 100, display: 'flex', alignItems: 'flex-start', justifyContent: 'center', overflowY: 'auto', padding: '32px 16px' }}>
      <div style={{ background: '#0f172a', border: '1px solid #1e293b', borderRadius: 20, width: '100%', maxWidth: 920 }}>

        {/* Header */}
        <div style={{ padding: '20px 26px 14px', borderBottom: '1px solid #1e293b', display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6, flexWrap: 'wrap' }}>
              <span style={{ background: '#1e293b', color: '#00C2A8', borderRadius: 8, padding: '3px 10px', fontSize: 13, fontWeight: 700 }}>{fund.code}</span>
              {fund.monthlyReturn != null && <Badge color={fund.monthlyReturn >= 0 ? '#00C2A8' : '#EF476F'}>{fund.monthlyReturn >= 0 ? '+' : ''}{fund.monthlyReturn}% aylık</Badge>}
              {fund.yearlyReturn != null && <Badge color="#FFD166">+{fund.yearlyReturn}% yıllık</Badge>}
              {fund.hasPdfAnalysis && <Badge color="#FFD166">📄 AI Analiz</Badge>}
              <span style={{ color: '#475569', fontSize: 12 }}>{fund.totalDays} gün veri</span>
            </div>
            <h2 style={{ margin: '0 0 3px', fontSize: 17, fontWeight: 700, color: '#f1f5f9' }}>{fund.name}</h2>
            <p style={{ margin: 0, color: '#64748b', fontSize: 12 }}>Son güncelleme: {fund.latestDate}</p>
          </div>
          <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
            <button onClick={handleRefresh} disabled={refreshing} style={{ background: 'rgba(0,194,168,0.1)', color: '#00C2A8', border: '1px solid rgba(0,194,168,0.2)', borderRadius: 8, padding: '6px 12px', cursor: 'pointer', fontSize: 12 }}>{refreshing ? '⏳ Güncelleniyor...' : '🔄 Güncelle'}</button>
            <button onClick={async () => {
              const isPublished = fund.published === 1
              await fetch(`/api/funds/${fund.code}/publish?published=${isPublished ? 'false' : 'true'}`, { method: 'POST' })
              window.location.reload()
            }} style={{ background: fund.published === 1 ? 'rgba(0,200,100,0.15)' : 'rgba(100,100,100,0.15)', color: fund.published === 1 ? '#00C864' : '#64748b', border: `1px solid ${fund.published === 1 ? 'rgba(0,200,100,0.3)' : 'rgba(100,100,100,0.2)'}`, borderRadius: 8, padding: '6px 12px', cursor: 'pointer', fontSize: 12, fontWeight: 600 }}>
              {fund.published === 1 ? '🌐 Yayında' : '📤 Yayınla'}
            </button>
            <button onClick={() => { if (confirm(`${fund.code} silinsin?`)) { onDeleteFund(fund.code) } }} style={{ background: 'rgba(239,71,111,0.1)', color: '#EF476F', border: '1px solid rgba(239,71,111,0.3)', borderRadius: 8, padding: '6px 12px', cursor: 'pointer', fontSize: 12 }}>Sil</button>
            <button onClick={onClose} style={{ background: '#1e293b', border: 'none', color: '#94a3b8', borderRadius: 8, width: 32, height: 32, cursor: 'pointer', fontSize: 16 }}>✕</button>
          </div>
        </div>

        {/* Metrikler */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: 10, padding: '14px 26px' }}>
          {[
            { label: 'Pay Fiyatı (TEFAS)', value: (() => { const p = fund.unitPrice; if (!p) return '—'; const fmt = (n, dec) => { const parts = n.toFixed(dec).split('.'); parts[0] = parts[0].replace(/\B(?=(\d{3})+(?!\d))/g, '.'); return parts.join(','); }; if (p >= 100) return fmt(p, 2) + ' TL'; if (p >= 1) return fmt(p, 4) + ' TL'; return fmt(p, 6) + ' TL'; })() },
            { label: 'Portföy', value: fund.totalValue ? (fund.totalValue >= 1e9 ? `₺${(fund.totalValue/1e9).toFixed(2)}B` : `₺${(fund.totalValue/1e6).toFixed(1)}M`) : '—' },
            { label: 'Yatırımcı', value: fund.participantCount ? fund.participantCount.toLocaleString('tr-TR', {maximumFractionDigits:0}) : '—' },
            { label: fund.avgMaturity ? 'Ort. Vade' : 'Risk Skoru', value: fund.avgMaturity ? `${fund.avgMaturity} gün` : fund.riskScore ? `${fund.riskScore}/7` : '—', editable: !fund.avgMaturity && !fund.riskScore },
          ].map((m, i) => (
            <div key={i} style={{ background: '#1e293b', borderRadius: 10, padding: '11px 13px' }}>
              <div style={{ color: '#64748b', fontSize: 10, textTransform: 'uppercase', letterSpacing: 0.8 }}>{m.label}</div>
              {m.editable ? (
                <RiskScoreInput fundCode={fund.code} onSaved={(r) => setFund(f => ({...f, riskScore: r}))} />
              ) : (
                <div style={{ color: '#f1f5f9', fontWeight: 700, fontSize: 14, marginTop: 3 }}>{m.value}</div>
              )}
            </div>
          ))}
        </div>

        {/* Tabs */}
        <div style={{ display: 'flex', borderBottom: '1px solid #1e293b', paddingLeft: 18, overflowX: 'auto' }}>
          {tabs.map(t => (
            <button key={t.id} onClick={() => setTab(t.id)} style={{
              background: 'none', border: 'none',
              borderBottom: tab === t.id ? '2px solid #00C2A8' : '2px solid transparent',
              color: tab === t.id ? '#00C2A8' : '#64748b',
              padding: '10px 13px', cursor: 'pointer', fontSize: 13, fontWeight: 600, whiteSpace: 'nowrap',
            }}>{t.label}</button>
          ))}
        </div>

        {/* Tab içeriği */}
        <div style={{ padding: '20px 26px 28px' }}>
          {tab === 'trend' && (
            <div>
              <p style={{ color: '#64748b', fontSize: 12, textTransform: 'uppercase', letterSpacing: 1, margin: '0 0 12px' }}>
                Pay Fiyatı — Son 90 Gün ({fund.totalDays} gün kayıt)
              </p>
              <PriceChart history={fund.priceHistory} />

              {/* PDF analizleri listesi */}
              {fund.pdfAnalyses?.length > 0 && (
                <div style={{ marginTop: 20 }}>
                  <p style={{ color: '#64748b', fontSize: 12, textTransform: 'uppercase', letterSpacing: 1, margin: '0 0 12px' }}>📄 PDF Analizleri</p>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                    {fund.pdfAnalyses.map((a, i) => (
                      <div key={i} style={{ background: '#1e293b', borderRadius: 10, padding: '12px 16px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <div style={{ color: '#94a3b8', fontSize: 13 }}>{a.dateKey} ({a.monthKey})</div>
                        <div style={{ display: 'flex', gap: 12 }}>
                          {a.monthlyReturn != null && <span style={{ color: a.monthlyReturn >= 0 ? '#00C2A8' : '#EF476F', fontWeight: 700 }}>{a.monthlyReturn >= 0 ? '+' : ''}{a.monthlyReturn}% aylık</span>}
                          {a.yearlyReturn != null && <span style={{ color: '#FFD166', fontWeight: 600 }}>{a.yearlyReturn}% yıllık</span>}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {tab === 'portfolio' && <PortfolioChart items={fund.portfolioItems} />}

          {tab === 'infografik' && <InfoCard fund={fund} latest={latest} priceHistory={fund.priceHistory} />}

          {tab === 'canli' && (
            <ManualPrice
              fundCode={fund.code}
              fundName={fund.name}
              pdfPrice={fund.unitPrice}
              pdfMonth={fund.latestDate}
            />
          )}

          {tab === 'dexter' && (
            <div>
              <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 12 }}>
                <button
                  onClick={async () => {
                    setAnalyzing(true)
                    try {
                      const res = await fetch(`/api/funds/${fund.code}/analyze-tefas`, { method: 'POST' })
                      const data = await res.json()
                      const f = await getFund(fund.code)
                      setFund(f)
                    } catch(e) { console.error(e) }
                    setAnalyzing(false)
                  }}
                  disabled={analyzing}
                  style={{ background: 'rgba(0,194,168,0.1)', color: '#00C2A8', border: '1px solid rgba(0,194,168,0.3)', borderRadius: 8, padding: '7px 14px', cursor: 'pointer', fontSize: 12, fontWeight: 600 }}
                >
                  {analyzing ? '⏳ Analiz ediliyor...' : '🤖 TEFAS ile Analiz Et'}
                </button>
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
                <div style={{ background: '#1e293b', borderRadius: 12, padding: 16 }}>
                  <p style={{ color: '#00C2A8', fontSize: 13, fontWeight: 600, margin: '0 0 12px' }}>🧠 AI Tespitleri</p>
                  {(fund.aiInsights || []).length > 0 ? fund.aiInsights.map((ins, i) => (
                    <div key={i} style={{ display: 'flex', gap: 8, marginBottom: 10 }}>
                      <div style={{ width: 5, height: 5, borderRadius: '50%', background: '#00C2A8', marginTop: 7, flexShrink: 0 }} />
                      <p style={{ color: '#cbd5e1', fontSize: 13, lineHeight: 1.6, margin: 0 }}>{ins}</p>
                    </div>
                  )) : <p style={{ color: '#475569', fontSize: 13 }}>Henüz analiz yok</p>}
                </div>
                <div style={{ background: '#1e293b', borderRadius: 12, padding: 16 }}>
                  <p style={{ color: '#FFD166', fontSize: 13, fontWeight: 600, margin: '0 0 12px' }}>⚡ Dexter Önerileri</p>
                  {(fund.dexterRecommendations || []).length > 0 ? fund.dexterRecommendations.map((rec, i) => (
                    <div key={i} style={{ display: 'flex', gap: 8, marginBottom: 10 }}>
                      <div style={{ width: 5, height: 5, borderRadius: '50%', background: '#FFD166', marginTop: 7, flexShrink: 0 }} />
                      <p style={{ color: '#cbd5e1', fontSize: 13, lineHeight: 1.6, margin: 0 }}>{rec}</p>
                    </div>
                  )) : <p style={{ color: '#475569', fontSize: 13 }}>Henüz öneri yok</p>}
                </div>
              </div>
            </div>
          )}

          {tab === 'evolver' && <EvolverPanel fundCode={fund.code} />}

          {tab === 'twitter' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
              <TwitterPanel text={fund.twitterSummary} fund={fund} latest={latest} onAnalyze={async () => { setAnalyzing(true); try { await fetch(`/api/funds/${fund.code}/analyze-tefas`, { method: "POST" }); const f = await getFund(fund.code); setFund(f); } catch(e) { console.error(e) } setAnalyzing(false); }} />
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

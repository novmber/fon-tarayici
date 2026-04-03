import { useState, useEffect, useCallback } from 'react'
import { getFunds, trackFund, refreshFund, analyzePDF, deleteFund, getStats } from './api.js'
import FundCard from './components/FundCard.jsx'
import FundDetail from './components/FundDetail.jsx'
import Top5 from './components/Top5.jsx'
import DailyTweets from './components/DailyTweets.jsx'

export default function App() {
  const [funds, setFunds] = useState([])
  const [stats, setStats] = useState({})
  const [selected, setSelected] = useState(null)
  const [loading, setLoading] = useState(true)
  const [trackInput, setTrackInput] = useState('')
  const [trackLoading, setTrackLoading] = useState(false)
  const [trackMsg, setTrackMsg] = useState(null)
  const [pdfFundCode, setPdfFundCode] = useState('')
  const [pdfLoading, setPdfLoading] = useState(false)
  const [pdfMsg, setPdfMsg] = useState(null)
  const [showAdd, setShowAdd] = useState(false)
  const [search, setSearch] = useState('')
  const [filterType, setFilterType] = useState('Tümü')
  const [filterRisk, setFilterRisk] = useState('Tümü')
  const [sortBy, setSortBy] = useState('name')
  const [viewMode, setViewMode] = useState('list') // 'list' | 'compare'
  const [compareA, setCompareA] = useState('')
  const [compareB, setCompareB] = useState('')

  const load = useCallback(async () => {
    try {
      const [f, s] = await Promise.all([getFunds(), getStats()])
      setFunds(f)
      setStats(s)
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])
  
  // Her 5 dakikada bir otomatik güncelle
  useEffect(() => {
    const interval = setInterval(() => { load() }, 5 * 60 * 1000)
    return () => clearInterval(interval)
  }, [load])

  const handleTrack = async () => {
    const code = trackInput.trim().toUpperCase()
    if (!code) return
    setTrackLoading(true)
    setTrackMsg(null)
    try {
      const res = await trackFund(code)
      setTrackMsg({ ok: true, text: `✅ ${res.fundName} — ${res.newRows} yeni gün eklendi (toplam ${res.totalRows})` })
      setTrackInput('')
      await load()
    } catch (e) {
      setTrackMsg({ ok: false, text: `❌ ${e.message}` })
    } finally {
      setTrackLoading(false)
    }
  }

  const handleRefresh = async (code) => {
    try {
      const res = await refreshFund(code)
      await load()
      return res
    } catch (e) {
      console.error(e)
    }
  }

  const handlePDF = async (e) => {
    const file = e.target.files?.[0]
    if (!file || !pdfFundCode.trim()) return
    setPdfLoading(true)
    setPdfMsg(null)
    try {
      const res = await analyzePDF(pdfFundCode.trim().toUpperCase(), file)
      setPdfMsg({ ok: true, text: `✅ ${res.fundCode} ${res.month} analiz tamamlandı` })
      await load()
    } catch (err) {
      setPdfMsg({ ok: false, text: `❌ ${err.message}` })
    } finally {
      setPdfLoading(false)
      e.target.value = ''
    }
  }

  const handleDelete = async (code) => {
    await deleteFund(code)
    setSelected(null)
    await load()
  }

  const sBtn = (onClick, label, color = '#00C2A8', disabled = false) => (
    <button onClick={onClick} disabled={disabled} style={{
      background: disabled ? '#1e293b' : color === 'red' ? 'rgba(239,71,111,0.15)' : `${color}22`,
      color: disabled ? '#475569' : color === 'red' ? '#EF476F' : color,
      border: `1px solid ${disabled ? '#1e293b' : color === 'red' ? 'rgba(239,71,111,0.3)' : `${color}44`}`,
      borderRadius: 8, padding: '8px 16px', cursor: disabled ? 'default' : 'pointer',
      fontSize: 13, fontWeight: 600, transition: 'all 0.15s',
    }}>{label}</button>
  )

  return (
    <div style={{ minHeight: '100vh', background: '#020817', color: '#f1f5f9', fontFamily: 'Space Grotesk, system-ui, sans-serif' }}>

      {/* Header */}
      <div style={{ borderBottom: '1px solid #1e293b', padding: '16px 28px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 16 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <div style={{ width: 36, height: 36, borderRadius: 10, background: 'linear-gradient(135deg,#00C2A8,#118AB2)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 18 }}>📊</div>
          <div>
            <div style={{ fontWeight: 800, fontSize: 18, letterSpacing: -0.5 }}>Fon Tarayıcı</div>
            <div style={{ color: '#475569', fontSize: 11 }}>TEFAS · KAP · Evolver AI</div>
          </div>
        </div>

        {/* Stats */}
        <div style={{ display: 'flex', gap: 20, alignItems: 'center' }}>
          {[
            ['Fon', stats.totalFunds || 0, '#00C2A8'],
            ['Gün Kaydı', stats.totalRecords || 0, '#3A86FF'],
            ['PDF Analiz', stats.pdfAnalyses || 0, '#FFD166'],
            ['Evolver', stats.evolverMemories || 0, '#8338EC'],
          ].map(([label, val, color]) => (
            <div key={label} style={{ textAlign: 'center' }}>
              <div style={{ color, fontWeight: 700, fontSize: 16 }}>{val}</div>
              <div style={{ color: '#475569', fontSize: 10 }}>{label}</div>
            </div>
          ))}
        </div>

        {/* Fon Ekle butonu */}
        <div style={{ display: 'flex', gap: 8 }}>
          <button onClick={() => setViewMode(viewMode === 'top5' ? 'list' : 'top5')}
            style={{ background: viewMode === 'top5' ? 'rgba(255,209,102,0.15)' : 'rgba(255,255,255,0.05)', color: viewMode === 'top5' ? '#FFD166' : '#94a3b8', border: `1px solid ${viewMode === 'top5' ? 'rgba(255,209,102,0.3)' : 'rgba(255,255,255,0.1)'}`, borderRadius: 8, padding: '7px 14px', cursor: 'pointer', fontSize: 12, fontWeight: 600 }}>
            🏆 {viewMode === 'top5' ? 'Listeye Dön' : 'Top 10'}
          </button>
          <button onClick={() => setViewMode(viewMode === 'tweets' ? 'list' : 'tweets')}
            style={{ background: viewMode === 'tweets' ? 'rgba(29,161,242,0.15)' : 'rgba(255,255,255,0.05)', color: viewMode === 'tweets' ? '#1da1f2' : '#94a3b8', border: `1px solid ${viewMode === 'tweets' ? 'rgba(29,161,242,0.3)' : 'rgba(255,255,255,0.1)'}`, borderRadius: 8, padding: '7px 14px', cursor: 'pointer', fontSize: 12, fontWeight: 600 }}>
            🐦 {viewMode === 'tweets' ? 'Listeye Dön' : 'Tweetler'}
          </button>
          <button onClick={() => setViewMode(viewMode === 'compare' ? 'list' : 'compare')}
            style={{ background: viewMode === 'compare' ? 'rgba(255,209,102,0.15)' : 'rgba(255,255,255,0.05)', color: viewMode === 'compare' ? '#FFD166' : '#94a3b8', border: `1px solid ${viewMode === 'compare' ? 'rgba(255,209,102,0.3)' : 'rgba(255,255,255,0.1)'}`, borderRadius: 8, padding: '7px 14px', cursor: 'pointer', fontSize: 12, fontWeight: 600 }}>
            ⚖️ {viewMode === 'compare' ? 'Listeye Dön' : 'Kıyasla'}
          </button>
          {sBtn(() => setShowAdd(!showAdd), showAdd ? '✕ Kapat' : '+ Fon Ekle')}
        </div>
      </div>

      {/* Fon Ekle / PDF Panel */}
      {showAdd && (
        <div style={{ background: '#0f172a', borderBottom: '1px solid #1e293b', padding: '20px 28px', display: 'flex', gap: 32, flexWrap: 'wrap' }}>

          {/* TEFAS takip */}
          <div style={{ flex: 1, minWidth: 280 }}>
            <div style={{ color: '#00C2A8', fontSize: 12, fontWeight: 600, textTransform: 'uppercase', letterSpacing: 1, marginBottom: 10 }}>
              📡 Fon Kodu ile Takip Et
            </div>
            <div style={{ color: '#475569', fontSize: 12, marginBottom: 12, lineHeight: 1.5 }}>
              TEFAS'tan son 365 günlük fiyat + portföy verisi otomatik çekilir.
            </div>
            <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
              <input
                value={trackInput}
                onChange={e => setTrackInput(e.target.value.toUpperCase())}
                onKeyDown={e => e.key === 'Enter' && handleTrack()}
                placeholder="Örn: PBR, TLY, MTH"
                style={{
                  background: '#1e293b', border: '1px solid #334155', borderRadius: 8,
                  padding: '10px 14px', color: '#f1f5f9', fontSize: 14, width: 160, outline: 'none',
                  textTransform: 'uppercase', letterSpacing: 1,
                }}
              />
              <button onClick={handleTrack} disabled={!trackInput || trackLoading} style={{
                background: trackInput && !trackLoading ? '#00C2A8' : '#1e293b',
                color: trackInput && !trackLoading ? '#020817' : '#475569',
                border: 'none', borderRadius: 8, padding: '10px 20px',
                cursor: trackInput && !trackLoading ? 'pointer' : 'default',
                fontSize: 13, fontWeight: 700,
              }}>
                {trackLoading ? '⏳ Çekiliyor...' : 'Ekle'}
              </button>
            </div>
            {trackMsg && (
              <div style={{ marginTop: 10, fontSize: 12, color: trackMsg.ok ? '#00C2A8' : '#EF476F' }}>
                {trackMsg.text}
              </div>
            )}
          </div>

          {/* PDF analiz */}
          <div style={{ flex: 1, minWidth: 280, borderLeft: '1px solid #1e293b', paddingLeft: 32 }}>
            <div style={{ color: '#FFD166', fontSize: 12, fontWeight: 600, textTransform: 'uppercase', letterSpacing: 1, marginBottom: 10 }}>
              📄 PDF ile Derin Analiz (Opsiyonel)
            </div>
            <div style={{ color: '#475569', fontSize: 12, marginBottom: 12, lineHeight: 1.5 }}>
              KAP'tan indirdiğiniz aylık portföy raporunu yükleyin. AI; getiri, risk, Dexter önerileri üretir.
            </div>
            <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
              <input
                value={pdfFundCode}
                onChange={e => setPdfFundCode(e.target.value.toUpperCase())}
                placeholder="Fon Kodu (PBR)"
                style={{
                  background: '#1e293b', border: '1px solid #334155', borderRadius: 8,
                  padding: '10px 14px', color: '#f1f5f9', fontSize: 13, width: 110, outline: 'none',
                  textTransform: 'uppercase',
                }}
              />
              <label style={{
                background: pdfFundCode && !pdfLoading ? 'rgba(255,209,102,0.15)' : '#1e293b',
                color: pdfFundCode && !pdfLoading ? '#FFD166' : '#475569',
                border: `1px solid ${pdfFundCode && !pdfLoading ? 'rgba(255,209,102,0.3)' : '#1e293b'}`,
                borderRadius: 8, padding: '10px 16px', cursor: pdfFundCode && !pdfLoading ? 'pointer' : 'default',
                fontSize: 13, fontWeight: 600,
              }}>
                {pdfLoading ? '⏳ Analiz ediliyor...' : '📂 PDF Seç'}
                <input type="file" accept=".pdf" onChange={handlePDF} style={{ display: 'none' }} disabled={!pdfFundCode || pdfLoading} />
              </label>
            </div>
            {pdfMsg && (
              <div style={{ marginTop: 10, fontSize: 12, color: pdfMsg.ok ? '#00C2A8' : '#EF476F' }}>
                {pdfMsg.text}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Fon Grid */}
      <div style={{ padding: '24px 28px' }}>
        {loading ? (
          <div style={{ textAlign: 'center', color: '#475569', padding: 60, fontSize: 14 }}>
            ⏳ Yükleniyor...
          </div>
        ) : funds.length === 0 ? (
          <div style={{ textAlign: 'center', padding: 80 }}>
            <div style={{ fontSize: 48, marginBottom: 16 }}>📡</div>
            <div style={{ color: '#475569', fontSize: 16, marginBottom: 8 }}>Henüz fon eklenmedi</div>
            <div style={{ color: '#334155', fontSize: 13 }}>
              Yukarıdaki "+ Fon Ekle" butonundan TEFAS fon kodu girin
            </div>
          </div>
        ) : (
          <>{/* Arama + Filtre Bar */}
          <div style={{ display: 'flex', gap: 10, marginBottom: 20, flexWrap: 'wrap', alignItems: 'center' }}>
            <input
              value={search}
              onChange={e => setSearch(e.target.value)}
              placeholder="🔍  Fon kodu veya adı..."
              style={{
                background: '#1e293b', border: '1px solid #334155', borderRadius: 8,
                padding: '9px 14px', color: '#f1f5f9', fontSize: 13, outline: 'none',
                minWidth: 220, flex: 1,
              }}
            />
            {[
              ['Tür', filterType, setFilterType, ['Tümü', 'Hisse Senedi Fonu', 'Serbest Fon', 'Para Piyasası Fonu', 'Borçlanma Araçları Fonu', 'Katılım Fonu', 'Değişken Fon']],
              ['Risk', filterRisk, setFilterRisk, ['Tümü', '1', '2', '3', '4', '5', '6', '7']],
            ].map(([label, val, setter, opts]) => (
              <select key={label} value={val} onChange={e => setter(e.target.value)} style={{
                background: '#1e293b', border: '1px solid #334155', borderRadius: 8,
                padding: '9px 12px', color: val === 'Tümü' ? '#64748b' : '#f1f5f9',
                fontSize: 13, outline: 'none', cursor: 'pointer',
              }}>
                {opts.map(o => <option key={o} value={o}>{label}: {o}</option>)}
              </select>
            ))}
            <select value={sortBy} onChange={e => setSortBy(e.target.value)} style={{
              background: '#1e293b', border: '1px solid #334155', borderRadius: 8,
              padding: '9px 12px', color: '#f1f5f9', fontSize: 13, outline: 'none', cursor: 'pointer',
            }}>
              <option value="name">Sırala: İsim</option>
              <option value="monthlyReturn">Sırala: Aylık Getiri</option>
              <option value="yearlyReturn">Sırala: Yıllık Getiri</option>
              <option value="totalValue">Sırala: Portföy Büyüklüğü</option>
              <option value="participantCount">Sırala: Yatırımcı Sayısı</option>
              <option value="riskScore">Sırala: Risk</option>
            </select>
            {(search || filterType !== 'Tümü' || filterRisk !== 'Tümü') && (
              <button onClick={() => { setSearch(''); setFilterType('Tümü'); setFilterRisk('Tümü'); }} style={{
                background: 'rgba(239,71,111,0.1)', color: '#EF476F',
                border: '1px solid rgba(239,71,111,0.2)', borderRadius: 8,
                padding: '9px 14px', cursor: 'pointer', fontSize: 12, fontWeight: 600,
              }}>✕ Temizle</button>
            )}
          </div>

          {(() => {
            const q = search.toLowerCase()
            const filtered = funds
              .filter(f => !q || f.code.toLowerCase().includes(q) || f.name.toLowerCase().includes(q))
              .filter(f => filterType === 'Tümü' || f.fundType === filterType)
              .filter(f => filterRisk === 'Tümü' || String(f.riskScore) === filterRisk)
              .sort((a, b) => {
                if (sortBy === 'name') return a.code.localeCompare(b.code)
                if (sortBy === 'monthlyReturn') return (b.monthlyReturn || -999) - (a.monthlyReturn || -999)
                if (sortBy === 'yearlyReturn') return (b.yearlyReturn || -999) - (a.yearlyReturn || -999)
                if (sortBy === 'totalValue') return (b.totalValue || 0) - (a.totalValue || 0)
                if (sortBy === 'participantCount') return (b.participantCount || 0) - (a.participantCount || 0)
                if (sortBy === 'riskScore') return (a.riskScore || 0) - (b.riskScore || 0)
                return 0
              })
            return (
              <>
                {filtered.length === 0 && (
                  <div style={{ textAlign: 'center', color: '#475569', padding: 40, fontSize: 14 }}>
                    🔍 Sonuç bulunamadı
                  </div>
                )}
          {viewMode === 'tweets' && <DailyTweets />}
          {viewMode === 'top5' && (
            <Top5 onSelectFund={(code) => {
              const f = funds.find(x => x.code === code)
              if (f) { setSelected(f); setViewMode('list') }
            }} />
          )}
          {viewMode === 'compare' && (
            <div style={{ padding: '24px 0' }}>
              <div style={{ fontSize: 13, fontWeight: 600, color: '#FFD166', marginBottom: 16 }}>⚖️ Karşılaştırmak istediğiniz iki fonu seçin</div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 24 }}>
                {[['A', compareA, setCompareA], ['B', compareB, setCompareB]].map(([label, val, setter]) => (
                  <div key={label}>
                    <div style={{ fontSize: 11, color: '#475569', marginBottom: 8 }}>FON {label}</div>
                    <select value={val} onChange={e => setter(e.target.value)}
                      style={{ width: '100%', background: '#0f172a', border: '1px solid #1e293b', borderRadius: 8, padding: '9px 12px', color: val ? '#f1f5f9' : '#475569', fontSize: 13, cursor: 'pointer' }}>
                      <option value="">Fon seçin...</option>
                      {funds.map(f => <option key={f.code} value={f.code}>{f.code} — {f.name}</option>)}
                    </select>
                  </div>
                ))}
              </div>
              {compareA && compareB && (() => {
                const fA = funds.find(f => f.code === compareA)
                const fB = funds.find(f => f.code === compareB)
                if (!fA || !fB) return null
                const rows = [
                  { label: 'Fon Adı', a: fA.name, b: fB.name, type: 'text' },
                  { label: 'Fon Türü', a: fA.fundType || '—', b: fB.fundType || '—', type: 'text' },
                  { label: 'Aylık Getiri', a: fA.monthlyReturn, b: fB.monthlyReturn, type: 'pct', better: 'high' },
                  { label: 'Yıllık Getiri', a: fA.yearlyReturn, b: fB.yearlyReturn, type: 'pct', better: 'high' },
                  { label: 'Risk Skoru', a: fA.riskScore, b: fB.riskScore, type: 'risk', better: 'low' },
                  { label: 'Portföy Büyüklüğü', a: fA.totalValue, b: fB.totalValue, type: 'aum', better: 'high' },
                  { label: 'Yatırımcı Sayısı', a: fA.participantCount, b: fB.participantCount, type: 'num', better: 'high' },
                ]
                const fmt = (v, type) => {
                  if (v == null) return '—'
                  if (type === 'pct') return (v >= 0 ? '+' : '') + v.toFixed(2) + '%'
                  if (type === 'risk') return v + '/7'
                  if (type === 'aum') return v >= 1e9 ? '₺' + (v/1e9).toFixed(1) + 'B' : '₺' + (v/1e6).toFixed(0) + 'M'
                  if (type === 'num') return v.toLocaleString('tr-TR')
                  return v
                }
                const winner = (row) => {
                  if (!row.better || row.a == null || row.b == null) return null
                  if (row.better === 'high') return row.a > row.b ? 'a' : row.b > row.a ? 'b' : null
                  return row.a < row.b ? 'a' : row.b < row.a ? 'b' : null
                }
                return (
                  <div style={{ background: '#0f172a', borderRadius: 12, overflow: 'hidden', border: '1px solid #1e293b' }}>
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', background: '#0a0a1a', padding: '12px 16px', fontSize: 12, fontWeight: 700 }}>
                      <div style={{ color: '#475569' }}>METRİK</div>
                      <div style={{ color: '#00C2A8', textAlign: 'center' }}>{fA.code}</div>
                      <div style={{ color: '#FFD166', textAlign: 'center' }}>{fB.code}</div>
                    </div>
                    {rows.map((row, i) => {
                      const w = winner(row)
                      return (
                        <div key={i} style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', padding: '11px 16px', borderTop: '1px solid #1e293b', fontSize: 13 }}>
                          <div style={{ color: '#64748b', fontSize: 12 }}>{row.label}</div>
                          <div style={{ textAlign: 'center', fontWeight: w === 'a' ? 700 : 400, color: w === 'a' ? '#00C2A8' : row.type === 'pct' && row.a != null ? (row.a >= 0 ? '#00C2A8' : '#FF6B6B') : '#f1f5f9' }}>
                            {fmt(row.a, row.type)}{w === 'a' ? ' ✓' : ''}
                          </div>
                          <div style={{ textAlign: 'center', fontWeight: w === 'b' ? 700 : 400, color: w === 'b' ? '#FFD166' : row.type === 'pct' && row.b != null ? (row.b >= 0 ? '#00C2A8' : '#FF6B6B') : '#f1f5f9' }}>
                            {fmt(row.b, row.type)}{w === 'b' ? ' ✓' : ''}
                          </div>
                        </div>
                      )
                    })}
                    <div style={{ padding: '16px', borderTop: '1px solid #1e293b' }}>
                      <div style={{ fontSize: 11, color: '#475569', marginBottom: 12 }}>PORTFÖY DAĞILIMI</div>
                      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
                        {[fA, fB].map((f, fi) => (
                          <div key={fi}>
                            <div style={{ fontSize: 11, color: fi === 0 ? '#00C2A8' : '#FFD166', marginBottom: 8 }}>{f.code}</div>
                            {(f.portfolioItems || []).slice(0, 5).map((item, ii) => (
                              <div key={ii} style={{ marginBottom: 8 }}>
                                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, color: '#64748b', marginBottom: 3 }}>
                                  <span>{item.name}</span><span>{item.value?.toFixed(1)}%</span>
                                </div>
                                <div style={{ height: 3, background: '#1e293b', borderRadius: 2 }}>
                                  <div style={{ height: '100%', width: item.value + '%', background: fi === 0 ? 'rgba(0,194,168,0.5)' : 'rgba(255,209,102,0.5)', borderRadius: 2 }} />
                                </div>
                              </div>
                            ))}
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                )
              })()}
            </div>
          )}
          <div style={{ display: viewMode === 'compare' ? 'none' : 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(340px, 1fr))', gap: 16 }}>
            {filtered.map(fund => (
              <FundCard
                key={fund.code}
                fund={fund}
                onClick={() => {
                  if (viewMode === 'compare') {
                    if (!compareA) setCompareA(fund.code)
                    else if (!compareB && fund.code !== compareA) setCompareB(fund.code)
                  } else {
                    setSelected(fund)
                  }
                }}
                onRefresh={() => handleRefresh(fund.code)}
              />
            ))}
          </div>
              </>
            )
          })()}
          </>
        )}
      </div>

      {/* Modal */}
      {selected && (
        <FundDetail
          fundCode={selected.code}
          onClose={() => setSelected(null)}
          onDeleteFund={handleDelete}
          onRefresh={handleRefresh}
        />
      )}
      {/* Footer Disclaimer */}
      <div style={{ borderTop: '1px solid #1e293b', padding: '16px 28px', marginTop: 8, textAlign: 'center' }}>
        <p style={{ color: '#475569', fontSize: 11, lineHeight: 1.6, maxWidth: 700, margin: '0 auto' }}>
          ⚠️ <strong style={{ color: '#64748b' }}>Sorumluluk Reddi:</strong> Bu platformda yer alan tüm bilgiler yalnızca bilgilendirme amaçlıdır. 
          Hiçbir içerik yatırım tavsiyesi niteliği taşımaz. Geçmiş performans gelecekteki getirilerin garantisi değildir. 
          Yatırım kararlarınızı almadan önce lisanslı bir finansal danışmana başvurunuz.
        </p>
      </div>
    </div>
  )
}

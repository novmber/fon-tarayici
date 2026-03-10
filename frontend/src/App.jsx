import { useState, useEffect, useCallback } from 'react'
import { getFunds, trackFund, refreshFund, analyzePDF, deleteFund, getStats } from './api.js'
import FundCard from './components/FundCard.jsx'
import FundDetail from './components/FundDetail.jsx'

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
            <div style={{ color: '#475569', fontSize: 11 }}>TEFAS + KAP AI Analiz</div>
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
        {sBtn(() => setShowAdd(!showAdd), showAdd ? '✕ Kapat' : '+ Fon Ekle')}
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
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(340px, 1fr))', gap: 16 }}>
            {filtered.map(fund => (
              <FundCard
                key={fund.code}
                fund={fund}
                onClick={() => setSelected(fund)}
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
    </div>
  )
}

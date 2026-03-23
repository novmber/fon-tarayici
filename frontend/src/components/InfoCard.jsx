import { useState, useEffect, useRef } from 'react'
import { getBenchmarks } from '../api.js'

const RISK_COLORS = ['#22c55e','#84cc16','#eab308','#f97316','#ef4444','#dc2626','#991b1b']
const RISK_LABELS = ['','Düşük','Düşük-Orta','Orta-Düşük','Orta','Orta-Yüksek','Yüksek','Çok Yüksek']

function RiskMeter({ score }) {
  if (!score) return <span style={{ color: '#475569', fontSize: 13 }}>—</span>
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
      <div style={{ display: 'flex', gap: 3 }}>
        {[1,2,3,4,5,6,7].map(i => (
          <div key={i} style={{
            width: 18, height: 18, borderRadius: 4,
            background: i <= score ? RISK_COLORS[score - 1] : '#1e293b',
            border: i === score ? `2px solid ${RISK_COLORS[score-1]}` : '2px solid transparent',
            boxShadow: i === score ? `0 0 8px ${RISK_COLORS[score-1]}88` : 'none',
            transition: 'all 0.2s',
          }} />
        ))}
      </div>
      <span style={{ color: RISK_COLORS[score-1], fontWeight: 700, fontSize: 13 }}>
        {score}/7 · {RISK_LABELS[score]}
      </span>
    </div>
  )
}

function PerfBar({ label, value, fundValue, color }) {
  if (value == null) return null
  const max = Math.max(Math.abs(value), Math.abs(fundValue || 0), 10)
  const barW = Math.min(Math.abs(value) / max * 100, 100)
  const isPos = value >= 0
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 }}>
      <div style={{ width: 80, color: '#94a3b8', fontSize: 12, textAlign: 'right', flexShrink: 0 }}>{label}</div>
      <div style={{ flex: 1, height: 22, background: '#0f172a', borderRadius: 6, overflow: 'hidden', position: 'relative' }}>
        <div style={{
          position: 'absolute', top: 0, left: 0, height: '100%',
          width: `${barW}%`, background: isPos ? color : '#EF476F',
          borderRadius: 6, opacity: 0.8,
          transition: 'width 0.5s ease',
        }} />
        <div style={{
          position: 'absolute', top: 0, left: 0, right: 0, bottom: 0,
          display: 'flex', alignItems: 'center', paddingLeft: 8,
          color: '#f1f5f9', fontSize: 12, fontWeight: 600,
        }}>
          {isPos ? '+' : ''}{value}%
        </div>
      </div>
    </div>
  )
}

export default function InfoCard({ fund, latest, priceHistory }) {
  const [benchmarks, setBenchmarks] = useState(null)
  const [loadingBench, setLoadingBench] = useState(true)
  const [period, setPeriod] = useState('1m')
  const cardRef = useRef(null)

  useEffect(() => {
    getBenchmarks().then(d => { setBenchmarks(d); setLoadingBench(false) })
  }, [])

  const manualData = (() => {
    try { return JSON.parse(localStorage.getItem(`manual_price_${fund.code}`)) } catch { return null }
  })()
  const manualChangePct = manualData
    ? (((manualData.price - latest.unitPrice) / latest.unitPrice) * 100).toFixed(2)
    : null

  // Dönem bazlı fon getirisi (sadece aylık için PDF verisi var, diğerleri için null)
  const fundReturn = {
    '1m': latest.monthlyReturn,
    '3m': null,
    '6m': null,
    '1y': latest.yearlyReturn,
  }

  const periodLabel = { '1m': '1 Ay', '3m': '3 Ay', '6m': '6 Ay', '1y': '1 Yıl' }

  const handleExport = async () => {
    try {
      const { toPng } = await import('html-to-image')
      const node = cardRef.current
      const dataUrl = await toPng(node, { quality: 1, pixelRatio: 2 })
      const a = document.createElement('a')
      a.download = `${fund.code}_infografik.png`
      a.href = dataUrl
      a.click()
    } catch (e) {
      alert('PNG export için: npm install html-to-image')
    }
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>

      {/* Export butonu */}
      <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10 }}>
        <button id="infografik-download-btn" onClick={handleExport} style={{
          background: 'linear-gradient(135deg, #8338EC, #3A86FF)',
          color: 'white', border: 'none', borderRadius: 8,
          padding: '8px 18px', cursor: 'pointer', fontSize: 13, fontWeight: 600,
          display: 'flex', alignItems: 'center', gap: 6,
        }}>
          📸 PNG İndir
        </button>
      </div>

      {/* ─── İNFOGRAFİK KART ─── */}
      <div ref={cardRef} style={{
        background: 'linear-gradient(135deg, #0a0a1a 0%, #0f172a 50%, #0a0a1a 100%)',
        border: '1px solid #1e293b', borderRadius: 20, padding: 28,
        fontFamily: 'Space Grotesk, system-ui, sans-serif',
      }}>
        {/* Header */}
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 22 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
            <div style={{
              width: 56, height: 56, borderRadius: 14,
              background: 'linear-gradient(135deg, #8338EC, #3A86FF)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontSize: 22, fontWeight: 900, color: 'white', flexShrink: 0,
            }}>
              {fund.code.slice(0, 3)}
            </div>
            <div>
              <div style={{ color: '#f1f5f9', fontWeight: 700, fontSize: 16, lineHeight: 1.2 }}>{fund.name}</div>
              <div style={{ color: '#64748b', fontSize: 12, marginTop: 3 }}>{fund.company}</div>
              {latest.fundType && (
                <span style={{ background: 'rgba(131,56,236,0.15)', color: '#8338EC', borderRadius: 6, padding: '2px 8px', fontSize: 11, fontWeight: 600, marginTop: 4, display: 'inline-block' }}>
                  {latest.fundType}
                </span>
              )}
            </div>
          </div>
          <div style={{ textAlign: 'right' }}>
            <div style={{ color: '#64748b', fontSize: 10, textTransform: 'uppercase', letterSpacing: 1 }}>TÜRKİYE'DE FON TARAYICI</div>
            <div style={{ color: '#475569', fontSize: 11, marginTop: 2 }}>{latest.month}</div>
          </div>
        </div>

        {/* Üst metrik grid */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 10, marginBottom: 16 }}>
          {/* Yatırımcı Sayısı */}
          <div style={{ background: 'rgba(131,56,236,0.1)', border: '1px solid rgba(131,56,236,0.2)', borderRadius: 14, padding: '14px 16px', textAlign: 'center' }}>
            <div style={{ fontSize: 22, marginBottom: 4 }}>👥</div>
            <div style={{ color: '#64748b', fontSize: 10, textTransform: 'uppercase', letterSpacing: 0.8 }}>Yatırımcı Sayısı</div>
            <div style={{ color: '#f1f5f9', fontWeight: 700, fontSize: 18, marginTop: 4 }}>
              {latest.participantCount ? latest.participantCount.toLocaleString('tr-TR', { maximumFractionDigits: 0 }) : '—'}
            </div>
          </div>

          {/* Portföy Değeri */}
          <div style={{ background: 'rgba(58,134,255,0.1)', border: '1px solid rgba(58,134,255,0.2)', borderRadius: 14, padding: '14px 16px', textAlign: 'center' }}>
            <div style={{ fontSize: 22, marginBottom: 4 }}>💼</div>
            <div style={{ color: '#64748b', fontSize: 10, textTransform: 'uppercase', letterSpacing: 0.8 }}>Portföy Değeri</div>
            <div style={{ color: '#f1f5f9', fontWeight: 700, fontSize: 18, marginTop: 4 }}>
              {latest.totalValue >= 1e9
                ? `${(latest.totalValue / 1e9).toFixed(1)} Milyar`
                : `${(latest.totalValue / 1e6).toFixed(0)} Milyon`} TL
            </div>
          </div>

          {/* Risk Skoru */}
          <div style={{ background: latest.riskScore ? `${RISK_COLORS[(latest.riskScore||1)-1]}11` : 'rgba(30,41,59,0.5)', border: `1px solid ${latest.riskScore ? RISK_COLORS[(latest.riskScore||1)-1] + '33' : '#1e293b'}`, borderRadius: 14, padding: '14px 16px', textAlign: 'center' }}>
            <div style={{ fontSize: 22, marginBottom: 4 }}>🛡️</div>
            <div style={{ color: '#64748b', fontSize: 10, textTransform: 'uppercase', letterSpacing: 0.8 }}>Risk Değeri</div>
            <div style={{ color: latest.riskScore ? RISK_COLORS[(latest.riskScore||1)-1] : '#475569', fontWeight: 900, fontSize: 24, marginTop: 4 }}>
              {latest.riskScore ? `${latest.riskScore} / 7` : '— / 7'}
            </div>
          </div>
        </div>

        {/* Getiri + Pay Fiyatı */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 10, marginBottom: 16 }}>
          <div style={{ background: 'rgba(0,194,168,0.08)', border: '1px solid rgba(0,194,168,0.2)', borderRadius: 14, padding: '12px 16px' }}>
            <div style={{ color: '#64748b', fontSize: 10, textTransform: 'uppercase', letterSpacing: 0.8, marginBottom: 4 }}>Aylık Getiri</div>
            <div style={{ color: latest.monthlyReturn >= 0 ? '#00C2A8' : '#EF476F', fontWeight: 900, fontSize: 22 }}>
              {latest.monthlyReturn >= 0 ? '+' : ''}{latest.monthlyReturn}%
            </div>
          </div>
          <div style={{ background: 'rgba(255,209,102,0.08)', border: '1px solid rgba(255,209,102,0.2)', borderRadius: 14, padding: '12px 16px' }}>
            <div style={{ color: '#64748b', fontSize: 10, textTransform: 'uppercase', letterSpacing: 0.8, marginBottom: 4 }}>Yıllık Getiri</div>
            <div style={{ color: '#FFD166', fontWeight: 900, fontSize: 22 }}>
              +{latest.yearlyReturn}%
            </div>
          </div>
          <div style={{ background: '#1e293b', borderRadius: 14, padding: '12px 16px' }}>
            <div style={{ color: '#64748b', fontSize: 10, textTransform: 'uppercase', letterSpacing: 0.8, marginBottom: 4 }}>Pay Fiyatı</div>
            <div style={{ color: '#f1f5f9', fontWeight: 700, fontSize: 16, fontFamily: 'JetBrains Mono, monospace' }}>
              {latest.unitPrice?.toFixed(4)} TL
            </div>
            {manualData && (
              <div style={{ color: Number(manualChangePct) >= 0 ? '#00C2A8' : '#EF476F', fontSize: 12, fontWeight: 600, marginTop: 2 }}>
                Bugün: {manualData.price.toFixed(4)} ({Number(manualChangePct) >= 0 ? '+' : ''}{manualChangePct}%)
              </div>
            )}
          </div>
        </div>

        {/* Detay satırı: Yönetim Ücreti + Stopaj + Valör */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 10, marginBottom: 16 }}>
          <div style={{ background: '#1e293b', borderRadius: 12, padding: '10px 14px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ color: '#64748b', fontSize: 11 }}>Kişi Başı Yatırım</span>
            <span style={{ color: '#f1f5f9', fontWeight: 700, fontSize: 14 }}>
              {latest.totalValue && latest.participantCount
                ? (() => {
                    const v = latest.totalValue / latest.participantCount;
                    return v >= 1e6
                      ? `${(v/1e6).toFixed(2)}M ₺`
                      : v >= 1e3
                      ? `${(v/1e3).toFixed(1)}K ₺`
                      : `${v.toFixed(0)} ₺`;
                  })()
                : '—'}
            </span>
          </div>
          <div style={{ background: '#1e293b', borderRadius: 12, padding: '10px 14px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ color: '#64748b', fontSize: 11 }}>30g Yatırımcı</span>
            <span style={{ fontWeight: 700, fontSize: 14, color: (() => {
              if (!priceHistory || priceHistory.length < 21) return '#94a3b8';
              const diff = priceHistory[priceHistory.length-1].participantCount - priceHistory[priceHistory.length-21].participantCount;
              return diff > 0 ? '#4ade80' : diff < 0 ? '#f87171' : '#94a3b8';
            })() }}>
              {(() => {
                if (!priceHistory || priceHistory.length < 21) return '—';
                const diff = priceHistory[priceHistory.length-1].participantCount - priceHistory[priceHistory.length-21].participantCount;
                return (diff > 0 ? '+' : '') + Math.round(diff).toLocaleString('tr-TR');
              })()}
            </span>
          </div>
          <div style={{ background: '#1e293b', borderRadius: 12, padding: '10px 14px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ color: '#64748b', fontSize: 11 }}>30g Para Akışı</span>
            <span style={{ fontWeight: 700, fontSize: 14, color: (() => {
              if (!priceHistory || priceHistory.length < 21) return '#94a3b8';
              const diff = priceHistory[priceHistory.length-1].totalValue - priceHistory[priceHistory.length-21].totalValue;
              return diff > 0 ? '#4ade80' : diff < 0 ? '#f87171' : '#94a3b8';
            })() }}>
              {(() => {
                if (!priceHistory || priceHistory.length < 21) return '—';
                const diff = priceHistory[priceHistory.length-1].totalValue - priceHistory[priceHistory.length-21].totalValue;
                const abs = Math.abs(diff);
                const str = abs >= 1e9 ? (abs/1e9).toFixed(2)+'B' : abs >= 1e6 ? (abs/1e6).toFixed(0)+'M' : (abs/1e3).toFixed(0)+'K';
                return (diff > 0 ? '+' : '-') + '₺' + str;
              })()}
            </span>
          </div>
        </div>

        {/* Risk meter */}
        {latest.riskScore && (
          <div style={{ background: '#1e293b', borderRadius: 12, padding: '12px 16px', marginBottom: 16 }}>
            <div style={{ color: '#64748b', fontSize: 11, marginBottom: 8 }}>RİSK SEVİYESİ</div>
            <RiskMeter score={latest.riskScore} />
          </div>
        )}

        {/* Portföy dağılımı bar */}
        {latest.portfolioItems?.length > 0 && (
          <div style={{ background: '#1e293b', borderRadius: 12, padding: '12px 16px', marginBottom: 16 }}>
            <div style={{ color: '#64748b', fontSize: 11, marginBottom: 10 }}>VARLIK DAĞILIMI</div>
            <div style={{ display: 'flex', height: 12, borderRadius: 8, overflow: 'hidden', gap: 2, marginBottom: 10 }}>
              {latest.portfolioItems.filter(i => i.value > 0).map((item, i) => {
                const colors = ['#00C2A8','#3A86FF','#FFD166','#EF476F','#8338EC','#06D6A0','#FB5607']
                return <div key={i} title={`${item.name}: ${item.value}%`} style={{ flex: item.value, background: colors[i % colors.length], borderRadius: 4 }} />
              })}
            </div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px 14px' }}>
              {latest.portfolioItems.filter(i => i.value > 0.5).map((item, i) => {
                const colors = ['#00C2A8','#3A86FF','#FFD166','#EF476F','#8338EC','#06D6A0','#FB5607']
                return (
                  <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
                    <div style={{ width: 8, height: 8, borderRadius: 2, background: colors[i % colors.length], flexShrink: 0 }} />
                    <span style={{ color: '#94a3b8', fontSize: 11 }}>{item.name} <span style={{ color: '#f1f5f9', fontWeight: 600 }}>%{item.value}</span></span>
                  </div>
                )
              })}
            </div>
          </div>
        )}

        {/* Footer */}
        <div style={{ textAlign: 'center', color: '#334155', fontSize: 10, marginTop: 8 }}>
          Fon Tarayıcı · KAP PDF Analizi · {latest.month}
        </div>
      </div>

      {/* ─── SCORECARD ─── */}
      {fund.scorecard && fund.scorecard.overall && (
        <div style={{ background: '#1e293b', borderRadius: 16, padding: '18px 20px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
            <p style={{ color: '#f1f5f9', fontSize: 14, fontWeight: 600, margin: 0 }}>🏅 AI Scorecard</p>
            <div style={{
              background: fund.scorecard.overall >= 70 ? 'rgba(74,222,128,0.15)' : fund.scorecard.overall >= 50 ? 'rgba(250,204,21,0.15)' : 'rgba(248,113,113,0.15)',
              border: `1px solid ${fund.scorecard.overall >= 70 ? 'rgba(74,222,128,0.4)' : fund.scorecard.overall >= 50 ? 'rgba(250,204,21,0.4)' : 'rgba(248,113,113,0.4)'}`,
              borderRadius: 8, padding: '4px 12px', display: 'flex', alignItems: 'center', gap: 8
            }}>
              <span style={{ fontSize: 20, fontWeight: 800, color: fund.scorecard.overall >= 70 ? '#4ade80' : fund.scorecard.overall >= 50 ? '#facc15' : '#f87171' }}>
                {fund.scorecard.overall}
              </span>
              <span style={{ fontSize: 16, fontWeight: 700, color: '#94a3b8' }}>{fund.scorecard.grade}</span>
            </div>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {[
              { label: '📈 İstikrar', value: fund.scorecard.istikrar, desc: `Max Düşüş: %${fund.scorecard.details?.maxDrawdown ?? '?'}` },
              { label: '🏆 Yönetim', value: fund.scorecard.yonetim, desc: `Benchmark Kazanma: %${fund.scorecard.details?.benchmarkWinRate ?? '?'}` },
              { label: '⏱️ Zamanlama', value: fund.scorecard.zamanlama, desc: fund.scorecard.details?.rsiYorum ?? '' },
            ].map(({ label, value, desc }) => (
              <div key={label}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                  <span style={{ fontSize: 12, color: '#94a3b8' }}>{label}</span>
                  <span style={{ fontSize: 12, color: '#64748b' }}>{desc}</span>
                </div>
                <div style={{ height: 8, background: '#0f172a', borderRadius: 4, overflow: 'hidden' }}>
                  <div style={{
                    height: '100%', borderRadius: 4,
                    width: `${value}%`,
                    background: value >= 70 ? '#4ade80' : value >= 50 ? '#facc15' : '#f87171',
                    transition: 'width 0.6s ease'
                  }} />
                </div>
                <div style={{ textAlign: 'right', fontSize: 11, color: '#475569', marginTop: 2 }}>{value}/100</div>
              </div>
            ))}
          </div>
          {fund.scorecard.details?.rsi && (
            <div style={{ marginTop: 12, padding: '8px 12px', background: '#0f172a', borderRadius: 8, fontSize: 12, color: '#94a3b8' }}>
              RSI: <span style={{ fontWeight: 700, color: fund.scorecard.details.rsi > 70 ? '#f87171' : fund.scorecard.details.rsi < 30 ? '#4ade80' : '#facc15' }}>
                {fund.scorecard.details.rsi}
              </span> — {fund.scorecard.details.rsiYorum}
            </div>
          )}
        </div>
      )}

      {/* ─── PERFORMANS KARŞILAŞTIRMASI ─── */}
      <div style={{ background: '#1e293b', borderRadius: 16, padding: '18px 20px' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
          <p style={{ color: '#f1f5f9', fontSize: 14, fontWeight: 600, margin: 0 }}>
            📊 Benchmark Karşılaştırması
          </p>
          <div style={{ display: 'flex', gap: 6 }}>
            {['1m','1y'].map(p => (
              <button key={p} onClick={() => setPeriod(p)} style={{
                background: period === p ? '#00C2A8' : '#0f172a',
                color: period === p ? '#020817' : '#64748b',
                border: 'none', borderRadius: 6, padding: '4px 10px',
                cursor: 'pointer', fontSize: 12, fontWeight: 600,
              }}>{periodLabel[p]}</button>
            ))}
          </div>
        </div>

        {loadingBench ? (
          <div style={{ color: '#475569', fontSize: 13, padding: '10px 0' }}>Yahoo Finance'ten çekiliyor...</div>
        ) : (
          <div>
            {/* Fon */}
            <PerfBar
              label={fund.code}
              value={fundReturn[period]}
              fundValue={fundReturn[period]}
              color="#00C2A8"
            />
            {fundReturn[period] == null && (
              <div style={{ color: '#475569', fontSize: 11, marginBottom: 8, marginLeft: 90 }}>
                {period === '3m' || period === '6m' ? `${periodLabel[period]} verisi için daha fazla PDF yükleyin` : ''}
              </div>
            )}
            {/* Benchmarklar */}
            {benchmarks && (
              <>
                <PerfBar label="BİST 100" value={benchmarks.bist100?.[period]} fundValue={fundReturn[period]} color="#3A86FF" />
                <PerfBar label="Altın" value={benchmarks.gold?.[period]} fundValue={fundReturn[period]} color="#FFD166" />
                <PerfBar label="Dolar/TL" value={benchmarks.usdtry?.[period]} fundValue={fundReturn[period]} color="#FB5607" />
              </>
            )}
            <div style={{ color: '#334155', fontSize: 10, marginTop: 12 }}>
              Benchmark verileri Yahoo Finance · Otomatik güncellenir (1 saat cache)
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
